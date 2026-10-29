/* Copyright (C) 2026 reunionSama. SPDX-License-Identifier: GPL-3.0-or-later */
package com.movtery.zalithlauncher.ui.screens.content.aurora

import org.junit.Assert.*
import org.junit.Test
import java.io.File

class AuroraDiagnosticsTest {
    @Test fun removesCommandLineCredentials() {
        val result = redact("java --accessToken secret_value --username PrivatePlayer --uuid abc-123 start")
        assertFalse(result.contains("secret_value")); assertFalse(result.contains("PrivatePlayer")); assertFalse(result.contains("abc-123"))
        assertTrue(result.contains("start"))
    }
    @Test fun removesJsonAndBearerCredentials() {
        val result = redact("""{"access_token":"privateToken","refresh_token":"refreshSecret"} Authorization: Bearer hiddenBearer""")
        assertFalse(result.contains("privateToken")); assertFalse(result.contains("refreshSecret")); assertFalse(result.contains("hiddenBearer"))
    }
    @Test fun removesEmailButPreservesUsefulErrors() {
        val result = redact("user@example.com ERROR java.lang.OutOfMemoryError")
        assertFalse(result.contains("user@example.com")); assertTrue(result.contains("OutOfMemoryError"))
    }
    @Test fun recognizesJavaAndMemoryErrorsWithoutClaimingCertainty() {
        assertTrue(logHint("UnsupportedClassVersionError").contains("Java"))
        assertTrue(logHint("OutOfMemoryError").contains("可能"))
        assertEquals("", logHint("Normal game startup"))
    }
    @Test fun tailKeepsRecentLinesAndExcludesOldOnes() {
        val f = File.createTempFile("aurora-test", ".log")
        try {
            f.writeText((1..10000).joinToString("\n") { "line-$it " + "x".repeat(40) })
            val tail = readLogTail(f)
            assertTrue(tail.contains("line-10000")); assertFalse(tail.contains("line-1 "))
            assertTrue(tail.lines().size <= 160)
        } finally { f.delete() }
    }
    @Test fun tailDoesNotExposeTokens() {
        val f = File.createTempFile("aurora-test", ".log")
        try { f.writeText("--accessToken shouldNotLeak\nlast line"); assertFalse(readLogTail(f).contains("shouldNotLeak")) }
        finally { f.delete() }
    }
    @Test fun updaterIgnoresWindowsForeignAndOlderAssets() {
        val json = """[
          {"html_url":"https://github.com/reunionSama/AuroraLauncher-Android/releases/tag/a4","assets":[{"name":"AuroraLauncher-Android-arm64-alpha4.apk","browser_download_url":"https://github.com/reunionSama/AuroraLauncher-Android/releases/download/a4/app.apk"}]},
          {"html_url":"https://github.com/someone/other/releases/tag/a99","assets":[{"name":"AuroraLauncher-Android-arm64-alpha99.apk","browser_download_url":"https://github.com/someone/other/releases/download/a99/app.apk"}]},
          {"html_url":"https://github.com/reunionSama/AuroraLauncher-Android/releases/tag/windows","assets":[{"name":"AuroraLauncher.exe","browser_download_url":"https://github.com/reunionSama/AuroraLauncher-Android/releases/download/windows/app.exe"}]}
        ]"""
        assertEquals(4, newerAuroraRelease(json, 3)?.alpha)
        assertNull(newerAuroraRelease(json, 4))
    }
    @Test fun missingLogGivesActionableMessage() { assertTrue(readLogTail(null).contains("启动")) }

    private val generic = """[{"html_url":"https://github.com/reunionSama/AuroraLauncher-Android/releases/tag/a5","assets":[{"id":99,"name":"AuroraLauncher.apk","updated_at":"2030-01-01T00:00:00Z","digest":"sha256:known","browser_download_url":"https://github.com/reunionSama/AuroraLauncher-Android/releases/download/a5/AuroraLauncher.apk"}]}]"""
    @Test fun sameApkDigestIsNotAnUpdate() { assertNull(parseRelease(generic,4,0,"sha256:known")) }
    @Test fun rejectedAssetIsNotDownloadedAgain() { assertNull(parseRelease(generic,4,0,"sha256:other",setOf("99"))) }
    @Test fun newerGenericAssetIsRecognized() { assertEquals(99L,parseRelease(generic,4,0,"sha256:old")?.id) }

