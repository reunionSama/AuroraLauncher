/* Copyright (C) 2026 reunionSama. SPDX-License-Identifier: GPL-3.0-or-later */
package com.movtery.zalithlauncher.ui.screens.content.aurora

import android.content.SharedPreferences
import androidx.compose.foundation.background
import androidx.compose.ui.draw.drawWithCache
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.*
import androidx.compose.ui.graphics.drawscope.drawIntoCanvas
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.repeatOnLifecycle
import kotlinx.coroutines.delay
import kotlin.math.*

internal data class AuroraPreferences(val sky:Boolean=true,val actions:Boolean=true,val interval:Int=15,val brightness:Float=.7f,val speed:Float=.5f,val hue:Float=.4f,val high:Boolean=true,val autoDownload:Boolean=true)
@Composable internal fun rememberAuroraPreferences():AuroraPreferences {
 val c=LocalContext.current
 val p=remember { c.getSharedPreferences("aurora_personal",0) }
 var revision by remember { mutableIntStateOf(0) }
 DisposableEffect(p) {
  val l=SharedPreferences.OnSharedPreferenceChangeListener { _,_->revision++ };p.registerOnSharedPreferenceChangeListener(l)
  onDispose { p.unregisterOnSharedPreferenceChangeListener(l) }
 }
 return remember(revision) { AuroraPreferences(p.getBoolean("sky",true),p.getBoolean("actions",true),p.getInt("interval",15),p.getFloat("brightness",.7f),p.getFloat("speed",.5f),p.getFloat("hue",.4f),p.getBoolean("high",true),p.getBoolean("autoDownload",true)) }
}

@Composable fun AuroraSky(visible:Boolean) {
 val prefs=rememberAuroraPreferences();val life=LocalLifecycleOwner.current
 // Read state only during drawing; cache gradients, geometry and paints.
 val drawClock=remember { mutableFloatStateOf(0f) }
 // Keep low mode's draw invalidation at <=30 FPS while preserving continuous phase.
 LaunchedEffect(visible,prefs.sky,prefs.high,life) {
  if(visible && prefs.sky)life.lifecycle.repeatOnLifecycle(Lifecycle.State.RESUMED) {
   var previous=0L;var elapsed=drawClock.floatValue;var drawn=0L
   while(true)withFrameNanos { now ->
    if(previous!=0L)elapsed+=((now-previous)/1_000_000_000f).coerceAtMost(.1f)
    previous=now
    if(now-drawn >= if(prefs.high)15_000_000L else 30_000_000L){drawClock.floatValue=elapsed;drawn=now}
   }
  }
 }
 Box(Modifier.fillMaxSize().drawWithCache {
  val w=size.width;val h=size.height
  val sky=Brush.verticalGradient(listOf(Color(0xFF030C1B),Color(0xFF092635),Color(0xFF091B27)))
  val stars=Array(110){i->Offset(((i*7919%1000)/1000f)*w,((i*3571%1000)/1500f)*h)}
  val paints=Array(4){layer->
   val color=Color.hsv(125f+prefs.hue*120f+layer*18f,.7f,.95f)
   android.graphics.Paint(android.graphics.Paint.ANTI_ALIAS_FLAG).apply {
    shader=android.graphics.LinearGradient(0f,0f,0f,1f,intArrayOf(android.graphics.Color.TRANSPARENT,color.copy(alpha=.25f).toArgb(),color.toArgb(),android.graphics.Color.TRANSPARENT),floatArrayOf(0f,.35f,.7f,1f),android.graphics.Shader.TileMode.CLAMP)
    xfermode=android.graphics.PorterDuffXfermode(android.graphics.PorterDuff.Mode.ADD)
   }
  }
  val matrix=android.graphics.Matrix()
  val mountain=Path().apply {moveTo(0f,h);lineTo(0f,h*.89f);for(i in 0..48){val u=i/48f;lineTo(u*w,h*(.82f-.06f*sin(u*15f)-.02f*cos(u*47f)))};lineTo(w,h);close()}
  val n=if(prefs.high)180 else 72;val column=w/n
  onDrawBehind {
   val t=drawClock.floatValue*(.15f+prefs.speed*.7f)
   drawRect(sky)
   repeat(stars.size){i->drawCircle(Color.White.copy(alpha=(.2f+.4f*(.5f+.5f*sin(t+i))).coerceIn(0f,1f)),if(i%9==0)1.4f else .7f,stars[i])}
   drawIntoCanvas { surface ->
    val canvas=surface.nativeCanvas
    repeat(4){layer->
     val paint=paints[layer]
     for(i in 0 until n){
      val u=i.toFloat()/n;val x=u*w
      val fold=sin(u*8f+t*.55f+layer)+.35f*sin(u*21f-t*.3f+layer*2f)
      val top=h*(.13f+layer*.07f)+h*.1f*fold
      val bottom=(top+h*(.28f+.07f*sin(u*13f+t+layer))).coerceAtMost(h*.87f)
      paint.alpha=(255*prefs.brightness*(.14f+.19f*(.5f+.5f*sin(u*37f+t+layer)))).toInt().coerceIn(0,166)
      matrix.setScale(1f,bottom-top);matrix.postTranslate(0f,top)
      paint.shader?.setLocalMatrix(matrix)
      canvas.drawRect(x,top,x+column+1f,bottom,paint)
     }
    }
   }
   drawPath(mountain,Color(0xFF050E19))
  }
 })
}

