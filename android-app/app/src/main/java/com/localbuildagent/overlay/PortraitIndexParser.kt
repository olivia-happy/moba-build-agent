package com.localbuildagent.overlay

import java.security.MessageDigest
import org.json.JSONObject

/**
 * Parses the versioned portrait_index.json produced by
 * backend/scripts/build_portrait_index.py. Android never needs to fetch this
 * file at runtime when it is bundled as an asset; it also validates the
 * content hash so a stale or corrupted index fails loudly instead of
 * mislabeling a hero.
 */
object PortraitIndexParser {

    data class ParsedIndex(
        val schemaVersion: Int,
        val gridSize: Int,
        val heroCount: Int,
        val contentHash: String,
        val fingerprints: List<HeroPortraitFingerprint>,
    )

    const val SUPPORTED_SCHEMA_VERSION = 1

    fun parse(json: String): ParsedIndex {
        val document = JSONObject(json)
        val schemaVersion = document.getInt("schema_version")
        require(schemaVersion == SUPPORTED_SCHEMA_VERSION) {
            "unsupported portrait index schema_version=$schemaVersion"
        }
        val gridSize = document.getInt("grid_size")
        val contentHash = document.getString("content_hash")
        val canonicalPayload = document.getString("canonical_payload")
        val entries = document.getJSONArray("entries")

        val fingerprints = buildList {
            for (i in 0 until entries.length()) {
                val entry = entries.getJSONObject(i)
                val grid = entry.getJSONArray("grid")
                val values = IntArray(grid.length()) { grid.getInt(it) }
                add(
                    HeroPortraitFingerprint(
                        heroId = entry.getInt("hero_id"),
                        heroName = entry.getString("hero_name"),
                        values = values,
                        contentHash = entry.getString("content_hash"),
                    ),
                )
            }
        }

        require(sha256Hex(canonicalPayload) == contentHash) {
            "portrait index content_hash mismatch for canonical payload"
        }
        return ParsedIndex(
            schemaVersion = schemaVersion,
            gridSize = gridSize,
            heroCount = fingerprints.size,
            contentHash = contentHash,
            fingerprints = fingerprints,
        )
    }

    /** SHA-256 hex digest, shared by the Python builder and this parser. */
    fun sha256Hex(input: String): String =
        MessageDigest.getInstance("SHA-256")
            .digest(input.toByteArray(Charsets.UTF_8))
            .joinToString("") { "%02x".format(it) }
}
