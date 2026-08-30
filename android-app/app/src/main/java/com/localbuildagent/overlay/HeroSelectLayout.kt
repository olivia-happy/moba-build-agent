package com.localbuildagent.overlay

data class IntRect(val left: Int, val top: Int, val width: Int, val height: Int)

data class NormalizedCrop(
    val left: Int,
    val top: Int,
    val width: Int,
    val height: Int,
    val referenceWidth: Int,
    val referenceHeight: Int,
) {
    fun scaleTo(widthPixels: Int, heightPixels: Int): IntRect = IntRect(
        left = left * widthPixels / referenceWidth,
        top = top * heightPixels / referenceHeight,
        width = width * widthPixels / referenceWidth,
        height = height * heightPixels / referenceHeight,
    )
}

/** Versioned crop profile; it is intentionally replaceable when the game's UI layout changes. */
data class HeroSelectLayout(
    val version: String,
    val enemyPortraits: List<NormalizedCrop>,
) {
    companion object {
        val default = HeroSelectLayout(
            version = "draft-layout-1080x2400-v1",
            enemyPortraits = listOf(
                NormalizedCrop(784, 312, 112, 112, 1080, 2400),
                NormalizedCrop(784, 462, 112, 112, 1080, 2400),
                NormalizedCrop(784, 612, 112, 112, 1080, 2400),
                NormalizedCrop(784, 762, 112, 112, 1080, 2400),
                NormalizedCrop(784, 912, 112, 112, 1080, 2400),
            ),
        )
    }
}