@Composable fun AuroraHomeControls(modifier:Modifier=Modifier) {
 var show by remember {mutableStateOf(false)};val prefs=rememberAuroraPreferences();val c=LocalContext.current
 val p=remember{c.getSharedPreferences("aurora_personal",0)}
 FilledTonalButton(onClick={show=true},modifier=modifier.padding(12.dp)){Text("极光与个性化")}
 if(show) AlertDialog(onDismissRequest={show=false},title={Text("让 Aurora 更像你的启动器")},text={
  Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(8.dp)) {
   fun setBool(key:String,v:Boolean){p.edit().putBoolean(key,v).apply()}
   Row {Text("极光光幕",Modifier.weight(1f));Switch(prefs.sky,{setBool("sky",it)})}
   Row {Text("人物随机动作（20 种）",Modifier.weight(1f));Switch(prefs.actions,{setBool("actions",it)})}
   Text("动作间隔：${prefs.interval} 秒")
   Slider(prefs.interval.toFloat(),{p.edit().putInt("interval",it.roundToInt()).apply()},valueRange=5f..60f,steps=54)
   Text("极光亮度");Slider(prefs.brightness,{p.edit().putFloat("brightness",it).apply()})
   Text("光幕速度");Slider(prefs.speed,{p.edit().putFloat("speed",it).apply()})
   Text("极光配色");Slider(prefs.hue,{p.edit().putFloat("hue",it).apply()})
   Row {Text("流畅 60 FPS（关闭为省电 30 FPS）",Modifier.weight(1f));Switch(prefs.high,{setBool("high",it)})}
   Row {Text("检测新版后自动下载",Modifier.weight(1f));Switch(prefs.autoDownload,{setBool("autoDownload",it)})}
   Text("左右拖动人物可旋转。离开主页或切到后台，极光停止绘制。",style=MaterialTheme.typography.bodySmall)
  }
 },confirmButton={TextButton(onClick={show=false}){Text("完成")}})
}

@Composable fun AuroraLegalCard(openLicense:(Int)->Unit,openLink:(String)->Unit) {
 var expanded by remember{mutableStateOf(false)}
 AuroraPanel("开源许可") {
  Text("Aurora 界面与功能扩展：reunionSama。保留所用开源核心的版权和许可。")
  TextButton(onClick={expanded=!expanded}){Text(if(expanded)"收起技术来源" else "查看技术来源与许可")}
  if(expanded){
   Text("Zalith Launcher 2：MovTery 及贡献者；PojavLauncher 及贡献者。GPL-3.0-or-later。第三方组件依照各自许可分发。")
   TextButton(onClick={openLink("https://github.com/ZalithLauncher/ZalithLauncher2")}){Text("上游核心与完整贡献记录")}
   TextButton(onClick={openLicense(com.movtery.zalithlauncher.R.raw.lgpl_3_license)}){Text("LGPL 许可")}
   com.movtery.zalithlauncher.library.libraryData.forEach { info ->
    Text(info.name + "\n" + (info.copyrightInfo ?: ""))
    TextButton(onClick={openLicense(info.license.raw)}){Text(info.license.name)}
   }
   TextButton(onClick={openLink("https://github.com/reunionSama/AuroraLauncher-Android")}){Text("Aurora 源码与许可记录")}
  }
 }
}

@Composable fun AuroraUpdateButton() {
 val context=LocalContext.current
 val scope=rememberCoroutineScope()
 FilledTonalButton(onClick={checkAuroraUpdate(context,scope,force=true)}){Text("检查更新")}
}