    private val atom = """<feed xmlns="http://www.w3.org/2005/Atom"><entry><link href="https://github.com/reunionSama/AuroraLauncher-Android/releases/tag/a6"/><content type="html">&lt;p&gt;修复更新&lt;br&gt;动画优化&lt;/p&gt;</content></entry></feed>"""
    private val webAssets = """<ul class="Box"><li class="Box-row"><a href="/reunionSama/AuroraLauncher-Android/releases/download/a6/AuroraLauncher.apk">APK</a><span>sha256:${"a".repeat(64)}</span><relative-time datetime="2030-01-01T00:00:00Z"></relative-time></li></ul>"""
    @Test fun atomPreservesNotesAndLineBreaks() {
        val entry=parseAuroraAtom(atom).single()
        assertEquals("修复更新\n动画优化",entry.notes)
        assertTrue(entry.page.endsWith("/a6"))
    }
    @Test fun webFallbackAcceptsOnlyOwnApkAndPreservesDigest() {
        val entry=parseAuroraAtom(atom).single()
        val json="["+fallbackRelease(entry,webAssets)+"]"
        val release=parseRelease(json,5,0)!!
        assertEquals("sha256:"+"a".repeat(64),release.digest)
        assertEquals("修复更新\n动画优化",release.body)
        assertNull(parseRelease(json,5,0,release.digest))
        assertNull(parseRelease("["+fallbackRelease(entry,webAssets.replace("/reunionSama/","/attacker/"))+"]",5,0))
    }
    @Test fun primaryFailureUsesIndependentWebEndpoint() = kotlinx.coroutines.runBlocking {
        val calls=mutableListOf<String>()
        val feed=loadAuroraFeeds(read={_,key->calls.add(key);when(key){"api"->throw UpdateHttpError(403);"atom"->atom;else->webAssets}})
        assertEquals(listOf("api","atom","assets.a6"),calls)
        assertEquals("GitHub 备用线路",feed.source)
        assertNotNull(parseRelease(feed.json,5,0))
    }
    @Test fun transientPrimaryFailureGetsOneRetry() = kotlinx.coroutines.runBlocking {
        var calls=0
        val feed=loadAuroraFeeds(read={_,_->calls++;if(calls==1)throw java.net.SocketTimeoutException() else "[]"})
        assertEquals(2,calls);assertEquals("[]",feed.json)
    }
    @Test fun validPrimaryAvoidsFallback() = kotlinx.coroutines.runBlocking {
        val calls=mutableListOf<String>()
        loadAuroraFeeds(read={_,key->calls.add(key);"[]"})
        assertEquals(listOf("api"),calls)
    }
    @Test fun apiCooldownUsesWebWithoutRetryingApi() = kotlinx.coroutines.runBlocking {
        val calls=mutableListOf<String>()
        loadAuroraFeeds(false,read={_,key->calls.add(key);if(key=="atom")atom else webAssets})
        assertFalse(calls.contains("api"))
    }
    @Test fun cancellationIsNotReportedAsNetworkFailure() = kotlinx.coroutines.runBlocking {
        var calls=0
        try { loadAuroraFeeds(read={_,_->calls++;throw kotlinx.coroutines.CancellationException()});fail("expected cancellation") }
        catch(_:kotlinx.coroutines.CancellationException){assertEquals(1,calls)}
    }
    @Test fun invalidAtomIsNotReportedAsNoUpdates() {
        try { parseAuroraAtom("<html>Sign in to Wi-Fi</html>");fail("expected format error") }
        catch(_:IllegalArgumentException){}
    }
    @Test fun bothRoutesFailWithAnActionableHint() = kotlinx.coroutines.runBlocking {
        try { loadAuroraFeeds(read={_,_->throw java.net.UnknownHostException()});fail("expected failure") }
        catch(e:java.io.IOException){assertTrue(e.message!!.contains("DNS"))}
    }
}
