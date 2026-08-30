package com.localbuildagent.overlay

import kotlin.math.abs

data class HeroPortraitFingerprint(
    val heroId: Int,
    val heroName: String,
    val values: IntArray,
    val contentHash: String = "",
)

data class HeroPortraitMatch(
    val heroId: Int,
    val heroName: String,
    val confidence: Double,
    val contentHash: String = "",
)

/** Lightweight on-device fallback. It yields candidates for player review, never final selections. */
class HeroPortraitMatcher(private val references: List<HeroPortraitFingerprint>) {
    fun rank(sample: IntArray, limit: Int = 3): List<HeroPortraitMatch> =
        references
            .filter { it.values.size == sample.size }
            .map { reference ->
                val maxDistance = sample.size * 255.0
                val distance = sample.indices.sumOf { index -> abs(sample[index] - reference.values[index]).toDouble() }
                HeroPortraitMatch(
                    heroId = reference.heroId,
                    heroName = reference.heroName,
                    confidence = (1.0 - distance / maxDistance).coerceIn(0.0, 1.0),
                    contentHash = reference.contentHash,
                )
            }
            .sortedByDescending { it.confidence }
            .take(limit)

    companion object {
        const val MINIMUM_CONFIRMATION_CONFIDENCE = 0.80

        fun isConfident(confidence: Double): Boolean =
            confidence >= MINIMUM_CONFIRMATION_CONFIDENCE

        fun fromIndex(index: PortraitIndexParser.ParsedIndex): HeroPortraitMatcher =
            HeroPortraitMatcher(index.fingerprints)
    }
}

object PortraitFingerprintExtractor {
    /** Uses luminance only so references stay small and can be computed entirely on-device. */
    fun fromRgb(rgbPixels: IntArray): IntArray = rgbPixels.map { rgb ->
        val red = (rgb shr 16) and 0xFF
        val green = (rgb shr 8) and 0xFF
        val blue = rgb and 0xFF
        (0.299 * red + 0.587 * green + 0.114 * blue).toInt()
    }.toIntArray()
}
