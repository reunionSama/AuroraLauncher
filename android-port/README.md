# AuroraLauncher Android alpha build

This branch builds an explicitly identified GPL derivative of Zalith Launcher 2,
not an EXE wrapper or the desktop Python code repackaged as Android.
Windows releases and the main branch are unchanged.

Pinned upstream: `a6b6fb6a63ce22c4e4fa91cc29a4d64286cd0924`.

The APK uses the upstream Android Java runtime, renderer support, game installer,
account UI and touch controls. Aurora adaptation adds a distinct application ID,
name, icon and prominent origin notice. All upstream copyrights, license text,
credits and third-party notices are retained.

The first build targets **arm64-v8a / Android 8+**. It is an alpha with a generated
debug signing key. No physical-device installation or gameplay validation is
implied. No Microsoft or CurseForge API keys are supplied by this recipe.

The workflow builds the APK, verifies its signature and application ID and
uploads it as an APK artifact. A separate artifact contains the full modified
corresponding source, applied recipe and build instructions under the original
licenses. The distributed APK must be accompanied by access to that source.

Reproduce on a machine with JDK 21, Android SDK/NDKs and Rust/cargo-ndk as specified
in `.github/workflows/android-apk.yml`. Apply `prepare.py` to the pinned upstream,
generate the documented test key and run the recorded Gradle command.

## Alpha2: branding and Microsoft registration

- Uses the project owner's public OAuth client ID `785d7402-026c-44d0-ae65-d4b29eb27d3c` at all three Microsoft OAuth request call sites.
- Device-code registration preflight returned HTTP 200; no user login, token polling or account credentials were used by this test. Full Xbox/Minecraft sign-in still needs device testing.
- Replaces the launcher/about raster image, fallback-density launcher icons, Play Store artwork and the original project-author/sponsor avatar images with Aurora/generic assets. Textual author credits and licenses remain.
- Uses the same Microsoft v2 token endpoint for refresh; respects the device-flow slowdown interval and reports the initial endpoint's OAuth error code/description.
- Alpha2 uses `io.github.reunionsama.auroralauncher.android` and versionCode 200047. Alpha1 used an ephemeral test key and `.android.debug`; it can remain installed so its data is not erased. No automatic data migration is claimed.
- Final delivery is locally re-signed using a private persistent Aurora key. Private keys/passwords are never added to this public repository or workflow artifacts.
