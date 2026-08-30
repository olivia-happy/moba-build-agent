
package com.localbuildagent.overlay

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

class DecisionRequestPolicyTest {
    @Test
    fun onlyReviewedDraftsCanBeSentToTheLocalDecisionAgent() {
        assertFalse(DecisionRequestPolicy.canSend(ScreenStateDraft(400, listOf(101), emptyList(), false)))
        assertTrue(DecisionRequestPolicy.canSend(ScreenStateDraft(400, listOf(101), emptyList(), true)))
    }
}

class DecisionResponseParserTest {
    @Test
    fun parserReadsEnrichedRecommendationAndEmergencySwapFields() {
        val json = """
        {
          "input_source": "player_confirmed_screen",
          "mode": "local_rules",
          "priority_needs": ["magic_resist", "tenacity"],
          "threat_counts": {"magic_burst": 2, "crowd_control": 1},
          "unknown_hero_ids": [],
          "recommendations": [
            {
              "item_id": 1422,
              "item_name": "抵抗之靴",
              "covered_needs": ["magic_resist", "tenacity"],
              "purchase_status": "buy_now",
              "next_item_id": 1422,
              "next_item_name": "抵抗之靴",
              "replace_item_id": null,
              "evidence": "提供韧性与法术防御",
              "function_explanation": {"tenacity": "韧性（缩短被控时间）", "magic_resist": "法术防御"},
              "item_price": 700,
              "component_path": [{"item_id": 1405, "name": "神速之靴", "price": 250}],
              "why_now": "敌方控制偏多，缩短被控时间"
            }
          ],
          "emergency_swap": {
            "suggestions": [
              {
                "action": "swap_now",
                "target_item_id": 1422,
                "target_item_name": "抵抗之靴",
                "cost": 700,
                "reason": "敌方控制偏多",
                "why_now": "换鞋提升韧性",
                "evidence": "提供韧性",
                "constraints": ["鞋子移速不叠加"],
                "replace_item_id": 1423
              }
            ],
            "remaining_gold": 1200,
            "inventory_slots_free": 5,
            "revive_uses_remaining": 1,
            "warnings": []
          }
        }
        """.trimIndent()

        val response = DecisionResponseParser.parse(json)

        assertEquals(listOf("magic_resist", "tenacity"), response.priorityNeeds)
        assertEquals(2, response.threatCounts["magic_burst"])
        assertEquals(1, response.recommendations.size)
        val rec = response.recommendations[0]
        assertEquals(1422, rec.itemId)
        assertEquals("抵抗之靴", rec.itemName)
        assertEquals("buy_now", rec.purchaseStatus)
        assertEquals(700, rec.itemPrice)
        assertEquals("韧性（缩短被控时间）", rec.functionExplanation["tenacity"])
        assertEquals(1, rec.componentPath.size)
        assertEquals("神速之靴", rec.componentPath[0].name)
        assertEquals("敌方控制偏多，缩短被控时间", rec.whyNow)

        val swap = assertNotNull(response.emergencySwap)
        assertEquals(1, swap.suggestions.size)
        val suggestion = swap.suggestions[0]
        assertEquals("swap_now", suggestion.action)
        assertEquals(1422, suggestion.targetItemId)
        assertEquals(1423, suggestion.replaceItemId)
        assertEquals(listOf("鞋子移速不叠加"), suggestion.constraints)
        assertEquals(1, swap.reviveUsesRemaining)
    }

    @Test
    fun parserToleratesMissingOptionalFields() {
        val json = """
        {
          "input_source": "player_confirmed_screen",
          "mode": "local_rules",
          "priority_needs": [],
          "threat_counts": {},
          "unknown_hero_ids": [999999],
          "recommendations": []
        }
        """.trimIndent()

        val response = DecisionResponseParser.parse(json)

        assertTrue(response.priorityNeeds.isEmpty())
        assertNull(response.emergencySwap)
        assertEquals(listOf(999999), response.unknownHeroIds)
        assertTrue(response.recommendations.isEmpty())
    }
}
