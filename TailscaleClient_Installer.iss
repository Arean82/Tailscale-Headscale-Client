; Inno Setup Script for Tailscale-Headscale Client Pro
[Setup]
AppName=Tailscale Client Pro
AppVersion=5.0.0
AppCopyright=Copyright (c) 2026 Arean82. All rights reserved.
VersionInfoVersion=5.0.0.0
VersionInfoTextVersion=5.0.0
DefaultDirName={autopf}\TailscaleClientPro
DefaultGroupName=Tailscale Client Pro
UninstallDisplayIcon={app}\Tailscale VPN Client Pro.exe
Compression=lzma2
SolidCompression=yes
OutputDir=dist\installer
OutputBaseFilename=TailscaleClientPro_Setup
SetupIconFile=assets\icon.ico
; Ensure the folder is removed even if it contains logs/database
ChangesAssociations=yes

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
; Cleanup all files in the directory including logs and DB created during runtime
Type: filesandordirs; Name: "{app}"
