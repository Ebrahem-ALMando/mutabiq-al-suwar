#define MyAppName "مُطابق الصور"
#define MyAppVersion "2.1.1"
#define MyAppExeName "MutabiqAlSuwar.exe"

[Setup]
AppId={{A2B6BC04-4268-49BB-9C7B-C05C2E027E94}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\MutabiqAlSuwar
DefaultGroupName={#MyAppName}
OutputDir=..\installer-output
OutputBaseFilename=MutabiqAlSuwar-Setup-2.1.1
SetupIconFile=..\assets\icons\app.ico
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "arabic"; MessagesFile: "compiler:Languages\Arabic.isl"

[Tasks]
Name: "desktopicon"; Description: "إنشاء اختصار على سطح المكتب"; GroupDescription: "اختصارات إضافية:"; Flags: unchecked

[Files]
Source: "..\dist\MutabiqAlSuwar\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "تشغيل {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
    if MsgBox('هل تريد حذف السجل المحلي والملفات التعريفية والصور المصغرة؟', mbConfirmation, MB_YESNO) = IDYES then
      DelTree(ExpandConstant('{localappdata}\MutabiqAlSuwar'), True, True, True);
end;
