/* Copyright (C) 2026 reunionSama. SPDX-License-Identifier: GPL-3.0-or-later */
package com.movtery.zalithlauncher.ui.screens.content.aurora

import android.content.Context
import kotlinx.coroutines.*
import kotlinx.serialization.json.*
import java.io.IOException
import java.net.HttpURLConnection
import java.net.SocketTimeoutException
import java.net.URL
import java.net.UnknownHostException
import java.time.Instant

internal const val AURORA_REPOSITORY = "https://github.com/reunionSama/AuroraLauncher-Android"
internal data class ReleaseFeed(val json:String,val source:String,val stale:Boolean=false)
internal class UpdateHttpError(val status:Int,val retryAt:Long=0):IOException("HTTP $status")
internal const val UPDATE_MAX_BYTES=2*1024*1024

/** Only GitHub-owned endpoints are used. No tokens, untrusted proxies or executable HTML. */
internal class AuroraUpdateNetwork(context:Context) {
 private val cache=context.applicationContext.getSharedPreferences("aurora_release_cache_v2",0)
 private suspend fun request(url:String,key:String):String=withContext(Dispatchers.IO) {
  coroutineContext.ensureActive()
  val c=URL(url).openConnection() as HttpURLConnection
  try {
   c.connectTimeout=8000;c.readTimeout=10000
   c.setRequestProperty("User-Agent","AuroraLauncher-Android/alpha5")
   c.setRequestProperty("Accept",if(key=="api")"application/vnd.github+json" else "application/atom+xml,text/html")
   cache.getString("$key.etag",null)?.let { c.setRequestProperty("If-None-Match",it) }
   val status=c.responseCode
   if(status==304) return@withContext cache.getString("$key.body",null)?:throw IOException("缓存已失效")
   if(status!=200) {
    val retry=c.getHeaderField("Retry-After")?.toLongOrNull()?.let{System.currentTimeMillis()+it*1000}
     ?: c.getHeaderField("X-RateLimit-Reset")?.toLongOrNull()?.times(1000) ?: 0
    throw UpdateHttpError(status,retry)
   }
   if(c.contentLengthLong>UPDATE_MAX_BYTES)throw IOException("更新响应过大")
   val body=c.inputStream.use{input->
    val out=java.io.ByteArrayOutputStream();val buffer=ByteArray(8192)
    while(true){coroutineContext.ensureActive();val n=input.read(buffer);if(n<0)break
     if(out.size()+n>UPDATE_MAX_BYTES)throw IOException("更新响应过大");out.write(buffer,0,n)}
    out.toString("UTF-8")
   }
   // Validate before caching, including responses from captive portals.
   if(key=="api")Json.parseToJsonElement(body).jsonArray
   else if(key=="atom")require(body.contains("<feed ")&&body.contains("</feed>")){"发布订阅格式异常"}
   else require(body.contains("<ul ")&&body.contains("</ul>")){"发布附件格式异常"}
   cache.edit().putString("$key.body",body).putString("$key.etag",c.getHeaderField("ETag")).apply()
   body
  }finally{c.disconnect()}
 }
 suspend fun fetch():ReleaseFeed {
  try {
   val result=loadAuroraFeeds(System.currentTimeMillis()>=cache.getLong("api.retryAt",0),::request){e->
    if(e is UpdateHttpError && (e.status==403||e.status==429))
     cache.edit().putLong("api.retryAt",maxOf(e.retryAt,System.currentTimeMillis()+60000)).apply()
   }
   return remember(result.json,result.source)
  }catch(e:CancellationException){throw e}
  catch(e:Exception){
   val saved=cache.getString("good.json",null)
   val age=System.currentTimeMillis()-cache.getLong("good.at",0)
   if(saved!=null && age in 0..86400000) return ReleaseFeed(saved,"上次成功检查的缓存",true)
   throw e
  }
 }
 private fun remember(json:String,source:String):ReleaseFeed {
  cache.edit().putString("good.json",json).putLong("good.at",System.currentTimeMillis()).apply()
  return ReleaseFeed(json,source)
 }
}

