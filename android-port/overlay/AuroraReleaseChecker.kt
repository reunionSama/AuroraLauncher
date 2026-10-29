/* Copyright (C) 2026 reunionSama. SPDX-License-Identifier: GPL-3.0-or-later */
package com.movtery.zalithlauncher.ui.screens.content.aurora

import android.app.AlertDialog
import android.app.DownloadManager
import android.app.ProgressDialog
import android.content.*
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.provider.Settings
import android.widget.Toast
import androidx.core.content.FileProvider
import com.movtery.zalithlauncher.BuildConfig
import kotlinx.coroutines.*
import kotlinx.serialization.json.*
import java.net.HttpURLConnection
import java.net.URL
import java.io.File
import java.security.MessageDigest
import java.time.Instant
import java.util.concurrent.atomic.AtomicBoolean

internal data class AuroraRelease(val alpha:Int,val page:String,val download:String="",val body:String="",val size:Long=0,val digest:String="",val id:Long=0)
private const val REPO="https://github.com/reunionSama/AuroraLauncher-Android"
private val checking=AtomicBoolean(false)
internal fun newerAuroraRelease(body:String,currentAlpha:Int):AuroraRelease? = parseRelease(body,currentAlpha,Long.MAX_VALUE)
internal fun parseRelease(body:String,currentAlpha:Int,buildTime:Long,installedDigest:String="",ignored:Set<String> = emptySet()):AuroraRelease? {
 return Json.parseToJsonElement(body).jsonArray.flatMap {value->
  val r=value.jsonObject;val page=r["html_url"]?.jsonPrimitive?.content.orEmpty()
  if(r["draft"]?.jsonPrimitive?.booleanOrNull==true || !page.startsWith("$REPO/releases/tag/")) return@flatMap emptyList()
  r["assets"]?.jsonArray.orEmpty().mapNotNull {element->
   val a=element.jsonObject;val name=a["name"]?.jsonPrimitive?.content.orEmpty();val url=a["browser_download_url"]?.jsonPrimitive?.content.orEmpty()
   val assetId=a["id"]?.jsonPrimitive?.longOrNull?:0
   val digest=a["digest"]?.jsonPrimitive?.content.orEmpty()
   if(assetId.toString() in ignored || (installedDigest.isNotEmpty() && digest==installedDigest))return@mapNotNull null
   val alpha=Regex("alpha(\\d+)",RegexOption.IGNORE_CASE).find(name)?.groupValues?.get(1)?.toIntOrNull()
   val updated=runCatching{Instant.parse(a["updated_at"]!!.jsonPrimitive.content).toEpochMilli()}.getOrDefault(0)
   val named=(name.equals("AuroraLauncher.apk",true) && updated>buildTime)
   if(!name.endsWith(".apk",true)||name.contains("x86",true)||!url.startsWith("$REPO/releases/download/")|| !(named || alpha!=null && alpha>currentAlpha)) null
   else AuroraRelease(alpha?:currentAlpha+1,page,url,r["body"]?.jsonPrimitive?.content.orEmpty(),a["size"]?.jsonPrimitive?.longOrNull?:0,a["digest"]?.jsonPrimitive?.content.orEmpty(),a["id"]?.jsonPrimitive?.longOrNull?:0)
  }
 }.maxByOrNull{it.id.takeIf {v->v>0}?:it.alpha.toLong()}
}

