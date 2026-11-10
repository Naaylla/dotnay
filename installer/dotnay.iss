; Inno Setup script for dotnay.
; Build with: python -m PyInstaller --noconfirm dotnay.spec
;             ISCC.exe installer\dotnay.iss
; or run tools\build_installer.ps1

#define MyAppName "dotnay"
#define MyAppVersion "0.1.0"
#define MyAppExeName "dotnay.exe"

[Setup]
; A fixed AppId makes new versions upgrade the same installation.
AppId={{B3F0C8D4-6A2E-4F57-9E31-7C5D2A8B4E90}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppName}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; Per-user install: no administrator prompt. {autopf} becomes
; {localappdata}\Programs when PrivilegesRequired=lowest.
PrivilegesRequired=lowest
ChangesAssociations=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=dotnay-setup
SetupIconFile=..\dotnay\assets\nayla.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Ask the running app to close so an upgrade can replace dotnay.exe.
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\dotnay.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dotnay\assets\nayla.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\nayla.ico"; Comment: "Self-destructing notes"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\nayla.ico"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Classes\.nayla"; ValueType: string; ValueName: ""; ValueData: "dotnay.nayla"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.nayla"; ValueType: string; ValueName: "FriendlyTypeName"; ValueData: "dotnay note"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.nayla\ShellNew"; ValueType: string; ValueName: "NullFile"; ValueData: ""; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\dotnay.nayla"; ValueType: string; ValueName: ""; ValueData: "Nayla note"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\dotnay.nayla"; ValueType: string; ValueName: "FriendlyTypeName"; ValueData: "dotnay note"
Root: HKCU; Subkey: "Software\Classes\dotnay.nayla\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\nayla.ico,0"
Root: HKCU; Subkey: "Software\Classes\dotnay.nayla\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
