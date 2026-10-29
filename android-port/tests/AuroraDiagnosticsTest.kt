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
}