fun checkAuroraUpdate(context:Context,scope:CoroutineScope,force:Boolean=false) {
 if(!checking.compareAndSet(false,true))return
 scope.launch {
  try {
   val result=withContext(Dispatchers.IO){runCatching{
    val c=URL("https://api.github.com/repos/reunionSama/AuroraLauncher-Android/releases?per_page=10").openConnection() as HttpURLConnection
    try{c.connectTimeout=6000;c.readTimeout=6000;c.setRequestProperty("User-Agent","AuroraLauncher/alpha4");check(c.responseCode==200){"HTTP ${c.responseCode}"}
     val json=c.inputStream.bufferedReader().use{it.readText()};check(json.length<2*1024*1024)
     val buildTime=context.assets.open("AURORA_CHANNEL.json").bufferedReader().use{Json.parseToJsonElement(it.readText()).jsonObject["build_time"]!!.jsonPrimitive.long}
     val currentAlpha=Regex("alpha(\\d+)").find(BuildConfig.VERSION_NAME)?.groupValues?.get(1)?.toIntOrNull()?:4
     val ignored=context.getSharedPreferences("aurora_update_rejected",0).getStringSet("ids",emptySet())!!.toSet()
     val prefs=context.getSharedPreferences("aurora_update_digest",0)
     val cacheKey="${BuildConfig.VERSION_CODE}:${context.packageManager.getPackageInfo(context.packageName,0).lastUpdateTime}"
     val installedDigest=if(json.contains("AuroraLauncher.apk",true))prefs.getString(cacheKey,null)?:run {
      val md=MessageDigest.getInstance("SHA-256")
      File(context.applicationInfo.sourceDir).inputStream().use { input ->
       val buffer=ByteArray(65536)
       while(true){val n=input.read(buffer);if(n<0)break;md.update(buffer,0,n)}
      }
      val hash="sha256:"+md.digest().joinToString(""){"%02x".format(it)}
      prefs.edit().putString(cacheKey,hash).apply();hash
     }else ""
     parseRelease(json,currentAlpha,buildTime,installedDigest,ignored)
    }finally{c.disconnect()}
   }}
   val release=result.getOrNull()
   if(release!=null){
    val auto=context.getSharedPreferences("aurora_personal",0).getBoolean("autoDownload",true)
    AlertDialog.Builder(context).setTitle("AuroraLauncher 更新")
     .setMessage(release.body.ifBlank{"此发布未填写更新说明。"}+"\n\n下载大小：${release.size/1048576} MiB")
     .setNegativeButton("稍后",null).setPositiveButton("应用内下载"){_,_->downloadUpdate(context,scope,release)}.show()
    if(auto) downloadUpdate(context,scope,release)
   }else if(force) Toast.makeText(context,if(result.isSuccess)"当前已是此发布渠道的新版本" else "更新检查失败，请稍后重试",Toast.LENGTH_LONG).show()
  }finally{checking.set(false)}
 }
}
private var downloading=false
@Suppress("DEPRECATION")
private fun downloadUpdate(context:Context,scope:CoroutineScope,r:AuroraRelease){
 if(downloading)return
 downloading=true
 val dm=context.getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager
 val prefs=context.getSharedPreferences("aurora_update",0)
 val file=File(context.getExternalFilesDir(android.os.Environment.DIRECTORY_DOWNLOADS),"AuroraLauncher-update-${r.id}.apk")
 val previous=prefs.getLong("download_id",-1)
 var id=if(prefs.getLong("asset",-2)==r.id)previous else -1
 if(id<0){
  file.delete()
  id=dm.enqueue(DownloadManager.Request(Uri.parse(r.download)).setTitle("AuroraLauncher 更新").setDescription("在应用内下载新版 APK").setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED).setDestinationUri(Uri.fromFile(file)))
  prefs.edit().putLong("download_id",id).putLong("asset",r.id).apply()
 }
 val downloadId=id
 val dialog=ProgressDialog(context).apply{setTitle("正在下载 AuroraLauncher");setMessage(r.body);setProgressStyle(ProgressDialog.STYLE_HORIZONTAL);max=100;setCancelable(false);setButton(DialogInterface.BUTTON_NEGATIVE,"取消"){_,_->dm.remove(downloadId);prefs.edit().clear().apply()};show()}
 scope.launch {
  try{
   while(isActive){
    val state=withContext(Dispatchers.IO){dm.query(DownloadManager.Query().setFilterById(downloadId)).use{c->
     if(!c.moveToFirst())Triple(-1,0L,0L)else Triple(c.getInt(c.getColumnIndexOrThrow(DownloadManager.COLUMN_STATUS)),c.getLong(c.getColumnIndexOrThrow(DownloadManager.COLUMN_BYTES_DOWNLOADED_SO_FAR)),c.getLong(c.getColumnIndexOrThrow(DownloadManager.COLUMN_TOTAL_SIZE_BYTES)))
    }}
    if(state.third>0)dialog.progress=(state.second*100/state.third).toInt()
    if(state.first==DownloadManager.STATUS_SUCCESSFUL){
     val error=withContext(Dispatchers.IO){validateUpdate(context,file,r.digest)}
     if(error!=null){
      val rejected=context.getSharedPreferences("aurora_update_rejected",0)
      rejected.edit().putStringSet("ids",rejected.getStringSet("ids",emptySet())!!.toSet()+r.id.toString()).apply()
      throw IllegalStateException(error)
     }
     dialog.dismiss()
     AlertDialog.Builder(context).setTitle("更新下载完成").setMessage(r.body).setNegativeButton("稍后",null).setPositiveButton("安装更新"){_,_->
      if(Build.VERSION.SDK_INT>=26 && !context.packageManager.canRequestPackageInstalls()){
       context.startActivity(Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,Uri.parse("package:${context.packageName}")))
       Toast.makeText(context,"授权后返回，打开关于页检查更新可再次安装",Toast.LENGTH_LONG).show()
      }else{
       val uri=FileProvider.getUriForFile(context,"${context.packageName}.provider",file)
       context.startActivity(Intent(Intent.ACTION_VIEW).setDataAndType(uri,"application/vnd.android.package-archive").addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION))
      }
     }.show();break
    }
    check(state.first!=DownloadManager.STATUS_FAILED && state.first!=-1){"下载失败或已取消，请重新检查更新"}
    delay(500)
   }
  }catch(e:Exception){if(e is CancellationException)throw e;dialog.dismiss();dm.remove(downloadId);prefs.edit().clear().apply();Toast.makeText(context,e.message?:"下载失败",Toast.LENGTH_LONG).show()}
  finally{dialog.dismiss();downloading=false}
 }
}
@Suppress("DEPRECATION")
internal fun validateUpdate(context:Context,file:File,digest:String):String? {
 if(!file.isFile)return "未找到安装包"
 if(digest.startsWith("sha256:")){
  val md=MessageDigest.getInstance("SHA-256");file.inputStream().use{input->val b=ByteArray(65536);while(true){val n=input.read(b);if(n<0)break;md.update(b,0,n)}}
  if(md.digest().joinToString(""){"%02x".format(it)}!=digest.removePrefix("sha256:"))return "下载文件校验失败"
 }
 val flags=if(Build.VERSION.SDK_INT>=28)PackageManager.GET_SIGNING_CERTIFICATES else PackageManager.GET_SIGNATURES
 val pm=context.packageManager;val incoming=pm.getPackageArchiveInfo(file.absolutePath,flags)?:return "无法读取 APK"
 if(incoming.packageName!=context.packageName)return "更新包应用标识不匹配"
 val code=if(Build.VERSION.SDK_INT>=28)incoming.longVersionCode else incoming.versionCode.toLong()
 if(code<=BuildConfig.VERSION_CODE)return "下载包版本不高于当前版本"
 val installed=pm.getPackageInfo(context.packageName,flags)
 val a=if(Build.VERSION.SDK_INT>=28)incoming.signingInfo?.apkContentsSigners else incoming.signatures
 val b=if(Build.VERSION.SDK_INT>=28)installed.signingInfo?.apkContentsSigners else installed.signatures
 if(a.isNullOrEmpty()||b.isNullOrEmpty()||a.map{it.toCharsString()}.toSet()!=b.map{it.toCharsString()}.toSet())return "更新包签名不匹配"
 return null
}
