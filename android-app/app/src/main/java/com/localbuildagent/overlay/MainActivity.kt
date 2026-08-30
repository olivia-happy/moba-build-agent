
package com.localbuildagent.overlay

import android.app.Activity
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.media.projection.MediaProjectionManager
import android.net.Uri
import android.os.Bundle
import android.provider.Settings
import androidx.core.content.ContextCompat
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import java.io.File
import kotlin.concurrent.thread

/**
 * Local-first in-match build assistant.
 *
 * Flow: player taps the floating ball (or the in-app button) -> exactly one
 * MediaProjection frame is captured and reduced to an on-device luminance
 * summary -> five enemy portrait crops are matched locally against the bundled
 * fingerprint index -> the player confirms or corrects every hero -> only then
 * does the app call the user's own FastAPI service for evidence-bearing build
 * advice.
 *
 * The app never captures automatically, never records video, never sends the
 * full frame anywhere, and never makes a purchase or controls the game.
 */
class MainActivity : ComponentActivity() {

    private var indexHash by mutableStateOf("")
    private var indexLoaded by mutableStateOf(false)
    private var slotCandidates by mutableStateOf<List<List<HeroPortraitMatch>>>(emptyList())
    private var lastDraft by mutableStateOf<ScreenStateDraft?>(null)
    private var stageMessage by mutableStateOf("截图只在你主动点击后执行，应用不会自动购买或操控游戏。")
    private var showReview by mutableStateOf(false)
    private var decisionHtml by mutableStateOf("")

