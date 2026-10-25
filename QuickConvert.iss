
#define MyAppName "QuickConvert"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "QuickConvert"
#define MyAppExeName "QuickConvert.exe"

[Setup]
AppId={{B74C31E9-6C1A-4C2A-9A71-5D98E31F7A42}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\QuickConvert
DefaultGroupName=QuickConvert
DisableProgramGroupPage=yes
OutputDir=D:\PROJECTS\QuickConvertMowa\installer
OutputBaseFilename=QuickConvert-Setup
SetupIconFile=D:\PROJECTS\QuickConvertMowa\assets\icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "D:\PROJECTS\QuickConvertMowa\dist\QuickConvert\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\QuickConvert"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\QuickConvert"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\QuickConvert"; ValueType: string; ValueName: ""; ValueData: "Convert with QuickConvert"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\QuickConvert"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\QuickConvert\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.docx\shell\QuickConvert"; ValueType: string; ValueName: ""; ValueData: "Convert with QuickConvert"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.docx\shell\QuickConvert"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.docx\shell\QuickConvert\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.txt\shell\QuickConvert"; ValueType: string; ValueName: ""; ValueData: "Convert with QuickConvert"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.txt\shell\QuickConvert"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.txt\shell\QuickConvert\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\QuickConvert"; ValueType: string; ValueName: ""; ValueData: "Convert with QuickConvert"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\QuickConvert"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\QuickConvert\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\QuickConvert"; ValueType: string; ValueName: ""; ValueData: "Convert with QuickConvert"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\QuickConvert"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\QuickConvert\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\QuickConvert"; ValueType: string; ValueName: ""; ValueData: "Convert with QuickConvert"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\QuickConvert"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\QuickConvert\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\QuickConvert"; ValueType: string; ValueName: ""; ValueData: "Convert with QuickConvert"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\QuickConvert"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\QuickConvert\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\QuickConvert"; ValueType: string; ValueName: ""; ValueData: "Convert with QuickConvert"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\QuickConvert"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\QuickConvert\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\QuickConvert"; ValueType: string; ValueName: ""; ValueData: "Convert with QuickConvert"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\QuickConvert"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\QuickConvert\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\QuickConvert"; ValueType: string; ValueName: ""; ValueData: "Convert with QuickConvert"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\QuickConvert"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\QuickConvert\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\QuickConvert"; ValueType: string; ValueName: ""; ValueData: "Convert with QuickConvert"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\QuickConvert"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\QuickConvert\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.html\shell\QuickConvert"; ValueType: string; ValueName: ""; ValueData: "Convert with QuickConvert"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.html\shell\QuickConvert"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.html\shell\QuickConvert\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.htm\shell\QuickConvert"; ValueType: string; ValueName: ""; ValueData: "Convert with QuickConvert"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.htm\shell\QuickConvert"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.htm\shell\QuickConvert\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch QuickConvert"; Flags: postinstall nowait skipifsilent
