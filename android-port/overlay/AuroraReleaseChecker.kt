/* Copyright (C) 2026 reunionSama. SPDX-License-Identifier: GPL-3.0-or-later */
package com.movtery.zalithlauncher.ui.screens.content.aurora

import android.app.AlertDialog
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.widget.Toast
import com.movtery.zalithlauncher.BuildConfig
import kotlinx.coroutines.*
import kotlinx.serialization.json.*
import java.net.HttpURLConnection
import java.net.URL

internal data class AuroraRelease(val alpha: Int, val page: String)
private const val AURORA_REPO = "https://github.com/reunionSama/AuroraLauncher"

/** Only Aurora's explicit ARM64 Android channel is eligible; ignore Windows/upstream assets. */
internal fun newerAuroraRelease(body: String, currentAlpha: Int): AuroraRelease? {
    val releases = Json.parseToJsonElement(body).jsonArray
    return releases.flatMap { value ->
        val release = value.jsonObject
        if (release["draft"]?.jsonPrimitive?.booleanOrNull == true) return@flatMap emptyList()
        val page = release["html_url"]?.jsonPrimitive?.content.orEmpty()
        if (!page.startsWith("$AURORA_REPO/releases/tag/")) return@flatMap emptyList()
        release["assets"]?.jsonArray.orEmpty().mapNotNull { element ->
            val asset = element.jsonObject
            val name = asset["name"]?.jsonPrimitive?.content.orEmpty()
            val download = asset["browser_download_url"]?.jsonPrimitive?.content.orEmpty()
            val match = Regex("AuroraLauncher-Android-arm64-alpha(\\d+)\\.apk", RegexOption.IGNORE_CASE).matchEntire(name)
            val alpha = match?.groupValues?.get(1)?.toIntOrNull()
            if (alpha != null && alpha > currentAlpha && download.startsWith("$AURORA_REPO/releases/download/")) AuroraRelease(alpha, page) else null
        }
    }.maxByOrNull { it.alpha }
}

/** Lifecycle-scoped, silent unless a compatible named channel update is published. */
fun checkAuroraUpdate(context: Context, scope: CoroutineScope, force: Boolean = false) {
    val prefs = context.getSharedPreferences("aurora_workspace", Context.MODE_PRIVATE)
    val now = System.currentTimeMillis()
    val previous = prefs.getLong("release_check", 0L)
    if (!force && now >= previous && now - previous < 3600000L) return
    scope.launch {
        val currentAlpha = Regex("alpha(\\d+)").find(BuildConfig.VERSION_NAME)?.groupValues?.get(1)?.toIntOrNull() ?: 3
        val result = withContext(Dispatchers.IO) {
            runCatching {
                val connection = URL("https://api.github.com/repos/reunionSama/AuroraLauncher/releases?per_page=10").openConnection() as HttpURLConnection
                try {
                    connection.connectTimeout = 5000; connection.readTimeout = 5000
                    connection.setRequestProperty("User-Agent", "AuroraLauncher/alpha3")
                    connection.setRequestProperty("Accept", "application/vnd.github+json")
                    check(connection.responseCode == 200) { "HTTP ${connection.responseCode}" }
                    val bytes = connection.inputStream.use { input ->
                        val output = java.io.ByteArrayOutputStream()
                        val buffer = ByteArray(8192)
                        while (true) {
                            val n = input.read(buffer); if (n < 0) break
                            check(output.size() + n <= 2 * 1024 * 1024) { "Release response too large" }
                            output.write(buffer, 0, n)
                        }
                        output.toByteArray()
                    }
                    newerAuroraRelease(bytes.toString(Charsets.UTF_8), currentAlpha)
                } finally { connection.disconnect() }
            }
        }
        if (result.isSuccess) prefs.edit().putLong("release_check", now).apply()
        val release = result.getOrNull()
        if (release != null) {
            AlertDialog.Builder(context).setTitle("Aurora Alpha${release.alpha} 可用")
                .setMessage("发现 Aurora 安卓 ARM64 渠道的新安装包，可前往项目发布页查看说明。")
                .setNegativeButton("稍后", null)
                .setPositiveButton("查看更新") { _, _ -> context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(release.page))) }
                .show()
        } else if (force) {
            Toast.makeText(context, if (result.isSuccess) "未发现此 ARM64 Alpha 渠道的新安装包" else "暂时无法检查更新，请稍后重试", Toast.LENGTH_LONG).show()
        }
    }
}
