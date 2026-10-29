# AuroraLauncher Android Alpha3

Aurora is a GPL-3.0-or-later derivative of the pinned Zalith Launcher 2 Android
runtime, not an independent reimplementation of its game engine or an EXE wrapper.
Upstream commit: `a6b6fb6a63ce22c4e4fa91cc29a4d64286cd0924`.
Original authorship, third-party credits and license documents are preserved.
The main branch and Windows release are unchanged.

## Aurora additions in Alpha3

- A separate responsive workspace with searchable feature shortcuts and persistent favorites.
- Per-instance local notes, isolated by a digest of the instance path.
- Explicit preflight checks for architecture, version validity, account selection,
  memory headroom, storage and Java runtime presence. This does not replace the
  existing game's full dependency checks and never changes game settings.
- Concurrent, bounded-time network probes for Modrinth, Mojang, BMCLAPI and
  Microsoft. These measure small HTTP response latency, not download throughput.
- A bounded log tail (96 KiB / 160 lines, refreshed every two seconds only while
  visible) with pause, keyword filter, known-error hints and credential masking.
  Full original log viewing remains available. Masking is best effort.
- Searchable navigation for all eight original settings categories and all eight
  download categories; no category, engine, renderer, touch/gamepad, account,
  multiplayer, mod, world, shader or export implementation is removed.
- An Aurora maintainer card separated from upstream authors and licenses.
  Automatic update checks accept only Aurora ARM64 Android Alpha assets from this repository; Windows and upstream APKs are excluded.
  Aurora update links point to Aurora releases.
- Aurora teal is the default on fresh installs; saved themes and all original theme choices remain.
- The existing customizable home page is preserved.

The original deeper feature screens and Android runtime are still upstream-based;
this is an incremental UI/feature redesign, not a claim that every screen was
independently rewritten. New files in `overlay/` and `tests/` carry Aurora's
copyright and the same GPL-compatible license. Modified upstream files keep
upstream headers.

## Microsoft login and compatibility

The owner's public client ID is configured at all three OAuth call sites:
`785d7402-026c-44d0-ae65-d4b29eb27d3c`. Device-code registration is tested without
printing/storing codes or signing in to anyone's account. Full Xbox/Minecraft
login and game launch require phone testing.

Arm64-v8a, Android 8+. Package `io.github.reunionsama.auroralauncher.android`,
versionCode `200048`, version name `2.7.2-Aurora-alpha3-debug`.
The delivered APK is signed with the same private persistent key as Alpha2 so
it can update Alpha2 in place. CI artifacts use a separate ephemeral test key;
do not install those on top of the privately signed deliverable.

## Reproduction and corresponding source

Use JDK21, Android SDK/NDKs and Rust targets from
`.github/workflows/android-apk.yml`. Apply `prepare.py` to a clean checkout of
the pinned upstream (including submodules). It applies identity/authentication
fixes, then `redesign.py` copies Aurora overlays and patches navigation.
The workflow builds the ARM64 APK, runs eight focused diagnostic/update tests,
checks signature/package and publishes the full modified corresponding source,
including native submodules, recipe, build configuration and license notices.
Private signing credentials are excluded.

No physical-phone install, complete sign-in, multiplayer session or gameplay
verification is claimed by CI compilation or local APK signature verification.


## Alpha4

App label and final asset: AuroraLauncher / AuroraLauncher.apk. Same application ID
and private Alpha2 signing key preserve upgrade compatibility. Native procedural
skeleton adds 20 distinct poses; home enables drag-to-yaw and 15-second randomized
gestures. New aurora sky is drawn at screen resolution, with 30/15 FPS, brightness,
hue, speed and on/off controls. This is a procedural visual effect, not filmed footage.
Main About removes donor/logo cards and consolidates attribution and all library
licenses into an expandable section; original headers and notices remain.

Update source is reunionSama/AuroraLauncher-Android releases, with raw GitHub release
body shown in-app. Startup and game launch check the feed; new APK downloads use
Android DownloadManager, support cancellation and survive activity recreation.
Before install: optional GitHub SHA256, same package, higher version and same
signing certificate are required. Android permission and package installation
still require user interaction. Unknown newer generic APKs are recognized using
asset update time and validated by their actual package metadata after downloading.
No artificial update is published merely to exercise this feature.
