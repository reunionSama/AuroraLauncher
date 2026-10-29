"""Reproducible Aurora Android alpha changes over the pinned GPL upstream.

Preserves every upstream copyright, license, native namespace and author credit.
"""
from pathlib import Path
import re
import sys
import json
from brand_assets import replace_branding

root = Path(sys.argv[1]).resolve()
module = root / 'ZalithLauncher'
properties = module / 'gradle.properties'
values = {
    'launcher_name': 'AuroraLauncher',
    'launcher_app_name': 'AuroraLauncher',
    'launcher_short_name': 'Aurora',
    'url_home': 'https://github.com/reunionSama/AuroraLauncher',
    'launcher_version_name': '2.7.2-Aurora-alpha4',
    'launcher_version_code': '200049',
    'default_store_password': 'android',
    'default_key_password': 'android',
}
text = properties.read_text('utf-8')
for key, value in values.items():
    text, count = re.subn(r'^' + re.escape(key) + r'=.*$', key + '=' + value, text, flags=re.M)
    if count != 1:
        raise RuntimeError('Missing or duplicated upstream property: ' + key)
text = re.sub(r'^oauth_client_id\s*=.*$', '', text, flags=re.M)
text += '\noauth_client_id=785d7402-026c-44d0-ae65-d4b29eb27d3c\n'
properties.write_text(text, 'utf-8')

file = module / 'build.gradle.kts'
text = file.read_text('utf-8')
for old, new in {
    'applicationId = zalithPackageName': 'applicationId = "io.github.reunionsama.auroralauncher"',
    'applicationIdSuffix = ".v2"': 'applicationIdSuffix = ".android"',
    'applicationIdSuffix = ".debug"': '// Independent alpha2 package; old alpha can remain installed.',
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
text = text.replace(marker, marker + '\n                        Text(text = "AuroraLauncher 安卓实验版。基于 Zalith Launcher 2 / PojavLauncher 开源实现，遵循 GPL-3.0-or-later；原作者和第三方组件的版权与致谢保留。")', 1)
file.write_text(text, 'utf-8')

res = module / 'src/main/res'
foreground = '''<vector xmlns:android="http://schemas.android.com/apk/res/android" android:width="108dp" android:height="108dp" android:viewportWidth="108" android:viewportHeight="108">
    <path android:fillColor="#09B9CA" android:pathData="M54,24 L64,44 L84,54 L64,64 L54,84 L44,64 L24,54 L44,44 Z"/>
    <path android:fillColor="#E4FAFF" android:pathData="M54,43 L65,54 L54,65 L43,54 Z"/>
</vector>'''
(res / 'drawable/ic_launcher_foreground.xml').write_text(foreground, 'utf-8')
(res / 'drawable/ic_launcher_monochrome.xml').write_text(foreground.replace('#09B9CA', '#FFFFFF'), 'utf-8')
(res / 'values/ic_launcher_background.xml').write_text('<resources><color name="ic_launcher_background">#101C25</color></resources>', 'utf-8')
audit = replace_branding(module)
# Configure the actual OAuth call sites, not just a label or a metadata file.
auth_file = module / 'src/main/java/com/movtery/zalithlauncher/game/account/microsoft/MicrosoftAuthenticator.kt'
auth = auth_file.read_text('utf-8')
client_id = '785d7402-026c-44d0-ae65-d4b29eb27d3c'
auth = auth.replace('private const val TAG = "MicrosoftAuth"', 'private const val TAG = "MicrosoftAuth"\nprivate const val AURORA_OAUTH_CLIENT_ID = "' + client_id + '"')
if auth.count('BuildKeys.OAUTH_CLIENT_ID') != 3:
    raise RuntimeError('Upstream OAuth client ID call sites changed')
auth = auth.replace('BuildKeys.OAUTH_CLIENT_ID', 'AURORA_OAUTH_CLIENT_ID')
a = auth.index('suspend fun fetchDeviceCodeResponse(')
b = auth.index('\n/**', a)
auth = auth[:a] + '''suspend fun fetchDeviceCodeResponse(context: CoroutineContext): DeviceCodeResponse = coroutineScope {
    withRetry {
        try {
            submitForm<DeviceCodeResponse>(
                url = "$MICROSOFT_AUTH_URL$TENANT/oauth2/v2.0/devicecode",
                parameters = Parameters.build {
                    append("client_id", AURORA_OAUTH_CLIENT_ID)
                    append("scope", SCOPES.joinToString(" "))
                },
                context = context
            )
        } catch (e: ClientRequestException) {
            val body = runCatching { e.response.safeBodyAsJson<JsonObject>() }.getOrNull()
            val error = body?.get("error").text()
            val detail = body?.get("error_description").text().take(800)
            throw IllegalStateException("Microsoft 设备码申请失败 (${e.response.status.value}): $error\\n$detail", e)
        }
    }
}
''' + auth[b:]
# No non-standard tenant form field; keep the v2 token endpoint for refresh too.
auth = auth.replace('                    append("tenant", TENANT)\n', '')
auth = auth.replace('pollingInterval += 1000L', 'pollingInterval += 5000L')
auth = auth.replace('url = "$LIVE_AUTH_URL/oauth20_token.srf",', 'url = "$MICROSOFT_AUTH_URL$TENANT/oauth2/v2.0/token",')
auth_file.write_text(auth, 'utf-8')
if 'BuildKeys.OAUTH_CLIENT_ID' in auth or auth.count('append("client_id", AURORA_OAUTH_CLIENT_ID)') != 3:
    raise RuntimeError('OAuth configuration verification failed')
(module / 'src/main/assets').mkdir(parents=True, exist_ok=True)
(module / 'src/main/assets/AURORA_BUILD_INFO.json').write_text(json.dumps({
    'version': 'alpha2', 'client_id': client_id,
    'package': 'io.github.reunionsama.auroralauncher.android',
    'branding_audit': audit,
    'signature_note': 'CI test-signed; final deliverable is locally re-signed with a private persistent key.'
}, ensure_ascii=False, indent=2), 'utf-8')

notice = '''AuroraLauncher Alpha4
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
The CI APK is test-signed. The delivered APK is re-signed locally with a persistent
private Aurora key. Alpha3 retains the Alpha2 package and signing key for updates.
Alpha1 has a distinct package ID and no automatic data migration is claimed.
Arm64 build: Android 8.0+ on 64-bit ARM devices only. No physical-device or
Minecraft gameplay test is claimed by the build. Microsoft login additionally
requires an application configuration accepted by Microsoft's services.
'''
(root / 'AURORA_ANDROID_NOTICE.txt').write_text(notice, 'utf-8')
assets = module / 'src/main/assets'
assets.mkdir(parents=True, exist_ok=True)
(assets / 'AURORA_ANDROID_NOTICE.txt').write_text(notice, 'utf-8')
print('Applied Aurora Android alpha identity and attribution; kept upstream engine and native namespaces.')


from redesign import apply
apply(root)


from upgrade4 import apply as apply4
apply4(root)
