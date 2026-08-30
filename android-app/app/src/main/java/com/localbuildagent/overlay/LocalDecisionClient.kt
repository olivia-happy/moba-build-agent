
package com.localbuildagent.overlay

import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

data class ScreenStateDraft(
    val gold: Int,
    val enemyHeroIds: List<Int>,
    val ownedItemIds: List<Int>,
    val playerConfirmed: Boolean,
    val reviveUsesUsed: Int = 0,
    val slotCapacity: Int = 6,
    val needsTenacity: Boolean = false,
)

object DecisionRequestPolicy {
    fun canSend(draft: ScreenStateDraft): Boolean = draft.playerConfirmed
}

/**
 * Calls only the user's own locally running FastAPI service.
 * 10.0.2.2 is Android Emulator's alias for the host machine; a physical device needs a user-configured LAN address.
 */
class LocalDecisionClient(private val baseUrl: String = "http://10.0.2.2:8000") {
    fun request(draft: ScreenStateDraft): String {
        require(DecisionRequestPolicy.canSend(draft)) { "Player confirmation is required." }
        val body = JSONObject()
            .put("gold", draft.gold)
            .put("enemy_hero_ids", JSONArray(draft.enemyHeroIds))
            .put("owned_item_ids", JSONArray(draft.ownedItemIds))
            .put("revive_uses_used", draft.reviveUsesUsed)
            .put("slot_capacity", draft.slotCapacity)
            .put("needs_tenacity", draft.needsTenacity)
            .put("input_source", "player_confirmed_screen")
        val connection = (URL("$baseUrl/api/decisions").openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            setRequestProperty("Content-Type", "application/json")
            doOutput = true
            connectTimeout = 3_000
            readTimeout = 5_000
        }
        connection.outputStream.bufferedWriter().use { it.write(body.toString()) }
        return connection.inputStream.bufferedReader().use { it.readText() }
    }
}

data class DecisionRecommendation(
    val itemId: Int,
    val itemName: String,
    val coveredNeeds: List<String>,
    val purchaseStatus: String,
    val nextItemName: String?,
    val replaceItemId: Int?,
    val evidence: String,
    val functionExplanation: Map<String, String> = emptyMap(),
    val itemPrice: Int? = null,
    val componentPath: List<ComponentInfo> = emptyList(),
    val whyNow: String = "",
)

data class ComponentInfo(
    val itemId: Int,
    val name: String,
    val price: Int,
)

data class EmergencySwapSuggestion(
    val action: String,
    val targetItemId: Int,
    val targetItemName: String,
    val cost: Int,
    val reason: String,
    val whyNow: String,
    val evidence: String,
    val constraints: List<String>,
    val replaceItemId: Int?,
)

data class EmergencySwapAdvice(
    val suggestions: List<EmergencySwapSuggestion>,
    val remainingGold: Int,
    val inventorySlotsFree: Int,
    val reviveUsesRemaining: Int?,
    val warnings: List<String>,
)

data class DecisionResponse(
    val priorityNeeds: List<String>,
    val threatCounts: Map<String, Int>,
    val unknownHeroIds: List<Int>,
    val recommendations: List<DecisionRecommendation>,
    val emergencySwap: EmergencySwapAdvice?,
)

