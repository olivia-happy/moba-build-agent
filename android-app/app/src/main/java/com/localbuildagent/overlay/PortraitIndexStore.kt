package com.localbuildagent.overlay

import android.content.Context
import java.io.IOException

/**
 * Loads the bundled portrait index from app assets.
 *
 * The JSON is produced by backend/scripts/build_portrait_index.py and copied
 * into android-app/app/src/main/assets/portrait_index.json (see
 * docs/data-sync.md). Parsing verifies the content hash so a stale or
 * corrupted bundle fails loudly instead of mislabelling a hero.
 */
object PortraitIndexStore {

    const val ASSET_NAME = "portrait_index.json"

    fun load(context: Context): PortraitIndexParser.ParsedIndex? {
        return try {
            val json = context.assets.open(ASSET_NAME).bufferedReader(Charsets.UTF_8).use { it.readText() }
            PortraitIndexParser.parse(json)
        } catch (error: IOException) {
            null
        } catch (error: IllegalArgumentException) {
            null
        }
    }
}
