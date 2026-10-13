; Inno-Setup-Skript für den DuelScan-Installer
; Bauen:  packaging\build_installer.bat   (erst PyInstaller, dann dieses Skript)
;
; Installiert pro Benutzer (keine Admin-Rechte nötig) nach %LOCALAPPDATA%\Programs\DuelScan.
; Kartendaten, Sammlung und Einstellungen liegen getrennt in %LOCALAPPDATA%\DuelScan
; und bleiben beim Deinstallieren erhalten.

#define AppName "DuelScan"
#define AppVersion "0.1.0"
#define AppExe "DuelScan.exe"

[Setup]
AppId={{6F1C2B9E-4D3A-4E8B-9C21-5A7D0E3F8B42}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=DuelScan contributors
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=Output
OutputBaseFilename=DuelScan-Setup-{#AppVersion}
SetupIconFile=..\ygo_scanner\assets\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=..\LICENSE

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "de"; MessagesFile: "compiler:Languages\German.isl"
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "fr"; MessagesFile: "compiler:Languages\French.isl"
Name: "it"; MessagesFile: "compiler:Languages\Italian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\DuelScan\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
