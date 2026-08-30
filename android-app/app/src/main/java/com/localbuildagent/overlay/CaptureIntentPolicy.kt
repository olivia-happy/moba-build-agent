package com.localbuildagent.overlay

/** Prevents background or timer-triggered screen capture requests. */
sealed interface CaptureTrigger {
    data object PlayerTappedOverlay : CaptureTrigger
    data object PlayerTappedShopUpdate : CaptureTrigger
    data object AppStarted : CaptureTrigger
    data object TimerElapsed : CaptureTrigger
}

object CaptureIntentPolicy {
    fun allowsCapture(trigger: CaptureTrigger): Boolean = when (trigger) {
        CaptureTrigger.PlayerTappedOverlay,
        CaptureTrigger.PlayerTappedShopUpdate -> true

        CaptureTrigger.AppStarted,
        CaptureTrigger.TimerElapsed -> false
    }
}
