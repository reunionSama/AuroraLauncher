/*
 * AuroraLauncher Android additions, Copyright (C) 2026 reunionSama.
 * SPDX-License-Identifier: GPL-3.0-or-later
 * New workspace and diagnostics UI over the credited Zalith/Pojav engine.
 */
package com.movtery.zalithlauncher.ui.screens.content.aurora

import android.app.ActivityManager
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.os.Build
import android.os.SystemClock
import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.movtery.zalithlauncher.BuildConfig
import com.movtery.zalithlauncher.game.account.AccountsManager
import com.movtery.zalithlauncher.game.version.installed.VersionsManager
import com.movtery.zalithlauncher.path.PathManager
import com.movtery.zalithlauncher.ui.base.BaseScreen
import com.movtery.zalithlauncher.ui.screens.NormalNavKey
import com.movtery.zalithlauncher.ui.screens.TitledNavKey
import kotlinx.coroutines.*
import java.io.File
import java.io.RandomAccessFile
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest
import java.text.DateFormat
import java.util.Date

private val AuroraTeal = Color(0xFF58DEC8)
private val AuroraNight = Color(0xFF101F2B)

internal data class Check(val name: String, val detail: String, val ok: Boolean)
internal data class Probe(val name: String, val detail: String, val ok: Boolean)

