# PyInstaller Windows x64 single executable. No Android runtime or legacy launcher code.
from PyInstaller.utils.hooks import collect_submodules,copy_metadata
from pathlib import Path
root=Path(SPECPATH)
datas=[(str(root/'qml'),'qml'),(str(root/'assets'),'assets')]
for name in ['minecraft-launcher-lib','requests','cryptography']:
    datas+=copy_metadata(name)
a=Analysis([str(root/'main.py')],pathex=[str(root)],binaries=[],datas=datas,
    hiddenimports=collect_submodules('minecraft_launcher_lib'),
    excludes=['PySide6.QtWebEngineCore','PySide6.QtWebEngineWidgets','PySide6.QtWebEngineQuick','PySide6.QtWebView','PySide6.QtQuick3D','PySide6.Qt3DCore','PySide6.QtMultimedia','PySide6.QtCharts','PySide6.QtGraphs','PySide6.QtPdf','PySide6.QtPdfWidgets','tkinter','numpy','pandas'],
    noarchive=False)
# These unused optional QML plugins would otherwise pull unrelated engines into a GUI-only launcher.
unused=('/qml/QtQuick3D/','/qml/Qt3D/','/qml/QtWebEngine/','/qml/QtWebView/','/qml/QtMultimedia/','/qml/QtCharts/','/qml/QtGraphs/','/qml/QtLocation/','/qml/QtVirtualKeyboard/')
a.datas=[x for x in a.datas if not any(v in '/'+x[0].replace('\\','/')+'/' for v in unused)]
a.binaries=[x for x in a.binaries if not any(v in '/'+x[0].replace('\\','/')+'/' for v in unused)]
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,a.binaries,a.datas,[],name='AuroraLauncher',debug=False,bootloader_ignore_signals=False,strip=False,upx=False,console=False,icon=str(root/'assets/icon.ico'),version=str(root/'version_info.txt'),uac_admin=False)
