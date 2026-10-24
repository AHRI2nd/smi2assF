#define AppName "smi2assF"
#define AppExeName "smi2assF.exe"
#ifndef WindowsArchitecture
#define WindowsArchitecture "x64"
#endif
#if WindowsArchitecture == "arm64"
#define AppId "AF94EC15-0A57-4072-B235-340D690F2C58"
#define AllowedArchitecture "arm64"
#define InstallArchitecture "arm64"
#define InstallerName "smi2assF.windows-arm64"
#define InstallDirectory "smi2assF-arm64"
#define ShortcutGroup "smi2assF ARM64"
#else
#define AppId "D037DE16-5DD8-4E87-8C9D-5A4D19B6E2A1"
#define AllowedArchitecture "x64"
#define InstallArchitecture "x64"
#define InstallerName "smi2assF.windows-x86_64"
#define InstallDirectory "smi2assF"
#define ShortcutGroup "smi2assF"
#endif

[Setup]
AppId={{{#AppId}}}
AppName={#AppName}
AppVerName={#AppName}
DefaultDirName={localappdata}\Programs\{#InstallDirectory}
DefaultGroupName={#ShortcutGroup}
PrivilegesRequired=lowest
Uninstallable=yes
DisableStartupPrompt=yes
DisableProgramGroupPage=yes
ArchitecturesAllowed={#AllowedArchitecture}
ArchitecturesInstallIn64BitMode={#InstallArchitecture}
SetupIconFile=..\assets\smi2ass.ico
UninstallDisplayIcon={app}\{#AppExeName}
OutputDir=..\build\gui-dist
OutputBaseFilename={#InstallerName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\build\gui-stage\smi2assF.exe"; DestDir: "{app}"; DestName: "{#AppExeName}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#ShortcutGroup}"; Filename: "{app}\{#AppExeName}"

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: postinstall nowait skipifsilent
