; SAM — Inno Setup installer
;
; Build order:
;   1. python tools/make_icon.py          (only after changing the icon design)
;   2. pyinstaller SAM.spec               -> dist\SAM\
;   3. iscc installer\SAM.iss             -> installer\Output\SAM-Setup-x.y.z.exe
;
; Requires Inno Setup 6.1+ (for the download page API).
;
; Per-user install by design: the Ollama installer, the HKCU Run key and the
; model downloads all work without administrator rights, and Ollama installs
; itself to the same place.

#define AppName        "SAM"
#define AppVersion     "0.4.4"
#define AppPublisher   "Samet Gurtuna"
#define AppExeName     "SAM.exe"
#define OllamaUrl      "https://ollama.com/download/OllamaSetup.exe"

[Setup]
AppId={{8E3F1C42-9D5A-4B77-A1E6-2C0B7F4D9A31}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=Output
OutputBaseFilename=SAM-Setup-{#AppVersion}
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#AppExeName}
WizardStyle=modern
Compression=lzma2/max
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; \
  GroupDescription: "Shortcuts"

Name: "startup"; Description: "Start SAM when Windows starts"; \
  GroupDescription: "Options"

Name: "installollama"; Description: "Install Ollama (required for the local AI engine)"; \
  GroupDescription: "Dependencies"; Check: not OllamaInstalled

Name: "pullmodel"; Description: "Download the language model (about 2 GB)"; \
  GroupDescription: "Models — these can also download later, on first use"

Name: "whisper"; Description: "Download the speech recognition model (about 500 MB)"; \
  GroupDescription: "Models — these can also download later, on first use"

[Files]
Source: "..\dist\SAM\*"; DestDir: "{app}"; \
  Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
  ValueType: string; ValueName: "SAM"; ValueData: """{app}\{#AppExeName}"""; \
  Flags: uninsdeletevalue; Tasks: startup

[Run]
; Ollama first — the model pull below needs it.
Filename: "{tmp}\OllamaSetup.exe"; Parameters: "/VERYSILENT /NORESTART"; \
  StatusMsg: "Installing Ollama..."; Tasks: installollama; \
  Flags: waituntilterminated

; Model downloads run through SAM.exe itself, so the installer and the app can
; never disagree about model names or download locations.
Filename: "{app}\{#AppExeName}"; Parameters: "--install-models --llm"; \
  StatusMsg: "Downloading the language model — this can take several minutes..."; \
  Tasks: pullmodel; Flags: waituntilterminated runhidden

Filename: "{app}\{#AppExeName}"; Parameters: "--install-models --whisper"; \
  StatusMsg: "Downloading the speech recognition model..."; \
  Tasks: whisper; Flags: waituntilterminated runhidden

Filename: "{app}\{#AppExeName}"; Description: "Launch SAM"; \
  Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
var
  OllamaDownloadPage: TDownloadWizardPage;

function OllamaInstalled: Boolean;
begin
  // {commonpf} kullanilmiyor: PrivilegesRequired=lowest ile Inno onu reddediyor.
  // Ortam degiskenini dogrudan okumak her iki ayricalik modunda da calisir.
  Result := FileExists(ExpandConstant('{localappdata}\Programs\Ollama\ollama.exe'))
         or FileExists(ExpandConstant('{localappdata}\Ollama\ollama.exe'))
         or FileExists(GetEnv('ProgramFiles') + '\Ollama\ollama.exe');
end;

function OnDownloadProgress(const Url, FileName: String;
  const Progress, ProgressMax: Int64): Boolean;
begin
  Result := True;
end;

procedure InitializeWizard;
begin
  OllamaDownloadPage := CreateDownloadPage(
    SetupMessage(msgWizardPreparing),
    'Downloading the Ollama installer...',
    @OnDownloadProgress);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if (CurPageID = wpReady) and WizardIsTaskSelected('installollama') then
  begin
    OllamaDownloadPage.Clear;
    OllamaDownloadPage.Add('{#OllamaUrl}', 'OllamaSetup.exe', '');
    OllamaDownloadPage.Show;
    try
      try
        OllamaDownloadPage.Download;
      except
        // Indirme basarisiz olursa kurulumu iptal etme — SAM'in kendi
        // "Ollama kurulu degil" yolu devreye girer.
        MsgBox('Could not download the Ollama installer:'#13#10 +
               GetExceptionMessage + #13#10#13#10 +
               'SAM will still be installed. You can install Ollama later ' +
               'from https://ollama.com/download',
               mbInformation, MB_OK);
      end;
    finally
      OllamaDownloadPage.Hide;
    end;
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  // Calisan bir SAM ornegi DLL'leri kilitler ve guncelleme basarisiz olur.
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM {#AppExeName}',
       '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := '';
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    // Kullanici verisi varsayilan olarak BIRAKILIR: config.yaml API
    // anahtarlarini, models\ birkac GB'lik indirmeyi tutuyor ve Ollama
    // modelleri baska istemcilerle paylasiliyor olabilir.
    if MsgBox('Also delete SAM''s settings, logs and downloaded speech models?'#13#10#13#10 +
              'Choose No to keep them for a future reinstall.'#13#10 +
              '(Ollama and its models are never removed by this uninstaller.)',
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      DelTree(ExpandConstant('{userappdata}\SAM'), True, True, True);
      DelTree(ExpandConstant('{localappdata}\SAM'), True, True, True);
    end;
  end;
end;
