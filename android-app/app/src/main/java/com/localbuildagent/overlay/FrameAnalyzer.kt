package com.localbuildagent.overlay

import java.io.File
import java.io.FileInputStream

/**
 * Analyzes one user-authorized screen frame and returns ranked hero candidates.
 *
 * The pipeline is intentionally explicit and local:
 *   1. Load the luminance summary written by SingleFrameCaptureService
 *      (4-byte LE width + 4-byte LE height + width*height luminance bytes).
 *   2. Crop each enemy portrait using a versioned layout profile.
 *   3. Downsample the crop to a fixed 16x16 luminance grid.
 *   4. Rank against the bundled portrait fingerprint index.
 *
 * It never returns a single "this is definitely the hero" answer; the player
 * always confirms or corrects the Top-3 candidates before any build advice is
 * requested. Low-confidence results are surfaced so the player can retry.
 */
object FrameAnalyzer {

    const val GRID_SIZE = 16
    const val MAX_FRAME_BYTES = 64L * 1024 * 1024
    private const val HEADER_BYTES = 8

    data class AnalyzedSlot(
        val slotIndex: Int,
        val crop: IntRect,
        val candidates: List<HeroPortraitMatch>,
    )

    fun analyze(
        frameFile: File,
        layout: HeroSelectLayout = HeroSelectLayout.default,
        matcher: HeroPortraitMatcher,
    ): List<AnalyzedSlot> {
        val frame = loadLuminanceFrame(frameFile) ?: return emptyList()
        val results = buildList {
            layout.enemyPortraits.forEachIndexed { index, normalized ->
                val rect = normalized.scaleTo(frame.width, frame.height)
                val crop = cropLuminance(frame.luminance, frame.width, frame.height, rect) ?: return@forEachIndexed
                val grid = downsampleToGrid(crop, rect.width, rect.height)
                add(
                    AnalyzedSlot(
                        slotIndex = index,
                        crop = rect,
                        candidates = matcher.rank(grid, limit = 3),
                    ),
                )
            }
        }
        return results
    }

    data class LuminanceFrame(val width: Int, val height: Int, val luminance: IntArray)

    /** Reads the app-private luminance file written by SingleFrameCaptureService. */
    fun loadLuminanceFrame(file: File): LuminanceFrame? {
        if (!file.isFile || file.length() < HEADER_BYTES || file.length() > MAX_FRAME_BYTES) return null
        val bytes = ByteArray(file.length().toInt())
        FileInputStream(file).use { input ->
            var offset = 0
            while (offset < bytes.size) {
                val read = input.read(bytes, offset, bytes.size - offset)
                if (read <= 0) break
                offset += read
            }
        }
        val width = (bytes[0].toInt() and 0xFF) or
            ((bytes[1].toInt() and 0xFF) shl 8) or
            ((bytes[2].toInt() and 0xFF) shl 16) or
            ((bytes[3].toInt() and 0xFF) shl 24)
        val height = (bytes[4].toInt() and 0xFF) or
            ((bytes[5].toInt() and 0xFF) shl 8) or
            ((bytes[6].toInt() and 0xFF) shl 16) or
            ((bytes[7].toInt() and 0xFF) shl 24)
        if (width <= 0 || height <= 0) return null
        val expected = HEADER_BYTES + width.toLong() * height.toLong()
        if (file.length() < expected) return null
        val luminance = IntArray(width * height)
        for (i in luminance.indices) {
            luminance[i] = bytes[HEADER_BYTES + i].toInt() and 0xFF
        }
        return LuminanceFrame(width, height, luminance)
    }

    /** Luminance crop; clamps out-of-bounds like the Python builder. */
    fun cropLuminance(luminance: IntArray, frameWidth: Int, frameHeight: Int, rect: IntRect): IntArray? {
        val left = rect.left.coerceIn(0, frameWidth - 1)
        val top = rect.top.coerceIn(0, frameHeight - 1)
        val width = rect.width.coerceIn(1, frameWidth - left)
        val height = rect.height.coerceIn(1, frameHeight - top)
        if (width <= 0 || height <= 0) return null
        val crop = IntArray(width * height)
        for (y in 0 until height) {
            val srcStart = (top + y) * frameWidth + left
            luminance.copyInto(crop, destinationOffset = y * width, startIndex = srcStart, endIndex = srcStart + width)
        }
        return crop
    }

    /** Same cell averaging as backend/app/portrait_index.py downsample_to_grid. */
    fun downsampleToGrid(luminance: IntArray, width: Int, height: Int, gridSize: Int = GRID_SIZE): IntArray {
        require(width > 0 && height > 0)
        require(luminance.size == width * height) { "pixel count mismatch" }
        val cells = IntArray(gridSize * gridSize)
        for (cellY in 0 until gridSize) {
            val y0 = cellY * height / gridSize
            val y1 = (cellY + 1) * height / gridSize
            for (cellX in 0 until gridSize) {
                val x0 = cellX * width / gridSize
                val x1 = (cellX + 1) * width / gridSize
                var total = 0
                var count = 0
                for (y in y0 until y1) {
                    val start = y * width + x0
                    for (x in x0 until x1) {
                        total += luminance[start + (x - x0)]
                        count += 1
                    }
                }
                cells[cellY * gridSize + cellX] = if (count > 0) total / count else 0
            }
        }
        return cells
    }
}
