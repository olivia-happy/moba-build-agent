package com.localbuildagent.overlay

import kotlin.test.Test
import kotlin.test.assertEquals

class HeroSelectLayoutTest {
    @Test
    fun `scales portrait crop from a 1080 by 2400 profile`() {
        val crop = HeroSelectLayout.default.enemyPortraits.first().scaleTo(540, 1200)

        assertEquals(IntRect(392, 156, 56, 56), crop)
    }
}