    private val captureLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult(),
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK && result.data != null) {
            startService(
                Intent(this, SingleFrameCaptureService::class.java)
                    .putExtra(SingleFrameCaptureService.RESULT_CODE, result.resultCode)
                    .putExtra(SingleFrameCaptureService.RESULT_DATA, result.data),
            )
            stageMessage = "正在截取一帧。完成后会立即停止共享，并进入识别确认。"
        } else {
            stageMessage = "未取得截图授权，未读取任何游戏画面。"
        }
    }

    private val frameReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            val frameName = intent?.getStringExtra(SingleFrameCaptureService.FRAME_FILE_EXTRA)
                ?: SingleFrameCaptureService.FRAME_FILE
            stageMessage = "画面已就绪，正在本地识别敌方阵容…"
            analyzeFrameAsync(File(cacheDir, frameName))
        }
    }

    companion object {
        const val CAPTURE_TRIGGER_EXTRA = "capture_trigger"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        indexHash = PortraitIndexStore.load(this)?.contentHash ?: ""
        indexLoaded = PortraitIndexStore.load(this) != null
        ContextCompat.registerReceiver(this, frameReceiver, IntentFilter(SingleFrameCaptureService.ACTION_NOTIFY_ANALYZED), ContextCompat.RECEIVER_NOT_EXPORTED)
        if (intent?.getStringExtra(CAPTURE_TRIGGER_EXTRA) == CaptureTrigger.PlayerTappedOverlay::class.simpleName) {
            val manager = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
            captureLauncher.launch(manager.createScreenCaptureIntent())
        }
        setContent { AppUi() }
    }

    override fun onDestroy() {
        unregisterReceiver(frameReceiver)
        super.onDestroy()
    }

    private fun analyzeFrameAsync(frameFile: File) {
        thread {
            val index = PortraitIndexStore.load(this@MainActivity) ?: return@thread
            val matcher = HeroPortraitMatcher.fromIndex(index)
            val results = FrameAnalyzer.analyze(
                frameFile = frameFile,
                layout = HeroSelectLayout.default,
                matcher = matcher,
            )
            frameFile.delete()
            runOnUiThread {
                val candidates = results.map { it.candidates }
                slotCandidates = candidates
                lastDraft = ScreenStateDraft(
                    gold = 0,
                    enemyHeroIds = candidates.map { it.firstOrNull()?.heroId ?: 0 },
                    ownedItemIds = emptyList(),
                    playerConfirmed = false,
                )
                showReview = true
                stageMessage = "识别完成，请核对每一位英雄后再获取建议。"
            }
        }
    }

    private fun requestDecision(draft: ScreenStateDraft) {
        stageMessage = "正在向本地 FastAPI 服务请求出装建议…"
        thread {
            val responseText = try {
                LocalDecisionClient().request(draft)
            } catch (error: Exception) {
                runOnUiThread { stageMessage = "本地服务不可用：" + error.message }
                return@thread
            }
            val response = DecisionResponseParser.parse(responseText)
            runOnUiThread {
                showReview = false
                decisionHtml = renderDecision(response)
                stageMessage = "已生成出装建议（含证据）。"
            }
        }
    }

    private fun renderDecision(response: DecisionResponse): String {
        val sb = StringBuilder()
        sb.append("出装建议（本地规则引擎）\n\n")
        sb.append("优先级需求：" + response.priorityNeeds.joinToString("、").ifBlank { "无" } + "\n")
        sb.append("威胁统计：" + response.threatCounts.entries.joinToString("；") { entry -> entry.key + "×" + entry.value }.ifBlank { "无" } + "\n")
        sb.append("未识别英雄：" + response.unknownHeroIds.joinToString().ifBlank { "无" } + "\n\n")
        response.recommendations.forEachIndexed { index, rec ->
            sb.append((index + 1).toString() + ". " + rec.itemName + "（" + rec.purchaseStatus + "）")
            rec.itemPrice?.let { sb.append("　" + it.toString() + " 金币") }
            sb.append("\n")
            sb.append("   覆盖需求：" + rec.coveredNeeds.joinToString("、").ifBlank { "无" } + "\n")
            if (rec.functionExplanation.isNotEmpty()) {
                sb.append("   功能：" + rec.functionExplanation.values.joinToString("、") + "\n")
            }
            if (rec.componentPath.isNotEmpty()) {
                sb.append("   组件：" + rec.componentPath.joinToString(" → ") { comp -> comp.name + "(" + comp.price + "金)" } + "\n")
            }
            rec.nextItemName?.let { sb.append("   下一步：" + it + "\n") }
            rec.replaceItemId?.let { sb.append("   可替换装备 ID：" + it.toString() + "\n") }
            if (rec.whyNow.isNotBlank()) {
                sb.append("   为什么买：" + rec.whyNow + "\n")
            }
            sb.append("   证据：" + rec.evidence + "\n\n")
        }
        response.emergencySwap?.let { swap ->
            sb.append("紧急秒换建议\n")
            if (swap.warnings.isNotEmpty()) {
                sb.append("提示：" + swap.warnings.joinToString("；") + "\n")
            }
            swap.suggestions.forEach { s ->
                sb.append("  " + s.action + " " + s.targetItemName + "（" + s.cost.toString() + " 金币）\n")
                sb.append("   原因：" + s.reason + "\n")
                sb.append("   为什么：" + s.whyNow + "\n")
                if (s.constraints.isNotEmpty()) {
                    sb.append("   限制：" + s.constraints.joinToString("；") + "\n")
                }
                s.replaceItemId?.let { sb.append("   替换装备 ID：" + it.toString() + "\n") }
                sb.append("   证据：" + s.evidence + "\n\n")
            }
            swap.reviveUsesRemaining?.let { sb.append("复活甲剩余次数：" + it.toString() + "\n") }
            sb.append("剩余金币：" + swap.remainingGold.toString() + "；空格子：" + swap.inventorySlotsFree.toString() + "\n")
        }
        return sb.toString()
    }

    @Composable
    private fun AppUi() {
        MaterialTheme {
            Column(
                modifier = Modifier.fillMaxSize().padding(24.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                Text("局内出装助手", style = MaterialTheme.typography.headlineMedium)
                Text(
                    "英雄识别索引：" + if (indexLoaded) "已加载（hash: " + indexHash + "）" else "未加载，请先构建并同步 assets",
                    style = MaterialTheme.typography.bodySmall,
                )
                Text(stageMessage)

                if (showReview && lastDraft != null) {
                    ReviewScreen(
                        initialDraft = lastDraft!!,
                        slotCandidates = slotCandidates,
                        indexHash = indexHash,
                        onRequestDecision = ::requestDecision,
                    )
                }

                if (decisionHtml.isNotBlank()) {
                    Text(decisionHtml, style = MaterialTheme.typography.bodyMedium)
                    Button(onClick = { decisionHtml = "" }) { Text("返回重新识别") }
                }

                if (!showReview && decisionHtml.isBlank()) {
                    Button(onClick = {
                        if (!Settings.canDrawOverlays(this@MainActivity)) {
                            startActivity(
                                Intent(
                                    Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                                    Uri.parse("package:" + packageName),
                                ),
                            )
                            stageMessage = "请开启悬浮窗权限后返回，再启动悬浮球。"
                        } else {
                            startService(Intent(this@MainActivity, OverlayService::class.java))
                            stageMessage = "悬浮球已启动；点它后会请求一次截图授权并识别当前画面。"
                        }
                    }) {
                        Text("启动悬浮球")
                    }
                    Button(onClick = {
                        val manager = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
                        captureLauncher.launch(manager.createScreenCaptureIntent())
                    }) {
                        Text("识别当前画面")
                    }
                }
            }
        }
    }
}
