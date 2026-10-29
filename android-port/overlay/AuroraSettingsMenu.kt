/* Copyright (C) 2026 reunionSama. SPDX-License-Identifier: GPL-3.0-or-later */
package com.movtery.zalithlauncher.ui.screens.content.aurora

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.movtery.zalithlauncher.ui.screens.TitledNavKey
import com.movtery.zalithlauncher.ui.screens.content.elements.CategoryItem

/** Search changes visibility only: the complete original category list remains intact. */
@Composable
fun AuroraSettingsMenu(items: List<CategoryItem>, selected: TitledNavKey?, navigate: (TitledNavKey) -> Unit, modifier: Modifier = Modifier, title: String = "设置导航") {
    var query by rememberSaveable { mutableStateOf("") }
    Column(modifier.widthIn(min = 154.dp, max = 220.dp).fillMaxHeight().verticalScroll(rememberScrollState()).padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text("AURORA", color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.labelLarge)
        Text(title, style = MaterialTheme.typography.titleMedium)
        OutlinedTextField(value = query, onValueChange = { query = it }, singleLine = true, label = { Text("查找分类") }, modifier = Modifier.fillMaxWidth())
        var matches = 0
        items.forEach { item ->
            val title = stringResource(item.textRes)
            if (query.isBlank() || title.contains(query, true)) {
                matches++
                NavigationDrawerItem(label = { Text(title, style = MaterialTheme.typography.labelLarge) }, selected = selected == item.key, onClick = { navigate(item.key) }, icon = { item.icon() }, modifier = Modifier.fillMaxWidth())
            }
        }
        if (matches == 0) Text("没有匹配分类", style = MaterialTheme.typography.bodySmall)
        HorizontalDivider(Modifier.padding(vertical = 8.dp))
        Text("分类搜索仅筛选入口\n原有功能与高级选项均保留", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