/** Injectable transport lets tests cover primary failure, retry and web fallback without Android. */
internal suspend fun loadAuroraFeeds(apiEnabled:Boolean=true,read:suspend(String,String)->String,onApiError:(Exception)->Unit={}):ReleaseFeed {
 var first:Exception?=null
 if(apiEnabled)for(attempt in 0..1)try {
  val body=read("https://api.github.com/repos/reunionSama/AuroraLauncher-Android/releases?per_page=10","api")
  Json.parseToJsonElement(body).jsonArray
  return ReleaseFeed(body,"GitHub API")
 }catch(e:CancellationException){throw e}
 catch(e:Exception){first=e;onApiError(e);if(e is UpdateHttpError)break;if(attempt==0)delay(400)}
 try {
  val entries=parseAuroraAtom(read("$AURORA_REPOSITORY/releases.atom","atom"))
  val releases=entries.take(3).map { entry ->
   val tag=entry.page.removePrefix("$AURORA_REPOSITORY/releases/tag/")
   fallbackRelease(entry,read("$AURORA_REPOSITORY/releases/expanded_assets/$tag","assets.$tag"))
  }
  return ReleaseFeed(JsonArray(releases).toString(),"GitHub 备用线路")
 }catch(e:CancellationException){throw e}
 catch(e:Exception){throw IOException(updateFailureHint(first,e),e)}
}

internal data class AtomRelease(val page:String,val notes:String)
private fun unescapeXml(s:String):String = Regex("&#(x[0-9a-fA-F]+|[0-9]+);").replace(s){m->
 val v=m.groupValues[1];val code=if(v.startsWith("x"))v.drop(1).toIntOrNull(16)else v.toIntOrNull()
 code?.takeIf{Character.isValidCodePoint(it)}?.let{String(Character.toChars(it))}?:m.value
}.replace("&lt;","<").replace("&gt;",">").replace("&quot;","\"").replace("&apos;","'").replace("&amp;","&")
internal fun parseAuroraAtom(xml:String):List<AtomRelease> {
 require(xml.contains("<feed ")&&xml.contains("</feed>")){"发布订阅格式异常"}
 return Regex("<entry>([\\s\\S]*?)</entry>").findAll(xml).mapNotNull{match->
  val entry=match.groupValues[1]
  val page=Regex("<link\\b[^>]*href=\"([^\"]+)\"").findAll(entry).map{unescapeXml(it.groupValues[1])}.firstOrNull{it.startsWith("$AURORA_REPOSITORY/releases/tag/")}?:return@mapNotNull null
  val encoded=Regex("<content\\b[^>]*>([\\s\\S]*?)</content>").find(entry)?.groupValues?.get(1).orEmpty()
  val notes=unescapeXml(unescapeXml(encoded).replace(Regex("(?i)<br\\s*/?>|</p>|</li>|</h[1-6]>"),"\n").replace(Regex("<[^>]*>"),"")).trim()
  AtomRelease(page,notes.take(32000))
 }.toList()
}
internal fun fallbackRelease(entry:AtomRelease,html:String):JsonObject {
 val assets=Regex("<li\\b[^>]*>([\\s\\S]*?)</li>").findAll(html).mapNotNull{m->
  val item=m.groupValues[1]
  val path=Regex("href=\"([^\"]+\\.apk)\"",RegexOption.IGNORE_CASE).find(item)?.groupValues?.get(1)?:return@mapNotNull null
  val url=unescapeXml(if(path.startsWith("/"))"https://github.com$path" else path)
  if(!url.startsWith("$AURORA_REPOSITORY/releases/download/"))return@mapNotNull null
  val timestamp=Regex("datetime=\"([^\"]+)\"").find(item)?.groupValues?.get(1).orEmpty()
  val millis=runCatching{Instant.parse(timestamp).toEpochMilli()}.getOrDefault(0)
  val digest=Regex("sha256:[0-9a-fA-F]{64}").find(item)?.value.orEmpty().lowercase()
  buildJsonObject {
   put("id",millis*1000+(url.hashCode().toLong()and 0x7fffffff)%1000)
   put("name",java.net.URLDecoder.decode(url.substringAfterLast('/'),"UTF-8"))
   put("updated_at",timestamp);put("browser_download_url",url);put("digest",digest)
  }
 }.toList()
 return buildJsonObject{put("html_url",entry.page);put("body",entry.notes);put("assets",JsonArray(assets))}
}
internal fun updateFailureHint(first:Exception?,last:Exception):String {
 val errors=listOfNotNull(first,last,last.cause)
 return when {
  errors.any{it is UpdateHttpError && (it.status==403||it.status==429)}->"GitHub 接口暂时限流，备用线路也未连通。请稍后重试。"
  errors.any{it is UnknownHostException}->"无法解析 GitHub 地址，请检查网络或 DNS 后重试。"
  errors.any{it is SocketTimeoutException}->"连接 GitHub 超时，主线路和备用线路均不可用。请检查网络后重试。"
  else->"暂时无法获取 GitHub 发布信息，请检查网络后重试。"
 }
}
