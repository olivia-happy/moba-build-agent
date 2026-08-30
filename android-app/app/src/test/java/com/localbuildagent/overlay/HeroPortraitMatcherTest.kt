package com.localbuildagent.overlay

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class HeroPortraitMatcherTest {
    @Test
    fun `returns closest local portraits in descending confidence order`() {
        val matcher = HeroPortraitMatcher(
            listOf(
                HeroPortraitFingerprint(105, "Hero105", intArrayOf(0, 10, 20, 30)),
                HeroPortraitFingerprint(106, "Hero106", intArrayOf(255, 240, 230, 220)),
                HeroPortraitFingerprint(107, "Hero107", intArrayOf(5, 15, 22, 32)),
            ),
        )

        val matches = matcher.rank(intArrayOf(4, 14, 21, 31), limit = 2)

        assertEquals(listOf(107, 105), matches.map { it.heroId })
        assertTrue(matches[0].confidence > matches[1].confidence)
        assertTrue(matches[0].confidence in 0.0..1.0)
    }

    @Test
    fun `requires minimum confidence before a portrait can become a draft selection`() {
        assertTrue(HeroPortraitMatcher.isConfident(0.83))
        assertTrue(!HeroPortraitMatcher.isConfident(0.64))
    }

    @Test
    fun `turns rgb pixels into a fixed length grayscale fingerprint`() {
        val fingerprint = PortraitFingerprintExtractor.fromRgb(
            intArrayOf(
                0x000000, 0xFFFFFF,
                0xFF0000, 0x00FF00,
            ),
        )

        assertEquals(4, fingerprint.size)
        assertEquals(0, fingerprint[0])
        assertEquals(255, fingerprint[1])
        assertTrue(fingerprint[2] in 70..80)
        assertTrue(fingerprint[3] in 145..155)
    }
}
