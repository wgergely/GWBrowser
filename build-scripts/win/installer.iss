; The installer script takes care of deploying Bookmarks and sets
; BOOKMARKS_ROOT environment variable to point to the
; install root. This is used by the Maya Pluging to load the python dependencies
; shipped with Bookmarks.
; We're not distributing the

#define MyAppName "Bookmarks"
#define MyAppVersion "0.3.5"
#define MyAppPublisher "Gergely Wootsch"
#define MyAppURL "http://gergely-wootsch.com/bookmarks"
#define MyAppExeName "bookmarks.exe"
#define MyAppExeDName "bookmarks_d.exe"


[Setup]
; NOTE: The value of AppId uniquely identifies this application. Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{43C00B91-E185-48A1-9FF0-0A90F0AB831C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}

ArchitecturesInstallIn64BitMode=x64
ArchitecturesAllowed=x64
DisableDirPage=false
DisableProgramGroupPage=false
; The [Icons] "quicklaunchicon" entry uses {userappdata} but its [Tasks] entry has a proper IsAdminInstallMode Check.
UsedUserAreasWarning=no
; Uncomment the following line to run in non administrative install mode (install for current user only.)
PrivilegesRequired=lowest
OutputDir={#SourcePath}..\..\..\{#MyAppName}-standalone


ChangesEnvironment=yes
ChangesAssociations=yes

OutputBaseFilename={#MyAppName}_setup_{#MyAppVersion}
SetupIconFile={#SourcePath}..\..\bookmarks\rsc\icon.ico

;Compression
;https://stackoverflow.com/questions/40447498/best-compression-settings-in-inno-setup-compiler
SolidCompression=no
Compression=lzma2/ultra64
LZMAUseSeparateProcess=yes
LZMADictionarySize=65536
LZMANumFastBytes=64

WizardStyle=modern
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=
VersionInfoTextVersion=
VersionInfoCopyright={#MyAppPublisher}
VersionInfoProductName=
VersionInfoProductVersion=
AppCopyright={#MyAppPublisher}
ShowLanguageDialog=no
WizardImageFile={#SourcePath}inno\WIZMODERNIMAGE.BMP
WizardImageBackColor=clGray
WizardSmallImageFile={#SourcePath}inno\WIZMODERNSMALLIMAGE.BMP
UsePreviousGroup=false
UninstallDisplayIcon={#SourcePath}..\..\bookmarks\rsc\icon.ico
UninstallDisplayName={#MyAppName}

[Languages]
Name: english; MessagesFile: compiler:Default.isl

[installDelete]
Type: filesandordirs; Name: {app}

[Tasks]
Name: desktopicon; Description: {cm:CreateDesktopIcon}; GroupDescription: {cm:AdditionalIcons}; Flags: unchecked
Name: quicklaunchicon; Description: {cm:CreateQuickLaunchIcon}; GroupDescription: {cm:AdditionalIcons}; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Components]
Name: standalone; Description: Standalone; Types: full compact custom; Flags: fixed;
Name: maya; Description: mBookmarks: Maya Plugin; Types: full; Check: DirExists(ExpandConstant('{userdocs}\maya'))

[Files]
; VC++ redistributable runtime. Extracted by VC2017RedistNeedsInstall(), if needed.
Source: "{#SourcePath}..\..\..\{#MyAppName}-standalone\VC_redist.x64.exe"; DestDir: "{tmp}"; Flags: dontcopy
; Main contents
Source: "{#SourcePath}..\..\..\{#MyAppName}-standalone\{#MyAppName}\*"; DestDir: "{app}"; Components: standalone; Flags: ignoreversion recursesubdirs createallsubdirs; Permissions: users-modify
; Maya plugin -- mBookmarks.py
Source:  "{#SourcePath}..\..\..\{#MyAppName}-standalone\{#MyAppName}\shared\{#MyAppName}\maya\mBookmarks.py"; DestDir: {userdocs}\maya\plug-ins; Components: maya; Flags: ignoreversion recursesubdirs createallsubdirs; Permissions: users-modify
; Example templates
Source:  "{#SourcePath}..\..\example-templates\bookmarks_asset.zip"; DestDir: "{localappdata}\{#MyAppName}\asset_templates"; Flags: ignoreversion recursesubdirs createallsubdirs; Permissions: users-modify
Source:  "{#SourcePath}..\..\example-templates\bookmarks_job.zip"; DestDir: "{localappdata}\{#MyAppName}\job_templates"; Flags: ignoreversion recursesubdirs createallsubdirs; Permissions: users-modify


[Registry]
; Used by the DCC plugins and the standalone executable to locate the install dir
Root: HKCU; Subkey: "Environment"; \
    ValueType: expandsz; ValueName: "BOOKMARKS_ROOT"; ValueData: "{app}";

; Extension
Root: HKCU; Subkey: "Software\Classes\.favourites"; ValueData: "{#MyAppName}"; Flags: uninsdeletevalue; ValueType: string;  ValueName: ""
Root: HKCU; Subkey: "Software\Classes\{#MyAppName}"; ValueData: "Program {#MyAppName}";  Flags: uninsdeletekey; ValueType: string;  ValueName: ""
Root: HKCU; Subkey: "Software\Classes\{#MyAppName}\DefaultIcon"; ValueData: "{app}\{#MyAppExeName},0"; ValueType: string;  ValueName: ""

; Install path
Root: HKCU; Subkey: "Software\{#MyAppName}\{#MyAppName}";  ValueData: "{app}\{#MyAppExeName}";  ValueType: string;  ValueName: "installpath"
Root: HKCU; Subkey: "Software\{#MyAppName}\{#MyAppExeDName}";  ValueData: "{app}\{#MyAppExeDName}";  ValueType: string;  ValueName: "installpath"

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: {cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}; Flags: nowait postinstall skipifsilent
Filename: "{tmp}\VC_redist.x64.exe"; StatusMsg: "{cm:InstallingVCRedist}"; Parameters: "/quiet"; Check: VCRedistNeedsInstall ; Flags: waituntilterminated

[CustomMessages]
InstallingVCRedist=Installing Microsoft Visual C++ Redistributable for Visual Studio 2015, 2017 and 2019...

[Code]
function VCRedistNeedsInstall: Boolean;
var
  Version: String;
begin
  if (RegQueryStringValue(HKEY_LOCAL_MACHINE, 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64', 'Version', Version)) then
  begin
    // Is the installed version at least 14.14 ?
    Log('VC Redist Version check : found ' + Version);
    Result := (CompareStr(Version, 'v14.14.26429.03')<0);
  end
  else
  begin
    // Not even an old version installed
    Result := True;
  end;
  if (Result) then
  begin
    ExtractTemporaryFile('VC_redist.x64.exe');
  end;
end;
