package com.localbuildagent.overlay

import kotlin.test.Test
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class CaptureIntentPolicyTest {
    @Test
    fun `only explicit player actions may request a game frame`() {
        assertTrue(CaptureIntentPolicy.allowsCapture(CaptureTrigger.PlayerTappedOverlay))
        assertTrue(CaptureIntentPolicy.allowsCapture(CaptureTrigger.PlayerTappedShopUpdate))
        assertFalse(CaptureIntentPolicy.allowsCapture(CaptureTrigger.AppStarted))
        assertFalse(CaptureIntentPolicy.allowsCapture(CaptureTrigger.TimerElapsed))
    }
}
