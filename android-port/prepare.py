"""Reproducible Aurora Android alpha changes over the pinned GPL upstream.

Preserves every upstream copyright, license, native namespace and author credit.
"""
from pathlib import Path
import re
import sys

root = Path(sys.argv[1]).resolve()
module = root / 'ZalithLauncher'
properties = module / 'gradle.properties'
values = {
    'launcher_name': 'AuroraAndroid',
    'launcher_app_name': 'AuroraLauncher Android Alpha',
    'launcher_short_name': 'Aurora',
    'url_home': 'https://github.com/reunionSama/AuroraLauncher',
    'launcher_version_name': '2.7.2-Aurora-alpha1',
    'default_store_password': 'android',
    'default_key_password': 'android',
}
text = properties.read_text('utf-8')
for key, value in values.items():
    text, count = re.subn(r'^' + re.escape(key) + r'=.*$', key + '=' + value, text, flags=re.M)
    if count != 1:
        raise RuntimeError('Missing or duplicated upstream property: ' + key)
properties.write_text(text, 'utf-8')

file = module / 'build.gradle.kts'
text = file.read_text('utf-8')
for old, new in {
    'applicationId = zalithPackageName': 'applicationId = "io.github.reunionsama.auroralauncher"',
    'applicationIdSuffix = ".v2"': 'applicationIdSuffix = ".android"',
    'storeFile = file("zalith_launcher_debug.jks")': 'storeFile = file("aurora_debug.jks")',
    'keyAlias = "movtery_zalith_debug"': 'keyAlias = "aurora_android"',
}.items():
    if text.count(old) != 1:
        raise RuntimeError('Upstream build configuration changed: ' + old)
    text = text.replace(old, new)
file.write_text(text, 'utf-8')

# Keep all original author and license UI; prominently identify this derivative.
file = module / 'src/main/java/com/movtery/zalithlauncher/ui/screens/content/settings/AboutInfoScreen.kt'
text = file.read_text('utf-8')
marker = 'Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {'
if marker not in text:
    raise RuntimeError('Upstream about screen changed')
text = text.replace(marker, marker + '\n                        Text(text = "AuroraLauncher Android Alpha — Android edition by reunionSama. Based on Zalith Launcher 2 by MovTery and contributors / PojavLauncher. GPL-3.0-or-later. This is an independent derivative, not an official Zalith release or a direct Windows port.")', 1)
file.write_text(text, 'utf-8')

res = module / 'src/main/res'
foreground = '''<vector xmlns:android="http://schemas.android.com/apk/res/android" android:width="108dp" android:height="108dp" android:viewportWidth="108" android:viewportHeight="108">
    <path android:fillColor="#09B9CA" android:pathData="M54,24 L64,44 L84,54 L64,64 L54,84 L44,64 L24,54 L44,44 Z"/>
    <path android:fillColor="#E4FAFF" android:pathData="M54,43 L65,54 L54,65 L43,54 Z"/>
</vector>'''
(res / 'drawable/ic_launcher_foreground.xml').write_text(foreground, 'utf-8')
(res / 'drawable/ic_launcher_monochrome.xml').write_text(foreground.replace('#09B9CA', '#FFFFFF'), 'utf-8')
(res / 'values/ic_launcher_background.xml').write_text('<resources><color name="ic_launcher_background">#101C25</color></resources>', 'utf-8')
notice = '''AuroraLauncher Android Alpha
Android adaptation/build recipe: reunionSama (2026).
Based on Zalith Launcher 2, copyright (C) 2025-2026 MovTery and contributors,
and its credited PojavLauncher/native renderer/runtime dependencies.
Upstream: https://github.com/ZalithLauncher/ZalithLauncher2
Pinned upstream revision: a6b6fb6a63ce22c4e4fa91cc29a4d64286cd0924

Distributed under GPL-3.0-or-later and the licenses of included components.
All original copyrights and third-party notices are preserved.
The full corresponding modified source accompanies each successful APK build
as a separate source artifact, including the applied recipe and build workflow.

This is an experimental Android derivative using a mature Android Java Edition
engine. The Python/Qt Windows EXE and its DLL files are NOT included or executed.
It does not reproduce all of Aurora's Windows UI or its exact implementation.
A debug signing key is generated for testing, not for Play Store distribution.
Arm64 build: Android 8.0+ on 64-bit ARM devices only. No physical-device or
Minecraft gameplay test is claimed by the build. Microsoft login additionally
requires an application configuration accepted by Microsoft's services.
'''
(root / 'AURORA_ANDROID_NOTICE.txt').write_text(notice, 'utf-8')
assets = module / 'src/main/assets'
assets.mkdir(parents=True, exist_ok=True)
(assets / 'AURORA_ANDROID_NOTICE.txt').write_text(notice, 'utf-8')
print('Applied Aurora Android alpha identity and attribution; kept upstream engine and native namespaces.')
