package com.localbuildagent.overlay

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.graphics.PixelFormat
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.ImageReader
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import androidx.core.app.NotificationCompat
import java.io.File
import java.io.FileOutputStream
import java.nio.ByteBuffer

/** Captures exactly one user-authorized frame, stores it in app cache, then stops. */
class SingleFrameCaptureService : Service() {
    private var projection: MediaProjection? = null
    private var display: VirtualDisplay? = null
    private var reader: ImageReader? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val resultCode = intent?.getIntExtra(RESULT_CODE, -1) ?: -1
        val resultData = intent?.getParcelableExtra<Intent>(RESULT_DATA)
        if (resultData == null || resultCode == -1) {
            stopSelf()
            return START_NOT_STICKY
        }
        startForeground(NOTIFICATION_ID, notification())
        captureOneFrame(resultCode, resultData)
        return START_NOT_STICKY
    }

    override fun onDestroy() {
        display?.release()
        reader?.close()
        projection?.stop()
        super.onDestroy()
    }

    @Suppress("DEPRECATION")
    private fun captureOneFrame(resultCode: Int, resultData: Intent) {
        val metrics = resources.displayMetrics
        reader = ImageReader.newInstance(metrics.widthPixels, metrics.heightPixels, PixelFormat.RGBA_8888, 2)
        val manager = getSystemService(MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        projection = manager.getMediaProjection(resultCode, resultData)
        projection?.registerCallback(object : MediaProjection.Callback() {}, null)
        display = projection?.createVirtualDisplay(
            "LocalBuildAgent-one-frame",
            metrics.widthPixels,
            metrics.heightPixels,
            metrics.densityDpi,
            DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
            reader?.surface,
            null,
            null,
        )
        val handler = Handler(Looper.getMainLooper())
        reader?.setOnImageAvailableListener({ imageReader ->
            imageReader.acquireLatestImage()?.use { image ->
                val plane = image.planes[0]
                val pixelStride = plane.pixelStride
                val rowStride = plane.rowStride
                val rowPadding = rowStride - pixelStride * image.width
                val buffer = ByteBuffer.allocate((rowStride * image.height) + 1)
                buffer.put(plane.buffer)
                buffer.rewind()
                // Strip row padding and store a compact custom layout:
                //   4-byte width (LE) + 4-byte height (LE) + w*h luminance bytes.
                // Only this grayscale summary is kept; the app-private cache
                // file is deleted after the frame is analyzed.
                val out = File(cacheDir, FRAME_FILE)
                FileOutputStream(out).use { output ->
                    writeIntLE(output, image.width)
                    writeIntLE(output, image.height)
                    val row = ByteArray(image.width * pixelStride)
                    for (y in 0 until image.height) {
                        buffer.position(y * rowStride)
                        buffer.get(row)
                        for (x in 0 until image.width) {
                            val offset = x * pixelStride
                            val luminance = (
                                0.299 * (row[offset].toInt() and 0xFF) +
                                0.587 * (row[offset + 1].toInt() and 0xFF) +
                                0.114 * (row[offset + 2].toInt() and 0xFF)
                            ).toInt().toByte()
                            output.write(luminance.toInt())
                        }
                    }
                }
            }
            sendBroadcast(
                Intent(ACTION_NOTIFY_ANALYZED)
                    .setPackage(packageName)
                    .putExtra(FRAME_FILE_EXTRA, FRAME_FILE),
            )
            stopSelf()
        }, handler)
    }

    private fun writeIntLE(output: FileOutputStream, value: Int) {
        output.write(value and 0xFF)
        output.write((value shr 8) and 0xFF)
        output.write((value shr 16) and 0xFF)
        output.write((value shr 24) and 0xFF)
    }

    private fun notification() = NotificationCompat.Builder(this, CHANNEL_ID)
        .setContentTitle("局内出装助手")
        .setContentText("正在处理你主动请求的一帧画面")
        .setSmallIcon(android.R.drawable.ic_menu_view)
        .setOngoing(true)
        .build()

    override fun onCreate() {
        super.onCreate()
        val channel = NotificationChannel(CHANNEL_ID, "截图状态", NotificationManager.IMPORTANCE_LOW)
        getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
    }

    companion object {
        const val RESULT_CODE = "result_code"
        const val RESULT_DATA = "result_data"
        const val FRAME_FILE = "latest-frame.lum"
        const val ACTION_NOTIFY_ANALYZED = "com.localbuildagent.overlay.ACTION_FRAME_ANALYZED"
        const val FRAME_FILE_EXTRA = "frame_file"
        private const val CHANNEL_ID = "frame_capture"
        private const val NOTIFICATION_ID = 1001
    }
}
