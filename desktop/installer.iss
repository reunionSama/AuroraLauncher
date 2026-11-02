#define AppVersion "6.2.0"
[Setup]
AppId={{DB477346-1260-4774-B1D3-058F8B7DFF72}
AppName=AuroraLauncher
AppVersion={#AppVersion}
AppPublisher=reunionSama
AppPublisherURL=https://github.com/reunionSama/AuroraLauncher
AppSupportURL=https://github.com/reunionSama/AuroraLauncher/issues
AppUpdatesURL=https://github.com/reunionSama/AuroraLauncher/releases/tag/publicLauncher
DefaultDirName={localappdata}\Programs\AuroraLauncher
DefaultGroupName=AuroraLauncher
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=dist
OutputBaseFilename=AuroraLauncher-Setup
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\AuroraLauncher.exe
WizardStyle=modern
WizardSizePercent=115
WizardResizable=no
WizardImageFile=assets\setup-sidebar.bmp
WizardSmallImageFile=assets\setup-small.bmp
WizardImageStretch=yes
DisableWelcomePage=no
DisableProgramGroupPage=yes
LicenseFile=assets\GPL-3.0.txt
Compression=lzma2/fast
SolidCompression=yes
CloseApplications=yes
RestartApplications=no
UninstallDisplayName=AuroraLauncher
VersionInfoDescription=AuroraLauncher Setup
VersionInfoCompany=reunionSama
VersionInfoVersion={#AppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "chinesesimp"; MessagesFile: "installer_languages\ChineseSimplified.isl"
Name: "japanese"; MessagesFile: "installer_languages\Japanese.isl"
Name: "korean"; MessagesFile: "installer_languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\AuroraLauncher\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\AuroraLauncher"; Filename: "{app}\AuroraLauncher.exe"
Name: "{autodesktop}\AuroraLauncher"; Filename: "{app}\AuroraLauncher.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\AuroraLauncher.exe"; Description: "{cm:LaunchProgram,AuroraLauncher}"; Flags: nowait postinstall skipifsilent

[Code]
procedure InitializeWizard;
begin
  WizardForm.Color := $00F6F4ED;
  WizardForm.MainPanel.Color := clWhite;
  WizardForm.WelcomeLabel1.Font.Size := 20;
  WizardForm.WelcomeLabel1.AutoSize := False;
  WizardForm.WelcomeLabel1.Height := ScaleY(105);
  WizardForm.WelcomeLabel2.Top := WizardForm.WelcomeLabel1.Top + WizardForm.WelcomeLabel1.Height + ScaleY(12);
  WizardForm.WelcomeLabel2.Height := WizardForm.WelcomePage.Height - WizardForm.WelcomeLabel2.Top - ScaleY(16);
  WizardForm.WelcomeLabel1.Font.Color := $00382E17;
  WizardForm.WelcomeLabel2.Font.Size := 11;
  WizardForm.FinishedHeadingLabel.Font.Size := 20;
  WizardForm.PageNameLabel.Font.Color := $007B6150;
end;
