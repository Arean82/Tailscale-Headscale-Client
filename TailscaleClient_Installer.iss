; Inno Setup Script for Tailscale-Headscale Client Pro
[Setup]
AppId={{8F2B1C74-5A3E-4D9B-9C21-7E4A6F0D5B83}
AppName=Tailscale Client Pro
AppVersion=5.0.0
AppVerName=Tailscale Client Pro 5.0.0
AppPublisher=Arean82
AppPublisherURL=https://github.com/Arean82/Tailscale-Headscale-Client
AppSupportURL=https://github.com/Arean82/Tailscale-Headscale-Client/issues
AppUpdatesURL=https://github.com/Arean82/Tailscale-Headscale-Client/releases
AppCopyright=Copyright (c) 2026 Arean82. All rights reserved.
VersionInfoVersion=5.0.0.0
VersionInfoTextVersion=5.0.0
VersionInfoDescription=Tailscale Client Pro Setup
; Per-machine install: enterprise deployment (Intune/SCCM) runs elevated.
PrivilegesRequired=admin
; Refuses to install while the application runs (the app creates this mutex).
AppMutex=Arean82.TailscaleClientPro
; GPL-3.0: the licence is shown before installation.
LicenseFile=LICENSE
DefaultDirName={autopf}\TailscaleClientPro
DefaultGroupName=Tailscale Client Pro
UninstallDisplayIcon={app}\Tailscale VPN Client Pro.exe
UninstallDisplayName=Tailscale Client Pro 5.0.0
Compression=lzma2
SolidCompression=yes
OutputDir=dist\installer
OutputBaseFilename=TailscaleClientPro_Setup
SetupIconFile=assets\icon.ico
; Signing: once a code-signing certificate exists, set SignTool=<tool> and
; SignedUninstaller=yes here; unsigned installers raise SmartScreen warnings.

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\TailscaleClientPro_OneDir\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Tailscale Client Pro"; Filename: "{app}\Tailscale VPN Client Pro.exe"
Name: "{autodesktop}\Tailscale Client Pro"; Filename: "{app}\Tailscale VPN Client Pro.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Tailscale VPN Client Pro.exe"; Description: "{cm:LaunchProgram,Tailscale Client Pro}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Removes the installation directory. User data is intentionally preserved:
; profiles, credentials and traffic history live in
; %APPDATA%\Tailscale_VPN_Client and must survive uninstall/upgrade.
Type: filesandordirs; Name: "{app}"
