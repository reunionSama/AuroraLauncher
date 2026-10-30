/* Copyright (C) 2026 reunionSama. SPDX-License-Identifier: GPL-3.0-or-later */
package io.github.reunionsama.aurora;
import java.io.File;
import java.lang.reflect.InvocationTargetException;
/** Calls the downloaded installer's public API against only the selected game library. */
public final class OptiFineBridge {
    public static void main(String[] args) throws Exception {
        if(args.length!=1)throw new IllegalArgumentException("Expected a Minecraft library path");
        try {Class.forName("optifine.Installer").getMethod("doInstall",File.class).invoke(null,new File(args[0]));}
        catch(InvocationTargetException error){Throwable cause=error.getCause();cause.printStackTrace();System.exit(1);}
    }
}
