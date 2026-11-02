@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" py -3.12 -m venv .venv
if not exist ".venv\Scripts\python.exe" goto fail
.venv\Scripts\python.exe -m pip install -i https://mirrors.aliyun.com/pypi/simple -r requirements-build.txt
if errorlevel 1 goto fail
.venv\Scripts\python.exe bootstrap_assets.py
if errorlevel 1 goto fail
.venv\Scripts\python.exe build_branding.py
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pytest tests -q
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean AuroraLauncher.spec
if errorlevel 1 goto fail
"dist\AuroraLauncher\AuroraLauncher.exe" --self-test --data-dir "%TEMP%\AuroraLauncher-build-test" --test-report "%CD%\windows-ui-report.json" --screenshot-dir "%CD%\windows-ui-screens"
if errorlevel 1 goto fail
 .venv\Scripts\python.exe make_installer_art.py
if errorlevel 1 goto fail
"%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" installer.iss
if errorlevel 1 goto fail
echo Built and startup-tested: dist\AuroraLauncher-Setup.exe
pause
exit /b 0
:fail
echo Build or startup test failed. See the error above.
pause
exit /b 1

