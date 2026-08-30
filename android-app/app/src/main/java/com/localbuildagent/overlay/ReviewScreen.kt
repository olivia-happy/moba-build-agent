
package com.localbuildagent.overlay

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

/**
 * Player-facing review step. Recognition results are ALWAYS shown with
 * confidence and candidate alternatives; the player confirms or corrects
 * before any build advice is requested. Manual hero IDs are accepted so a
 * wrong recognition never silently reaches the decision agent.
 */
@Composable
fun ReviewScreen(
    initialDraft: ScreenStateDraft,
    slotCandidates: List<List<HeroPortraitMatch>>,
    indexHash: String,
    onRequestDecision: (ScreenStateDraft) -> Unit,
) {
    var confirmed by remember { mutableStateOf(false) }
    var goldText by remember { mutableStateOf(initialDraft.gold.toString()) }
    var enemyHeroIds by remember { mutableStateOf(initialDraft.enemyHeroIds.toMutableList()) }
    var ownedItemIds by remember { mutableStateOf(initialDraft.ownedItemIds.toMutableList()) }
    var ownedItemsText by remember { mutableStateOf(initialDraft.ownedItemIds.joinToString()) }
    var reviveUsesText by remember { mutableStateOf(initialDraft.reviveUsesUsed.toString()) }

    val gold = goldText.toIntOrNull() ?: initialDraft.gold
    val reviveUses = reviveUsesText.toIntOrNull() ?: initialDraft.reviveUsesUsed
    val draft = ScreenStateDraft(
        gold = gold,
        enemyHeroIds = enemyHeroIds,
        ownedItemIds = ownedItemIds,
        playerConfirmed = confirmed,
        reviveUsesUsed = reviveUses,
        slotCapacity = initialDraft.slotCapacity,
        needsTenacity = initialDraft.needsTenacity,
    )

    LazyColumn(
        modifier = Modifier.fillMaxWidth().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Text("确认识别结果", style = MaterialTheme.typography.headlineSmall)
            Text(
                "识别只是候选，请核对每个位置的英雄；认错时点下方候选或手动输入英雄 ID。",
                style = MaterialTheme.typography.bodyMedium,
            )
        }
        itemsIndexed(slotCandidates) { index, candidates ->
            if (index < enemyHeroIds.size) {
                ReviewSlotRow(
                    slotIndex = index,
                    selectedHeroId = enemyHeroIds[index],
                    candidates = candidates,
                    onSelect = { heroId -> enemyHeroIds[index] = heroId },
                    onManualHeroId = { heroId -> enemyHeroIds[index] = heroId },
                )
            }
        }
        item {
            OutlinedTextField(
                value = goldText,
                onValueChange = { goldText = it.filter { c -> c.isDigit() } },
                label = { Text("当前金币") },
                singleLine = true,
            )
        }
        item {
            OutlinedTextField(
                value = ownedItemsText,
                onValueChange = { ownedItemsText = it },
                label = { Text("已持有装备 ID（逗号分隔，可填 1423 冷静之靴等）") },
                singleLine = true,
            )
        }
        item {
            OutlinedTextField(
                value = reviveUsesText,
                onValueChange = { reviveUsesText = it.filter { c -> c.isDigit() } },
                label = { Text("复活甲已用次数") },
                singleLine = true,
            )
        }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = {
                    ownedItemIds = ownedItemsText.split(",").mapNotNull { it.trim().toIntOrNull() }.toMutableList()
                    confirmed = true
                }, enabled = !confirmed) {
                    Text(if (confirmed) "已核对" else "我确认阵容无误")
                }
                Button(
                    onClick = {
                        ownedItemIds = ownedItemsText.split(",").mapNotNull { it.trim().toIntOrNull() }.toMutableList()
                        onRequestDecision(draft)
                    },
                    enabled = DecisionRequestPolicy.canSend(draft),
                ) {
                    Text("获取本地出装建议")
                }
            }
        }
        item {
            Text(
                "已识别英雄 ID：" + enemyHeroIds.joinToString() + " ｜ 金币：" + gold,
                style = MaterialTheme.typography.bodySmall,
            )
            Text(
                "已持有装备：" + ownedItemIds.joinToString().ifBlank { "无" } + " ｜ 复活甲已用：" + reviveUses,
                style = MaterialTheme.typography.bodySmall,
            )
            Text(
                "识别索引 hash：" + indexHash,
                style = MaterialTheme.typography.bodySmall,
            )
        }
    }
}

@Composable
private fun ReviewSlotRow(
    slotIndex: Int,
    selectedHeroId: Int,
    candidates: List<HeroPortraitMatch>,
    onSelect: (Int) -> Unit,
    onManualHeroId: (Int) -> Unit,
) {
    var manualId by remember { mutableStateOf("") }
    Card(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("位置 " + (slotIndex + 1), style = MaterialTheme.typography.titleMedium)
            if (candidates.isEmpty()) {
                Text("未能识别到可靠候选，请手动输入英雄 ID。", style = MaterialTheme.typography.bodySmall)
            } else {
                candidates.forEach { candidate ->
                    val selected = candidate.heroId == selectedHeroId
                    Row(
                        modifier = Modifier.fillMaxWidth().clickable { onSelect(candidate.heroId) },
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        Text(
                            if (selected) "✓ " + candidate.heroName + "（" + candidate.heroId + "）" else candidate.heroName + "（" + candidate.heroId + "）",
                            style = if (selected) MaterialTheme.typography.titleSmall else MaterialTheme.typography.bodyMedium,
                        )
                        Text(
                            String.format("%.1f%%", candidate.confidence * 100),
                            style = MaterialTheme.typography.bodySmall,
                        )
                    }
                }
            }
            Row(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                OutlinedTextField(
                    value = manualId,
                    onValueChange = { manualId = it.filter { c -> c.isDigit() } },
                    label = { Text("手动英雄 ID") },
                    singleLine = true,
                )
                Button(
                    onClick = { manualId.toIntOrNull()?.let(onManualHeroId) },
                    enabled = manualId.toIntOrNull() != null,
                ) { Text("设为该位置") }
            }
        }
    }
}
