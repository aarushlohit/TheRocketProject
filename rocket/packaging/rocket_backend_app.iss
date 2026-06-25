#define MyAppName "Rocket Backend"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Rocket"
#define MyAppExeName "rocket_backend_app.exe"
#define SourceDir "..\backend_app\build\windows\x64\runner\Release"

[Setup]
AppId={{D88888E8-83F4-4C62-BB2B-80C5E60B0A27}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Rocket Backend
DefaultGroupName=Rocket
DisableProgramGroupPage=yes
OutputDir=..\dist\installer
OutputBaseFilename=RocketBackendSetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Rocket Backend"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Rocket Backend"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Rocket Backend"; Flags: nowait postinstall skipifsilent
