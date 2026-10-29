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
    @Test fun missingLogGivesActionableMessage() { assertTrue(readLogTail(null).contains("启动")) }
}
