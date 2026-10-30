import os,shutil,subprocess,sys,json
from pathlib import Path
import pytest
from aurora.branding import agent_path,mapped_classes
from aurora import VERSION

def test_official_mappings_select_brand_and_title_classes():
    title,brand=mapped_classes('net.minecraft.client.gui.screens.TitleScreen -> abc:\nnet.minecraft.client.ClientBrandRetriever -> xyz:\n')
    assert 'abc' in title and 'xyz' in brand

def test_java_agent_brands_title_and_f3_without_changing_inputs(tmp_path):
    java=shutil.which('java');javac=shutil.which('javac');ecj=os.environ.get('AURORA_ECJ')
    if not java or not (javac or ecj):pytest.skip('JDK compiler required; verified in Windows CI')
    source=tmp_path/'BrandProbe.java'
    source.write_text('''public class BrandProbe {
        public static void main(String[] args) {
            System.out.println(Brand.getClientModName());
            System.out.println(Title.title(args.length));
        }
    }
    class Brand { public static String getClientModName() { return "vanilla"; } }
    class Title { public static String title(int number) { return "Minecraft "+number; } }
    ''')
    compile=[javac,'-d',str(tmp_path),str(source)] if javac else [java,'-jar',ecj,'-17','-d',str(tmp_path),str(source)]
    subprocess.run(compile,check=True,capture_output=True)
    base=[java,'-cp',str(tmp_path),'BrandProbe']
    before=subprocess.check_output(base,text=True)
    result=subprocess.check_output([java,'-javaagent:'+str(agent_path())+'='+VERSION,'-Daurora.titleClasses=Title','-Daurora.brandClasses=Brand','-cp',str(tmp_path),'BrandProbe'],text=True)
    assert before.strip()=='vanilla\nMinecraft 0'
    assert 'AuroraLauncher('+VERSION+')/minecraft' in result
    assert 'AuroraLauncher('+VERSION+')/Minecraft 0' in result
    assert subprocess.check_output(base,text=True)==before

def test_all_asm_classes_use_private_namespace():
    import zipfile
    with zipfile.ZipFile(agent_path()) as jar:
        assert not any(n.startswith('org/objectweb/asm/') for n in jar.namelist())
        assert any(n.startswith('io/github/reunionsama/aurora/shaded/asm/') for n in jar.namelist())
