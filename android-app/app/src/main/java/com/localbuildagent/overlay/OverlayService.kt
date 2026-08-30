package com.localbuildagent.overlay

import android.app.Service
import android.content.Intent
import android.graphics.PixelFormat
import android.os.IBinder
import android.view.Gravity
import android.view.WindowManager
import android.widget.Button

class OverlayService : Service() {
    private lateinit var windowManager: WindowManager
    private lateinit var overlayButton: Button

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (!::overlayButton.isInitialized) showOverlay()
        return START_NOT_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        if (::overlayButton.isInitialized) windowManager.removeView(overlayButton)
        super.onDestroy()
    }

    private fun showOverlay() {
        windowManager = getSystemService(WINDOW_SERVICE) as WindowManager
        overlayButton = Button(this).apply {
            text = "识别阵容"
            setOnClickListener {
                startActivity(
                    Intent(this@OverlayService, MainActivity::class.java)
                        .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                        .putExtra(MainActivity.CAPTURE_TRIGGER_EXTRA, CaptureTrigger.PlayerTappedOverlay::class.simpleName),
                )
            }
        }
        windowManager.addView(
            overlayButton,
            WindowManager.LayoutParams(
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
                PixelFormat.TRANSLUCENT,
            ).apply { gravity = Gravity.END or Gravity.CENTER_VERTICAL },
        )
    }
}
