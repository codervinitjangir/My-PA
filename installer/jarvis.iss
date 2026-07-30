; installer/jarvis.iss
; Inno Setup Compiler Script for JARVIS v1.0 RC1 Setup Installer (JARVIS_Setup.exe)

#define MyAppName "J.A.R.V.I.S Desktop"
#define MyAppVersion "1.0.0-rc1"
#define MyAppPublisher "Deepmind Advanced Agentic Coding"
#define MyAppURL "https://github.com/codervinitjangir/My-PA"
#define MyAppExeName "JARVIS.exe"

[Setup]
AppId={{55A601C1-A3AB-4542-AB43-C4910DDD6052}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\installer_output
OutputBaseFilename=JARVIS_Setup_v1.0_RC1
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "Launch JARVIS automatically on Windows startup"; GroupDescription: "Startup Settings"

[Files]
Source: "..\dist\JARVIS\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