/** Pure JSON -> model parsing so unit tests can verify evidence payloads. */
object DecisionResponseParser {
    fun parse(json: String): DecisionResponse {
        val root = JSONObject(json)
        val needs = buildList {
            val arr = root.getJSONArray("priority_needs")
            for (i in 0 until arr.length()) add(arr.getString(i))
        }
        val threats = buildMap {
            val obj = root.getJSONObject("threat_counts")
            val names = obj.names()
            if (names != null) {
                for (i in 0 until names.length()) {
                    val key = names.getString(i)
                    put(key, obj.getInt(key))
                }
            }
        }
        val unknown = buildList {
            val arr = root.getJSONArray("unknown_hero_ids")
            for (i in 0 until arr.length()) add(arr.getInt(i))
        }
        val recs = buildList {
            val arr = root.getJSONArray("recommendations")
            for (i in 0 until arr.length()) {
                val rec = arr.getJSONObject(i)
                val covered = buildList {
                    val needsArr = rec.getJSONArray("covered_needs")
                    for (j in 0 until needsArr.length()) add(needsArr.getString(j))
                }
                val functions = buildMap {
                    if (rec.has("function_explanation") && !rec.isNull("function_explanation")) {
                        val funcObj = rec.getJSONObject("function_explanation")
                        val keys = funcObj.names()
                        if (keys != null) {
                            for (j in 0 until keys.length()) {
                                val key = keys.getString(j)
                                put(key, funcObj.getString(key))
                            }
                        }
                    }
                }
                val components = buildList {
                    if (rec.has("component_path") && !rec.isNull("component_path")) {
                        val compArr = rec.getJSONArray("component_path")
                        for (j in 0 until compArr.length()) {
                            val comp = compArr.getJSONObject(j)
                            add(
                                ComponentInfo(
                                    itemId = comp.getInt("item_id"),
                                    name = comp.getString("name"),
                                    price = comp.getInt("price"),
                                ),
                            )
                        }
                    }
                }
                add(
                    DecisionRecommendation(
                        itemId = rec.getInt("item_id"),
                        itemName = rec.getString("item_name"),
                        coveredNeeds = covered,
                        purchaseStatus = rec.getString("purchase_status"),
                        nextItemName = if (rec.isNull("next_item_name")) null else rec.getString("next_item_name"),
                        replaceItemId = if (rec.isNull("replace_item_id")) null else rec.getInt("replace_item_id"),
                        evidence = rec.getString("evidence"),
                        functionExplanation = functions,
                        itemPrice = if (rec.has("item_price") && !rec.isNull("item_price")) rec.getInt("item_price") else null,
                        componentPath = components,
                        whyNow = if (rec.has("why_now") && !rec.isNull("why_now")) rec.getString("why_now") else "",
                    ),
                )
            }
        }
        val emergency = if (root.has("emergency_swap") && !root.isNull("emergency_swap")) {
            val obj = root.getJSONObject("emergency_swap")
            val suggestions = buildList {
                val arr = obj.getJSONArray("suggestions")
                for (i in 0 until arr.length()) {
                    val s = arr.getJSONObject(i)
                    val constraints = buildList {
                        val cArr = s.getJSONArray("constraints")
                        for (j in 0 until cArr.length()) add(cArr.getString(j))
                    }
                    add(
                        EmergencySwapSuggestion(
                            action = s.getString("action"),
                            targetItemId = s.getInt("target_item_id"),
                            targetItemName = s.getString("target_item_name"),
                            cost = s.getInt("cost"),
                            reason = s.getString("reason"),
                            whyNow = s.getString("why_now"),
                            evidence = s.getString("evidence"),
                            constraints = constraints,
                            replaceItemId = if (s.isNull("replace_item_id")) null else s.getInt("replace_item_id"),
                        ),
                    )
                }
            }
            val warnings = buildList {
                val arr = obj.getJSONArray("warnings")
                for (i in 0 until arr.length()) add(arr.getString(i))
            }
            EmergencySwapAdvice(
                suggestions = suggestions,
                remainingGold = obj.getInt("remaining_gold"),
                inventorySlotsFree = obj.getInt("inventory_slots_free"),
                reviveUsesRemaining = if (obj.isNull("revive_uses_remaining")) null else obj.getInt("revive_uses_remaining"),
                warnings = warnings,
            )
        } else {
            null
        }
        return DecisionResponse(
            priorityNeeds = needs,
            threatCounts = threats,
            unknownHeroIds = unknown,
            recommendations = recs,
            emergencySwap = emergency,
        )
    }
}
