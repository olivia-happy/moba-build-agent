package com.localbuildagent.overlay

import java.io.File
import java.io.FileOutputStream
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class FrameAnalyzerTest {

    private fun writeLuminanceFrame(file: File, width: Int, height: Int, values: IntArray) {
        FileOutputStream(file).use { output ->
            output.write(width and 0xFF)
            output.write((width shr 8) and 0xFF)
            output.write((width shr 16) and 0xFF)
            output.write((width shr 24) and 0xFF)
            output.write(height and 0xFF)
            output.write((height shr 8) and 0xFF)
            output.write((height shr 16) and 0xFF)
            output.write((height shr 24) and 0xFF)
            for (value in values) output.write(value and 0xFF)
        }
    }

    @Test
    fun loadsLuminanceFrameWithHeader() {
        val file = File.createTempFile("frame", ".lum")
        writeLuminanceFrame(file, 2, 2, intArrayOf(10, 20, 30, 40))

        val frame = FrameAnalyzer.loadLuminanceFrame(file)

        assertEquals(2, frame?.width)
        assertEquals(2, frame?.height)
        assertEquals(listOf(10, 20, 30, 40), frame?.luminance?.toList())
        file.delete()
    }

    @Test
    fun downsampleToGridMatchesPythonCellAveraging() {
        val luminance = IntArray(16 * 16) { index -> (index * 16) % 256 }
        val grid = FrameAnalyzer.downsampleToGrid(luminance, 16, 16, gridSize = 4)

        assertEquals(16, grid.size)
        assertTrue(grid.all { it in 0..255 })
        // Cell (0,0) covers rows 0..3, cols 0..3; value at (r,c) = ((r*16+c)*16)%256.
        // Each row contributes 0+16+32+48 = 96, four rows -> mean 384/16 = 24 (matches Python BOX).
        assertEquals(24, grid[0])
    }

    @Test
    fun cropLuminanceClampsOutOfBounds() {
        val luminance = IntArray(100) { it }
        val crop = FrameAnalyzer.cropLuminance(luminance, 10, 10, IntRect(8, 8, 4, 4))

        assertEquals(4, crop?.size)
        assertEquals(listOf(88, 89, 98, 99), crop?.toList())
    }
}
