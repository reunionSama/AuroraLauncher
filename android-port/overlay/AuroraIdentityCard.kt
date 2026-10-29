/* Copyright (C) 2026 reunionSama. SPDX-License-Identifier: GPL-3.0-or-later */
package com.movtery.zalithlauncher.ui.screens.content.aurora

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import com.movtery.zalithlauncher.BuildConfig
import com.movtery.zalithlauncher.R

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun AuroraIdentityCard(modifier: Modifier = Modifier, openLink: (String) -> Unit) {
    Column(modifier.fillMaxWidth().background(Brush.horizontalGradient(listOf(Color(0xFF101F2B), Color(0xFF17463F))), RoundedCornerShape(24.dp)).padding(22.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Image(painterResource(R.drawable.img_launcher), contentDescription = "Aurora", modifier = Modifier.size(56.dp))
        Text("AuroraLauncher", color = Color.White, style = MaterialTheme.typography.headlineMedium)
        Text("让每次出发更从容 · ${BuildConfig.VERSION_NAME}", color = Color(0xFF9CE8DA))
        Text("Aurora 项目维护：reunionSama\nAurora 特色：极光主页、可旋转角色、20 种动作、个性化选项、工具中心及应用内更新。", color = Color.White, style = MaterialTheme.typography.bodyMedium)
        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FilledTonalButton(onClick = { openLink("https://github.com/reunionSama/AuroraLauncher-Android") }) { Text("项目主页") }
            AuroraUpdateButton()
            FilledTonalButton(onClick = { openLink("https://ifdian.net/a/AuroraLauncher") }) { Text("赞助创作者") }
        }
        Text("Android 运行核心基于 Zalith Launcher 2 / PojavLauncher。下方独立列出原作者、贡献者与第三方许可，Aurora 的新增部分不改变其归属。", color = Color(0xFFBED8D6), style = MaterialTheme.typography.bodySmall)
    }
}