@Composable
fun AuroraToolsScreen(
    currentKey: TitledNavKey?,
    onShortcut: (String) -> Unit,
    onLaunch: () -> Unit,
    onOpenLog: (String) -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val version by VersionsManager.currentVersion.collectAsStateWithLifecycle()
    val account by AccountsManager.currentAccountFlow.collectAsStateWithLifecycle()
    val allVersions by VersionsManager.versions.collectAsStateWithLifecycle()
    var tab by rememberSaveable { mutableStateOf(0) }
    var query by rememberSaveable { mutableStateOf("") }
    var checks by remember { mutableStateOf<List<Check>>(emptyList()) }
    var checksBusy by remember { mutableStateOf(false) }
    var probes by remember { mutableStateOf<List<Probe>>(emptyList()) }
    var probing by remember { mutableStateOf(false) }
    var checkedAt by rememberSaveable { mutableStateOf("") }
    val prefs = remember { context.getSharedPreferences("aurora_workspace", Context.MODE_PRIVATE) }
    var favorites by remember { mutableStateOf(prefs.getStringSet("favorites", setOf("versions", "mods", "java"))!!.toSet()) }
    val versionPath = version?.getVersionPath()?.absolutePath.orEmpty()
    val noteKey = remember(versionPath) { "note_" + MessageDigest.getInstance("SHA-256").digest(versionPath.toByteArray()).joinToString("") { "%02x".format(it) } }
    var note by remember(noteKey) { mutableStateOf(prefs.getString(noteKey, "").orEmpty()) }
    var noteSaved by remember(noteKey) { mutableStateOf(true) }
    var clipboardMessage by remember { mutableStateOf("") }
    var logText by remember { mutableStateOf("") }
    var paused by rememberSaveable { mutableStateOf(false) }
    var logFilter by rememberSaveable { mutableStateOf("") }
    val logFile = remember(version) { version?.getLatestLog() }
    val selectedVersion = version

    fun copyReport(text: String) {
        val cm = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        cm.setPrimaryClip(ClipData.newPlainText("Aurora diagnostics", text))
        clipboardMessage = "已复制，可粘贴到反馈中"
    }

    // A check result is scoped to the selected version; never show stale green checks.
    LaunchedEffect(version, account) { checks = emptyList(); checkedAt = "" }

    BaseScreen(screenKey = NormalNavKey.AuroraTools, currentKey = currentKey) { isVisible ->
        // Read only a bounded tail; polling stops immediately when hidden/paused.
        LaunchedEffect(tab, paused, logFile, isVisible) {
            if (tab == 3 && !paused && isVisible) {
                while (isActive) {
                    logText = withContext(Dispatchers.IO) { readLogTail(logFile) }
                    delay(2000)
                }
            }
        }
        Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Column(Modifier.fillMaxWidth().background(Brush.horizontalGradient(listOf(AuroraNight, Color(0xFF17463F))), RoundedCornerShape(24.dp)).padding(20.dp)) {
                Text("A U R O R A   /   工具中心", color = AuroraTeal, style = MaterialTheme.typography.labelLarge)
                Spacer(Modifier.height(8.dp))
                Text("让每次出发更从容", color = Color.White, style = MaterialTheme.typography.headlineSmall)
                Text("${version?.getVersionName() ?: "尚未选择游戏"}  ·  ${allVersions.size} 个已安装版本  ·  ${if (account != null) "已选择账号" else "尚未选择账号"}", color = Color(0xFFBED8D6), style = MaterialTheme.typography.bodyMedium)
            }
            Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf("我的工作台", "启动前检查", "网络诊断", "日志速览").forEachIndexed { index, label ->
                    FilterChip(selected = tab == index, onClick = { tab = index; clipboardMessage = "" }, label = { Text(label) })
                }
            }
            when (tab) {
                0 -> {
                    Text("常用功能，由你安排", style = MaterialTheme.typography.titleLarge)
                    Text("点按打开，点星号收藏。所有原有功能仍可从下载和设置访问。", style = MaterialTheme.typography.bodySmall)
                    OutlinedTextField(value = query, onValueChange = { query = it }, modifier = Modifier.fillMaxWidth(), singleLine = true, label = { Text("查找功能：模组、Java、陶瓦、触控…") })
                    val items = listOf(
                        Triple("versions", "版本管理", "安装实例与独立配置"), Triple("mods", "模组与资源", "搜索和安装模组、整合包"),
                        Triple("download", "游戏下载", "游戏版本与加载器"), Triple("multiplayer", "陶瓦联机", "保留原有组队功能"),
                        Triple("java", "Java 运行时", "查看、安装和切换 Java"), Triple("renderer", "图形与渲染", "驱动、渲染器与兼容性"),
                        Triple("game", "游戏设置", "内存、启动参数与窗口"), Triple("control", "触控设置", "按键、手势与操作体验"),
                        Triple("gamepad", "手柄设置", "手柄映射与输入"), Triple("layouts", "控制布局", "管理与编辑触控布局"),
                        Triple("launcher", "外观与启动器", "背景、主题和行为"), Triple("account", "账号管理", "微软和其他受支持账号"),
                        Triple("files", "文件管理", "浏览文件、导入和导出"), Triple("about", "关于 Aurora", "维护者、来源与开源许可")
                    ).filter { query.isBlank() || (it.second + it.third + it.first).contains(query, ignoreCase = true) }
                        .sortedByDescending { it.first in favorites }
                    if (items.isEmpty()) Text("没有匹配项，试试其他关键词。")
                    BoxWithConstraints {
                        val columns = if (maxWidth >= 620.dp) 3 else if (maxWidth >= 380.dp) 2 else 1
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            items.chunked(columns).forEach { row ->
                                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    row.forEach { (id, title, summary) ->
                                        Surface(onClick = { onShortcut(id) }, modifier = Modifier.weight(1f), shape = RoundedCornerShape(18.dp), color = MaterialTheme.colorScheme.surfaceContainerHigh) {
                                            Column(Modifier.padding(14.dp)) {
                                                Row(verticalAlignment = Alignment.CenterVertically) {
                                                    Text(title, Modifier.weight(1f), style = MaterialTheme.typography.titleSmall)
                                                    TextButton(onClick = {
                                                        favorites = if (id in favorites) favorites - id else favorites + id
                                                        prefs.edit().putStringSet("favorites", favorites).apply()
                                                    }, contentPadding = PaddingValues(0.dp), modifier = Modifier.size(40.dp)) {
                                                        Text(if (id in favorites) "★" else "☆")
                                                    }
                                                }
                                                Text(summary, style = MaterialTheme.typography.bodySmall)
                                            }
                                        }
                                    }
                                    repeat(columns - row.size) { Spacer(Modifier.weight(1f)) }
                                }
                            }
                        }
                    }
                    AuroraPanel("实例备忘") {
                        Text("为当前实例保存自己的整合包说明、联机约定或待办，仅保存在本机。", style = MaterialTheme.typography.bodySmall)
                        OutlinedTextField(value = note, onValueChange = { note = it.take(4000); noteSaved = false }, enabled = version != null, modifier = Modifier.fillMaxWidth(), minLines = 2, maxLines = 5, label = { Text("${version?.getVersionName() ?: "先选择一个实例"} 的备忘") })
                        Button(enabled = version != null && !noteSaved, onClick = { prefs.edit().putString(noteKey, note).apply(); noteSaved = true }) { Text(if (noteSaved) "已保存" else "保存备忘") }
                    }
                }
                1 -> {
                    AuroraPanel("出发前，快速检查一次") {
                        Text("检查当前设备和所选实例的基本条件。此检查不会下载或修改文件，也不替代启动器原有的依赖完整性检查。")
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Button(enabled = !checksBusy, onClick = {
                                checksBusy = true
                                scope.launch {
                                    try {
                                        val result = withContext(Dispatchers.IO) { collectChecks(context, selectedVersion, account != null) }
                                        if (VersionsManager.currentVersion.value == selectedVersion) {
                                            checks = result
                                            checkedAt = DateFormat.getTimeInstance().format(Date())
                                        }
                                    } finally { checksBusy = false }
                                }
                            }) { Text(if (checksBusy) "检查中…" else "检查当前实例") }
                            OutlinedButton(enabled = version != null, onClick = onLaunch) { Text("使用原有启动流程") }
                        }
                        if (checkedAt.isNotEmpty()) Text("检查时间 $checkedAt", style = MaterialTheme.typography.labelSmall)
                    }
                    checks.forEach { check -> StatusCard(check.name, check.detail, check.ok) }
                    if (checks.isNotEmpty()) OutlinedButton(onClick = {
                        copyReport("Aurora ${BuildConfig.VERSION_NAME}\nAndroid ${Build.VERSION.RELEASE}; ABI ${Build.SUPPORTED_ABIS.joinToString()}\n" + checks.joinToString("\n") { "${if(it.ok) "OK" else "请检查"} ${it.name}: ${it.detail}" })
                    }) { Text("复制检查报告") }
                }
                2 -> {
                    AuroraPanel("看看请求卡在哪里") {
                        Text("分别检测 Modrinth、官方版本列表、镜像列表和微软登录服务。显示的是小请求响应时间，不能代表大文件下载速度。")
                        Button(enabled = !probing, onClick = {
                            probing = true; probes = emptyList()
                            scope.launch {
                                try {
                                    probes = coroutineScope {
                                        listOf(
                                            "Modrinth" to "https://api.modrinth.com/v2/tag/game_version",
                                            "Mojang 版本列表" to "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json",
                                            "BMCLAPI 版本列表" to "https://bmclapi2.bangbang93.com/mc/game/version_manifest_v2.json",
                                            "微软登录" to "https://login.microsoftonline.com/consumers/v2.0/.well-known/openid-configuration"
                                        ).map { (name, url) -> async(Dispatchers.IO) { probe(name, url) } }.awaitAll()
                                    }
                                } finally { probing = false }
                            }
                        }) { Text(if (probing) "正在检测 4 个服务…" else "开始网络诊断") }
                        if (probing) LinearProgressIndicator(Modifier.fillMaxWidth())
                    }
                    probes.forEach { StatusCard(it.name, it.detail, it.ok) }
                    if (probes.isNotEmpty()) {
                        Text("建议：单一服务失败时，检查该平台服务与代理设置；全部失败时，检查网络、DNS、系统时间和 VPN。微软服务可达不等于账号认证成功。", style = MaterialTheme.typography.bodySmall)
                        OutlinedButton(onClick = { copyReport("Aurora 网络诊断\n" + probes.joinToString("\n") { "${it.name}: ${it.detail}" }) }) { Text("复制网络报告") }
                    }
                }
                3 -> {
                    AuroraPanel("看清这次启动发生了什么") {
                        Text("只读取当前实例日志末尾，最多 96 KiB / 160 行，每 2 秒刷新。原有完整日志查看器继续保留。", style = MaterialTheme.typography.bodySmall)
                        Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            OutlinedButton(onClick = { paused = !paused }) { Text(if (paused) "继续刷新" else "暂停刷新") }
                            OutlinedButton(enabled = logFile != null, onClick = { logFile?.let { onOpenLog(it.absolutePath) } }) { Text("完整日志") }
                        }
                        OutlinedTextField(value = logFilter, onValueChange = { logFilter = it }, modifier = Modifier.fillMaxWidth(), singleLine = true, label = { Text("筛选日志，如 ERROR、WARN、异常关键词") })
                        val hint = logHint(logText)
                        if (hint.isNotEmpty()) Text("排查线索：$hint", color = MaterialTheme.colorScheme.primary)
                        SelectionContainer {
                            Text(if (logFilter.isBlank()) logText.ifEmpty { "还没有日志，先启动一次游戏。" } else logText.lineSequence().filter { it.contains(logFilter, true) }.joinToString("\n").ifEmpty { "没有匹配行" }, fontFamily = FontFamily.Monospace, style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
            }
            if (clipboardMessage.isNotEmpty()) Text(clipboardMessage, color = MaterialTheme.colorScheme.primary)
            Text("Aurora 的界面与工具扩展 · Android 游戏运行核心基于 Zalith Launcher 2 / PojavLauncher，完整署名和许可见关于页。", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
internal fun AuroraPanel(title: String, content: @Composable ColumnScope.() -> Unit) {
    Surface(shape = RoundedCornerShape(22.dp), color = MaterialTheme.colorScheme.surfaceContainer) {
        Column(Modifier.fillMaxWidth().padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium)
            content()
        }
    }
}

@Composable
private fun StatusCard(name: String, detail: String, ok: Boolean) {
    Surface(shape = RoundedCornerShape(16.dp), color = if (ok) MaterialTheme.colorScheme.secondaryContainer else MaterialTheme.colorScheme.errorContainer) {
        Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text("${if (ok) "✓" else "!"}  $name", style = MaterialTheme.typography.titleSmall)
            Text(detail, style = MaterialTheme.typography.bodySmall)
        }
    }
}

private fun collectChecks(context: Context, version: com.movtery.zalithlauncher.game.version.installed.Version?, hasAccount: Boolean): List<Check> {
    val memory = ActivityManager.MemoryInfo()
    (context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager).getMemoryInfo(memory)
    val freeMB = memory.availMem / 1048576
    val freeDiskMB = context.filesDir.usableSpace / 1048576
    val allocation = version?.getRamAllocation(context) ?: 0
    val runtimeCount = PathManager.DIR_MULTIRT.listFiles()?.count { it.isDirectory } ?: 0
    return listOf(
        Check("运行架构", Build.SUPPORTED_ABIS.joinToString(), Build.SUPPORTED_ABIS.contains("arm64-v8a")),
        Check("游戏实例", if (version?.isValid() == true) "已选实例的基础描述有效；完整依赖由原有启动流程校验。" else "请先安装或选择一个有效版本。", version?.isValid() == true),
        Check("账号选择", if (hasAccount) "已选择账号，在线账号仍需登录服务验证。" else "请前往账号管理选择或登录账号。", hasAccount),
        Check("可用内存", "当前约 ${freeMB} MiB；实例分配 ${allocation} MiB。建议给 Android 和图形驱动留出空间。", allocation > 0 && allocation + 512 <= freeMB),
        Check("存储空间", "应用内部存储剩余约 ${freeDiskMB} MiB；大型整合包需要更多空间。", freeDiskMB >= 2048),
        Check("Java 运行时目录", "检测到 $runtimeCount 个运行时目录；兼容版本请在 Java 管理中确认。", runtimeCount > 0)
    )
}

internal fun probe(name: String, url: String): Probe {
    val start = SystemClock.elapsedRealtime()
    var connection: HttpURLConnection? = null
    return try {
        connection = URL(url).openConnection() as HttpURLConnection
        connection.connectTimeout = 5000; connection.readTimeout = 5000
        connection.useCaches = false
        connection.setRequestProperty("User-Agent", "AuroraLauncher/alpha3 (https://github.com/reunionSama/AuroraLauncher)")
        val status = connection.responseCode
        val elapsed = SystemClock.elapsedRealtime() - start
        Probe(name, "HTTP $status · ${elapsed} ms" + if (status in 200..299) " · 请求可达" else " · 服务返回错误，检查平台限制或稍后重试", status in 200..299)
    } catch (e: Exception) {
        Probe(name, when (e) {
            is java.net.UnknownHostException -> "DNS 解析失败，检查网络或 DNS。"
            is java.net.SocketTimeoutException -> "连接或响应超时，检查网络与代理。"
            is javax.net.ssl.SSLException -> "TLS 握手失败，检查系统时间与证书。"
            else -> "请求失败：${e.javaClass.simpleName}"
        }, false)
    } finally { connection?.disconnect() }
}

internal fun readLogTail(file: File?): String {
    if (file == null || !file.isFile) return "还没有当前实例的日志，先启动一次游戏。"
    return runCatching {
        RandomAccessFile(file, "r").use { input ->
            val length = input.length(); val start = (length - 96 * 1024).coerceAtLeast(0)
            input.seek(start)
            val bytes = ByteArray((length - start).toInt()); input.readFully(bytes)
            val raw = bytes.toString(Charsets.UTF_8)
            val complete = if (start > 0) raw.substringAfter('\n', "") else raw
            redact(complete.lineSequence().toList().takeLast(160).joinToString("\n"))
        }
    }.getOrElse { "暂时无法读取日志：${it.javaClass.simpleName}" }
}

internal fun redact(value: String): String = value
    .replace(Regex("(?i)(--(?:accessToken|clientToken|username|uuid)\\s+)([^\\s]+)"), "$1[已隐藏]")
    .replace(Regex("""(?i)(["']?(?:access_token|refresh_token|client_token|authorization|password)["']?\s*[=:]\s*["']?)(?:Bearer\s+)?[^\s,}"']+"""), "$1[已隐藏]")
    .replace(Regex("eyJ[A-Za-z0-9_-]{10,}\\.[A-Za-z0-9_-]+\\.[A-Za-z0-9_-]+"), "[已隐藏令牌]")
    .replace(Regex("[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}"), "[已隐藏邮箱]")

internal fun logHint(text: String): String = when {
    text.contains("OutOfMemoryError", true) -> "可能内存不足：检查实例内存分配、整合包大小和后台应用。"
    text.contains("UnsupportedClassVersionError", true) -> "可能 Java 版本不匹配：到 Java 管理选择该游戏要求的运行时。"
    text.contains("SSLHandshakeException", true) -> "可能 TLS 连接异常：检查系统时间、证书和代理。"
    text.contains("UnknownHostException", true) -> "可能 DNS 解析失败：检查网络和 DNS。"
    text.contains("NoClassDefFoundError", true) -> "可能缺少依赖或模组不兼容：查看完整日志中最早的异常。"
    else -> ""
}


