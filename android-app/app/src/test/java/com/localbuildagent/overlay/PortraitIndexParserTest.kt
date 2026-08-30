package com.localbuildagent.overlay

import org.junit.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith

class PortraitIndexParserTest {

    /** Builds a synthetic index document whose canonical_payload matches [entries]. */
    private fun indexJson(entries: List<Triple<Int, String, IntArray>>): String {
        val sorted = entries.sortedBy { it.first }
        val entryJson = sorted.joinToString(",") { (id, name, grid) ->
            """{"content_hash":"entry-$id","grid":[${grid.joinToString(",")}],"hero_id":$id,"hero_name":"$name"}"""
        }
        val canonical = """[$entryJson]"""
        val contentHash = PortraitIndexParser.sha256Hex(canonical)
        return """{"schema_version":1,"grid_size":16,"hero_count":${sorted.size},"content_hash":"$contentHash","canonical_payload":"${escape(canonical)}","entries":[$entryJson]}"""
    }

    private fun escape(s: String): String =
        s.replace("\\", "\\\\").replace("\"", "\\\"")

    @Test
    fun parsesVersionedIndexIntoFingerprintsOrderedByHeroId() {
        val heroes = listOf(
            Triple(107, "Hero107", intArrayOf(4, 5, 6)),
            Triple(105, "Hero105", intArrayOf(1, 2, 3)),
        )
        val parsed = PortraitIndexParser.parse(indexJson(heroes))

        assertEquals(2, parsed.heroCount)
        assertEquals(listOf(105, 107), parsed.fingerprints.map { it.heroId })
        assertEquals(listOf("Hero105", "Hero107"), parsed.fingerprints.map { it.heroName })
        assertEquals(16, parsed.gridSize)
        assertEquals(listOf("entry-105", "entry-107"), parsed.fingerprints.map { it.contentHash })
    }

    @Test
    fun rejectsUnsupportedSchemaVersion() {
        val json = indexJson(listOf(Triple(105, "Hero105", intArrayOf(1)))).replace("\"schema_version\":1", "\"schema_version\":2")
        assertFailsWith<IllegalArgumentException> { PortraitIndexParser.parse(json) }
    }

    @Test
    fun rejectsTamperedContentHash() {
        val json = indexJson(listOf(Triple(105, "Hero105", intArrayOf(1)))).replace("\"content_hash\":\"", "\"content_hash\":\"evil-")
        assertFailsWith<IllegalArgumentException> { PortraitIndexParser.parse(json) }
    }

    @Test
    fun parsesSingleEntryAndKeepsPerHeroHash() {
        val json = indexJson(listOf(Triple(105, "Hero105", intArrayOf(1, 2, 3))))
        val parsed = PortraitIndexParser.parse(json)

        // parse() verifies document-level hash; per-hero hash stays intact.
        assertEquals("entry-105", parsed.fingerprints[0].contentHash)
        assertEquals(listOf(1, 2, 3), parsed.fingerprints[0].values.toList())
    }
}
