#define AppName "smi2assF"
#define AppExeName "smi2assF.exe"

[Setup]
AppId={{D037DE16-5DD8-4E87-8C9D-5A4D19B6E2A1}
AppName={#AppName}
AppVerName={#AppName}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
Uninstallable=yes
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
SetupIconFile=..\assets\smi2ass.ico
UninstallDisplayIcon={app}\{#AppExeName}
OutputDir=..\build\gui-dist
OutputBaseFilename=smi2assF.windows-x86_64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\build\gui-stage\smi2assF.exe"; DestDir: "{app}"; DestName: "{#AppExeName}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: postinstall nowait skipifsilent
