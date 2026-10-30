/* Copyright (C) 2026 reunionSama. SPDX-License-Identifier: GPL-3.0-or-later */
package io.github.reunionsama.aurora;
import java.lang.instrument.ClassFileTransformer;
import java.lang.instrument.Instrumentation;
import java.security.ProtectionDomain;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;
import org.objectweb.asm.*;

/** In-memory cosmetic branding. Game files on disk stay untouched. */
public final class AuroraBranding {
    public static void premain(String version, Instrumentation instrumentation) {
        final String brand="AuroraLauncher("+(version==null?"?":version)+")";
        final Set<String> titles=names("aurora.titleClasses","net/minecraft/client/gui/screens/TitleScreen,net/minecraft/client/gui/GuiMainMenu");
        final Set<String> brands=names("aurora.brandClasses","net/minecraft/client/ClientBrandRetriever");
        instrumentation.addTransformer(new ClassFileTransformer() {
            public byte[] transform(ClassLoader loader,String name,Class<?> old,ProtectionDomain domain,byte[] bytes) {
                if(!titles.contains(name)&&!brands.contains(name)) return null;
                try {
                    final boolean isBrand=brands.contains(name);final boolean[] changed={false};
                    ClassReader reader=new ClassReader(bytes);ClassWriter writer=new ClassWriter(reader,ClassWriter.COMPUTE_MAXS);
                    reader.accept(new ClassVisitor(Opcodes.ASM9,writer) {
                        public MethodVisitor visitMethod(int access,String method,String descriptor,String signature,String[] exceptions) {
                            MethodVisitor original=super.visitMethod(access,method,descriptor,signature,exceptions);
                            final boolean brandMethod=isBrand&&descriptor.equals("()Ljava/lang/String;")&&(access&Opcodes.ACC_STATIC)!=0;
                            return new MethodVisitor(Opcodes.ASM9,original) {
                                String title(String text) {
                                    if(!isBrand&&text.startsWith("Minecraft ")) {changed[0]=true;return brand+"/"+text;}
                                    return text;
                                }
                                public void visitLdcInsn(Object value) {
                                    if(brandMethod&&"vanilla".equals(value)) value="minecraft";
                                    else if(value instanceof String) value=title((String)value);
                                    super.visitLdcInsn(value);
                                }
                                public void visitInvokeDynamicInsn(String n,String d,Handle bootstrap,Object... arguments) {
                                    Object[] copy=arguments.clone();
                                    if(!isBrand)for(int i=0;i<copy.length;i++)if(copy[i] instanceof String)copy[i]=title((String)copy[i]);
                                    super.visitInvokeDynamicInsn(n,d,bootstrap,copy);
                                }
                                public void visitInsn(int opcode) {
                                    if(brandMethod&&opcode==Opcodes.ARETURN) {
                                        changed[0]=true;
                                        super.visitTypeInsn(Opcodes.NEW,"java/lang/StringBuilder");super.visitInsn(Opcodes.DUP);
                                        super.visitLdcInsn(brand+"/");
                                        super.visitMethodInsn(Opcodes.INVOKESPECIAL,"java/lang/StringBuilder","<init>","(Ljava/lang/String;)V",false);
                                        super.visitInsn(Opcodes.SWAP);
                                        super.visitMethodInsn(Opcodes.INVOKEVIRTUAL,"java/lang/StringBuilder","append","(Ljava/lang/String;)Ljava/lang/StringBuilder;",false);
                                        super.visitMethodInsn(Opcodes.INVOKEVIRTUAL,"java/lang/StringBuilder","toString","()Ljava/lang/String;",false);
                                    }
                                    super.visitInsn(opcode);
                                }
                            };
                        }
                    },0);
                    if(!changed[0])return null;
                    System.out.println("[AuroraLauncher] branding patched "+(isBrand?"F3 brand":"title screen")+": "+name);
                    return writer.toByteArray();
                } catch(Throwable error) {
                    System.err.println("[AuroraLauncher] branding unavailable for "+name+": "+error.getClass().getSimpleName());
                    return null;
                }
            }
        });
    }
    private static Set<String> names(String property,String defaults) {
        Set<String> result=new HashSet<String>(Arrays.asList(defaults.split(",")));
        result.addAll(Arrays.asList(System.getProperty(property,"").replace('.','/').split(",")));
        return result;
    }
}
