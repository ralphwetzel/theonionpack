#include <.\IDP_1.5.1\idp.iss>

; The Onion Pack
; Definition file for the Inno Setup compiler.
; Copyright 2019 - 2020 Ralph Wetzel
; License MIT
; https://www.github.com/ralphwetzel/theonionpack

; =====
; Supported COMPILER command line parameter:
; "/Dtheonionpack=<path to theonionpack-xx.x.tar.gz>": To include a locally (at installer compilation time)
;                                                      provided package of theonionpack into the installer.
;                                                      The installer will only include a package with matching
;                                                      version number & adequate labeling!

; =====
; Supported INSTALLER command line parameters:
; /tob="theonionbox-xx.x.tar.gz":   To install from a locally (at setup time) provided packache of The Onion Box
;                                   (rather then pip'ing this from online).
; /top="theonionpack-xx.x.tar.gz":  To install a locally (at setup time) provided packache of The Onion Pack
;                                   (rather then using the one from this installer or pip'ing it from online).

; All default INSTALLER commandline options are supported as well.
; In case of trouble - to enable logging - use:
; /LOG              Create a log file in the user's TEMP directory
; /LOG="filename"   Create a log file at the specified path.
; For further reference: http://www.jrsoftware.org/ishelp/index.php?topic=setupcmdline

; =====
; The Python version to be used is configured via an INI file.
; This ensures that compatibility can be tested ... to avoid side effects. 
#define INIFile RemoveBackslash(SourcePath) + "\..\theonionpack\setup.ini"

; The license file
#define LicenseFile RemoveBackslash(SourcePath) + "\..\LICENSE"

; Statement of Independence
#define IndependenceFile RemoveBackslash(SourcePath) + "\..\INDEPENDENCE"

; py shall become something like '3.7.6'
#define py ReadIni(INIFile, "python", "version")
; for pth we extract the first two digits of py      
#define pth Copy(StringChange(py, '.', ''), 1, 2)

; Tor Download page
#define tor ReadIni(INIFile, "tor", "download")

; Name / Title
#define __title__ ReadIni(INIFile, "theonionpack", "title")
; Version
#define __version__ ReadIni(INIFile, "theonionpack", "version")
; Description
#define __description__ ReadIni(INIFile, "theonionpack", "description")
; Copyright
#define __copyright__ ReadIni(INIFile, "theonionpack", "copyright")

[ThirdParty]
UseRelativePaths=True

[Setup]
AppName={# __title__ } 
AppVersion={# __version__}
AppCopyright={# __copyright__ }
AppId={{9CF06087-6B33-44B0-B9EE-24A3EE0678C9}
DefaultDirName={userpf}\TheOnionPack
DisableWelcomePage=False
UninstallLogMode=new
PrivilegesRequired=lowest
; There's a 'bug' (better an annoyance) in Inno Script Studio that limits
; ExtraDiskSpaceRequired to 10000000 in the dialog window.
; It yet doesn't overwrite the value here - as long as we don't touch it. 
ExtraDiskSpaceRequired=87439216
MinVersion=0,6.0
LicenseFile={# LicenseFile}
WizardImageFile=compiler:WizModernImage-IS.bmp
WizardSmallImageFile=compiler:WizModernSmallImage-IS.bmp
OutputBaseFilename=TheOnionPack
DefaultGroupName=The Onion Pack
AppPublisher=Ralph Wetzel
AppComments={# __description__}
VersionInfoVersion={# __version__}
VersionInfoDescription={# __description__}
VersionInfoProductName={# __title__}
VersionInfoCopyright={# __copyright__}
DisableProgramGroupPage=yes
ArchitecturesInstallIn64BitMode=x64
DisableDirPage=no

[Files]
; The statement of Independence; only used by the installer.
Source: "{# IndependenceFile}"; DestName: "INDEPENDENCE"; Flags: dontcopy
;
; Those file were downloaded & unziped into the {tmp} directory.
; Will be copied to {app} now. Inno keeps record of these files for later uninstall.
Source: "{tmp}\Python\*"; DestDir: "{app}\Python"; Flags: external recursesubdirs
Source: "{tmp}\Tor\*"; DestDir: "{app}\Tor"; Flags: external recursesubdirs
Source: "{tmp}\get-pip.py"; DestDir: "{app}\Python"; Flags: external deleteafterinstall
;
; The next line supports a CommandLine parameter for the Inno Setup COMPILER!
; This can be invoked by "/Dtheonionpack=<path to theonionpack-xx.x.tar.gz>"
; If defined, this package will become part of the installer.
; If not, we'll pip the package - either local or from PyPI
#ifdef theonionpack
  #define top_file ExtractFilePath(theonionpack) + 'theonionpack-' + __version__ + '.tar.gz'
  #if FileExists(top_file)
    #define theonionpack top_file
    #pragma message "TheOnionPack package @ '" + theonionpack + "' will be included in this installer."
    Source: "{# theonionpack}"; DestDir: "{app}\Python"; DestName: "{# ExtractFileName(theonionpack)}"; Flags: deleteafterinstall
  #else
    #pragma error "FileNotFound: TheOnionPack package @ '" + theonionpack + "'!"
    #undef theonionpack
  #endif
#endif
;
; local package of TheOnionBox: CommandLine parameter to the INSTALLER
; As the Inno compiler is changing the CurrentWorkingDirectory (due to whatever reason) while processing,
; GetAbsSourcePath was added to work with the absolute path of a file - if the input is relative or absolute.
; CheckIfExists as well calls GetAbsSourcePath to verify file existance.
Source: "{code:GetAbsSourcePath|{param:tob}}"; \
    DestDir: "{app}\Python"; \
    DestName: "{code:ExtractFN|{param:tob}}"; \
    Flags: external deleteafterinstall; \
    Check: CheckIfExists(ExpandConstant('{param:tob}'))
;
; local package of TheOnionPack: CommandLine parameter to the INSTALLER
Source: "{code:GetAbsSourcePath|{param:tob}}"; \
    DestDir: "{app}\Python"; \
    DestName: "{code:ExtractFN|{param:top}}"; \
    Flags: external deleteafterinstall; \
    Check: CheckIfExists(ExpandConstant('{param:top}'))
;
; An icon ...
; Source: "..\theonionpack\icons\top256.ico"; DestDir: "{app}"; Attribs: hidden
;
; This adds support to install obfs4proxy.
; Prerequisite is 'obfs4proxy.exe' being present in the same directoy as this installer file.
; A GitHub action is established to compile obfs4proxy & put it there - as requested.
; If the file is found, we provide it as an optional component for installation.
#define obfs_file RemoveBackslash(SourcePath) + "\obfs4proxy.exe"
#if FileExists(obfs_file)
  #pragma message "obfs4proxy support will be included in this installer."
  Source: "{# obfs_file}"; \
    DestDir: "{app}\Tor\Tor\PluggableTransport"; \
    DestName: "{# ExtractFileName(obfs_file)}"; \
    Tasks: obfs4proxy
#else
  #pragma message "'obfs4proxy.exe' not found. No obfs4proxy support with this installer."
  #undef obfs_file
#endif

[Dirs]
; Those two directories hold the data of the Tor relay (e.g. fingerprints).
; We'll never touch them!
Name: "{app}\Data"; Flags: uninsneveruninstall
Name: "{app}\Data\torrc"; Flags: uninsneveruninstall

; Clean the Python directory from support files of TheOnionBox (> TOBv20.2).
Name: "{app}\Python\theonionbox"; Flags: deleteafterinstall

[Icons]
; This link gets the path to the Tor as a command line parameter.
Name: "{app}\The Onion Pack"; \
    Filename: "{app}\Python\Scripts\theonionpack.exe"; \
    WorkingDir: "{app}"; \
    Flags: runminimized; \
    Parameters: "--tor ""{app}\Tor"""; \
    Comment: "Launching The Onion Pack..."

; This autostart link gets the path to the Tor as a command line parameter.
Name: "{userstartup}\The Onion Pack"; \
    Filename: "{app}\Python\Scripts\theonionpack.exe"; \
    WorkingDir: "{app}"; \
    Flags: runminimized; \
    Parameters: "--tor ""{app}\Tor"""; \
    Comment: "Launching The Onion Pack..."; \
    Tasks: startup

; And finally: A desktop icon...    
Name: "{userdesktop}\The Onion Pack"; \
    Filename: "{app}\Python\Scripts\theonionpack.exe"; \
    WorkingDir: "{app}"; \
    Flags: runminimized; \
    Parameters: "--tor ""{app}\Tor"""; \
    Comment: "Launching The Onion Pack...";

[CustomMessages]
MSG_INSTALLING_TOP=Now installing The Onion Pack. This may take some time, as a number of additional packages most probably have to be collected from the Internet...
MSG_FAILED_PIP=Unfortunately we were not able to orderly setup the Python environment.
MSG_FAILED_TOB=We failed to install the necessary packages for The Onion Pack into our Python environment.
MSG_FAILED_TOP=We failed to add The Onion Pack to the Python environment.
MSG_FAILED_FINISHED=Setup failed to install The Onion Pack on your computer. You may run the uninstaller to remove now the obsolete remainders of this procedure. Sorry for this inconvenience!

[Tasks]
Name: "startup"; Description: "Start The Onion Pack when you start Windows."; GroupDescription: "Autostart"; Flags: unchecked
#ifdef obfs_file
  Name: "obfs4proxy"; Description: "Install obfs4proxy {# GetFileVersion(obfs_file)}"; GroupDescription: "Obfuscation Support"; Flags: unchecked
#endif

[Run]
; Those runners check - parameter AfterInstall - if a dedicated file (that was part of the current step of installation) exists.
; If not, ConfirmInstallation raises a MsgBox and sets the error flag - to abort installation.
; From step two on, ConfirmNoInstallError (parameter Check) confirms that the error flag is down. If raised, this step is skipped.

; We start by getting pip.
Filename: "{app}\Python\python.exe"; \
  Parameters: "get-pip.py ""pip>18"" --no-warn-script-location"; \
  Flags: runhidden; \
  StatusMsg: "Preparing the Python runtime environment..."; \
  BeforeInstall: SetupRunConfig; \
  AfterInstall: ConfirmInstallation('pip.exe', ExpandConstant('{cm:MSG_FAILED_PIP}'))
;
; We pip theonionbox as individual package - despite it's as well defined as dependency for theonionpack.
; This ensures that we can upgrade to the latest tob by simply re-running this (unmodified) installer.
; We can pip from a local package using /tob!
Filename: "{app}\Python\python.exe"; \
  Parameters: "{code:create_pip_command|{param:tob|theonionbox}}"; \
  Flags: runhidden; \
  StatusMsg: {cm:MSG_INSTALLING_TOP}; \
  Check: ConfirmNoInstallError; \
  BeforeInstall: SetupRunConfig; \
  AfterInstall: ConfirmInstallation('theonionbox.exe', ExpandConstant('{cm:MSG_FAILED_TOB}'))
;
;The next line implements command line parameter /top (e.g. /top="theonionpack.tar.gz") to pip from a local package.
;There are 2 scenarios - depending on the COMPILER command line parameter 'theonionpack'
; #1) This installer carries a (default) package - thus #ifdef theonionpack:
;       In this case, the local package will be installed, if it exists. If not, we'll install the default package.
; #2) This installer carries NO (default) package (#ifndef theonionpack):
;       Then we'll pip the local package, if it exists. If not, we'll try to pip from PyPI.
#ifdef theonionpack
  Filename: "{app}\Python\python.exe"; \
    Parameters: "{code:create_pip_command|{param:top|{#theonionpack}}}"; \
    Flags: runhidden; \
    StatusMsg: {cm:MSG_INSTALLING_TOP}; \
    Check: ConfirmNoInstallError; \
    BeforeInstall: SetupRunConfig; \
    AfterInstall: ConfirmInstallation('theonionpack.exe', ExpandConstant('{cm:MSG_FAILED_TOP}'))
#else
  Filename: "{app}\Python\python.exe"; \
    Parameters: "{code:create_pip_command|{param:top|theonionpack}}"; \
    Flags: runhidden; \
    StatusMsg: {cm:MSG_INSTALLING_TOP}; \
    Check: ConfirmNoInstallError; \
    BeforeInstall: SetupRunConfig; \
    AfterInstall: ConfirmInstallation('theonionpack.exe', ExpandConstant('{cm:MSG_FAILED_TOP}'))
#endif

; We offer 'Run The Onion Pack...' if there was no install error.
Filename: "{app}\The Onion Pack.lnk"; \
  WorkingDir: "{app}"; \
  Flags: postinstall shellexec; \
  Description: "Run The Onion Pack..."; \
  Verb: "open"; \
  Check: ConfirmNoInstallError;

; Alternatively, we propose 'Run Uninstaller...' if an error occured!
Filename: "{uninstallexe}"; \
  Flags: postinstall shellexec; \
  Description: "Run Uninstaller..."; \
  Verb: "open"; \
  Check: IfInstallationError;


[InstallDelete]
; InstallDelete ... deletes files as the first step of installation!!
; Thus it's of no use for us!


[UninstallRun]
; To uninstall, we freeze the Python environment and write the names of the currently installed packages
; into a dedicated file (unins.req).
Filename: "{cmd}"; Parameters: """{cmd}"" /S /C """"{app}\Python\Scripts\pip.exe"" freeze > ""{app}\unins.req"""""; Flags: runhidden
; This done, we ask pip to remove all those packages.
Filename: "{cmd}"; Parameters: """{cmd}"" /S /C """"{app}\Python\Scripts\pip.exe"" uninstall -y -r ""{app}\unins.req"""""; Flags: runhidden
; Finally pip may remove itself & it's friends.
Filename: "{app}\Python\python.exe"; Parameters: "-m pip uninstall -y pip setuptools wheel"; Flags: runhidden


[UninstallDelete]
; Housekeeping...
Type: files; Name: "{app}\unins.req"
Type: dirifempty; Name: "{app}\Python\Lib\site-packages"
Type: dirifempty; Name: "{app}\Python\Lib"
Type: dirifempty; Name: "{app}\Python\service"
Type: dirifempty; Name: "{app}\Python"
; Type: dirifempty; Name: "{app}\Python\support\osxtemp"
; Type: dirifempty; Name: "{app}\Python\support"
; Type: dirifempty; Name: "{app}\Python\theonionbox\tob\system\windows"
; Type: dirifempty; Name: "{app}\Python\theonionbox\tob\system"
; Type: dirifempty; Name: "{app}\Python\theonionbox\tob"
; Type: dirifempty; Name: "{app}\Python\theonionbox"
;Type: files; Name: "{app}\Tor\Data\torrc-defaults"

[Code]
var
  // Custom page showing progress while extracting the Tor Download Link
  TorDownloadLinkPage: TOutputProgressWizardPage;

  // Independence Statement Acknowledgement Page
  IndependencePage: TOutputMsgMemoWizardPage;
  IndependenceAcceptedRadio: TRadioButton;
  IndependenceNotAcceptedRadio: TRadioButton;

  // This is the application wide Error Flag.
  error: Boolean;

procedure CreateIndependencePage(); forward;
procedure CheckIndependenceAccepted(Sender: TObject); forward;

procedure debug(message: string);
begin
  Log('[TOP] ' + message);
end;

procedure InitializeWizard();
begin

  // We are going to download Python from python.org...
  // ... and get-pip.py from pypa,io.

  // the target file shall end with '.zip' ... to later support unzipping!
  if Is64BitInstallMode() = True then begin
    // Let's try to use the 64bit version of Python ... if running on Win64
    debug('We are going to install the 64bit version of Python.');
    idpAddFile('https://www.python.org/ftp/python/{#py}/python-{#py}-embed-amd64.zip', ExpandConstant('{tmp}\python.zip'));
  end else begin
    idpAddFile('https://www.python.org/ftp/python/{#py}/python-{#py}-embed-win32.zip', ExpandConstant('{tmp}\python.zip'));
  end;
  idpAddFile('https://bootstrap.pypa.io/get-pip.py', ExpandConstant('{tmp}\get-pip.py'));

  // Yet we'll do this later - after the preparation stage.
  idpDownloadAfter(wpPreparing);

  // Initialize the custom page to fetch the Tor Doenload link.
  // This Link (if found) will later (@ PrepareToInstall) be added
  // to the files to be downloaded => becoming {tmp}\tor.zip
  TorDownloadLinkPage:= CreateOutputProgressPage('Extracting Download Link for current Tor version', '');

  // Create the page to acknowledge the Statement of Independence
  CreateIndependencePage();

end;


// pastebin.com/STcQLfKR
Function SplitString(const Value: string; Delimiter: string; Strings: TStrings): Boolean;
var
  S: string;
begin
  S := Value;
  if StringChangeEx(S, Delimiter, #13#10, True) > 0 then begin
    Strings.text := S;
    Result := True;
    Exit;
  end;
  Result := False;
end;


// To unzip a file; based on an answer by willw @ 20160107
// https://stackoverflow.com/questions/6065364/how-to-get-inno-setup-to-unzip-a-file-it-installed-all-as-part-of-the-one-insta
const
  SHCONTCH_NOPROGRESSBOX = 4;
  SHCONTCH_RESPONDYESTOALL = 16;

procedure UnZip(ZipPath, TargetPath: string); 
var
  Shell: Variant;
  ZipFile: Variant;
  TargetFolder: Variant;
begin
  debug('Unzipping ' + ZipPath + ' -> ' + TargetPath);

  Shell := CreateOleObject('Shell.Application');

  ZipFile := Shell.NameSpace(ZipPath);
  if VarIsClear(ZipFile) then
    RaiseException(Format('ZIP file "%s" does not exist or cannot be opened', [ZipPath]));

  TargetFolder := Shell.NameSpace(TargetPath);
  if VarIsClear(TargetFolder) then
    if CreateDir(TargetPath) <> True then 
      RaiseException(Format('Target path "%s" does not exist', [TargetPath]))
    else
      TargetFolder := Shell.NameSpace(TargetPath);

  TargetFolder.CopyHere(ZipFile.Items, SHCONTCH_NOPROGRESSBOX or SHCONTCH_RESPONDYESTOALL);

end;


// Extract the Tor Package Download Link
// html: array of string, each string representing one line of the source code of www.torproject.org/download/tor
// pbar: reference to the progressbar on the wizards page - to provide feedback
// Result: Download Link (if found), otherwize ''
function ExtractDownloadLink(const html: array of string; const pbar: TOutputProgressWizardPage): string;
var
  line, tag, address: string;
  linesplit, tagsplit: TStringList;
  i, ii, iii: Integer;
  
begin

  debug('Trying to fetch Tor download link...');

  Result:= '';

  for i := 0 to GetArrayLength(html) - 1  do begin
    line := html[i];
    pbar.SetProgress(pbar.ProgressBar.Position + 1, pbar.ProgressBar.Max);
    // find line with "class='downloadLink'" 
    if StringChangeEx(line, 'downloadLink', 'found', True) > 0 then begin
      // split this line @ ' '
      linesplit := TStringList.Create;
      if SplitString(line, ' ', linesplit) = True then begin
        for ii := 0 to linesplit.Count - 1 do begin
          // find a tag that has a 'zip' in it
          tag := linesplit.Strings[ii];
          if StringChangeEx(tag, 'zip', 'xxx', True) > 0 then begin
            // split this tag @ '"' ... to extract the address portion
            tagsplit := TStringList.Create;
            if SplitString(tag, '"', tagsplit) = True then begin
              for iii := 0 to tagsplit.Count - 1 do begin
                // check if it's in a expected format
                // ToDo: add more checks?
                address := tagsplit.Strings[iii];
                if Length(address) > 3 then begin
                  if Copy(address, Length(address) - 2, 3) = 'xxx' then begin
                    // convert back to original; found!
                    StringChangeEx(address, 'xxx', 'zip', True);
                    Result := address;
                    Break;
                   end;
                end;
              end;
            end;
            tagsplit.Free();
          end;
        end;
      end;
      linesplit.Free();
    end;
  end;

  debug('Tor Download Link: ' + Result);
end;


procedure CurStepChanged(CurStep: TSetupStep);          

var
  pth: String;

begin
  if CurStep = ssInstall then begin
      // Unzip downloaded files; will be copied by Inno to the target directory
      // Thus we support propper uninstalling later.
      UnZip(ExpandConstant('{tmp}\tor.zip'), ExpandConstant('{tmp}\Tor'));
      UnZip(ExpandConstant('{tmp}\python.zip'), ExpandConstant('{tmp}\Python'));

      // Patch Python ...
      // Mandatory to enable pip operations later!
      pth := ExpandConstant('{tmp}\Python\python{#pth}._pth');    
      SaveStringsToFile(pth, ['', '# by TheOnionPack', '.\Lib\site-packages', 'import site'], true);
      
  end;
  if CurStep = ssPostInstall then 
    begin
  end;
end;


procedure CurPageChanged(CurPageID: Integer);
begin

  // Update Next button when user gets to second license page
  if CurPageID = IndependencePage.ID then
  begin
    CheckIndependenceAccepted(nil);
  end;

  // Customize FinishedPage in case of error.
  if CurPageID = wpFinished then begin
    if error = True then begin
      WizardForm.FinishedHeadingLabel.Caption := 'The Onion Pack Setup Error';
      WizardForm.FinishedLabel.Caption := ExpandConstant('{cm:MSG_FAILED_FINISHED}');
    end;  
  end;
end;


function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  html: array of string;
  tor, link, link64: string;
  check: Boolean;
  size: Int64;

begin

  // Extract the Tor Download Link from the Tor Website
  // This serves as well to verify that an internet connection is present.
  
  TorDownloadLinkPage.SetText('Fetching Tor Download Webpage...', '');
  TorDownloadLinkPage.ProgressBar.Style := npbstNormal;
  TorDownloadLinkPage.SetProgress(1, 2);
  TorDownloadLinkPage.Show;
  
  // Give the page time to setup nicely
  // Note: This does not work! :(
  Sleep(500);

  try
    // Download the website
    check := idpDownloadFile('{#tor}', ExpandConstant('{tmp}\tor.check'));      
    if check = False then begin
      // if this failed, we cannot continue.
      Result := 'Failed to fetch the Tor Download Webpage @ {#tor}' + #13#10
        + #13#10 +'Please verify that you''re connected to the Internet.';
      WizardForm.PreparingLabel.WordWrap := True;
      Exit;
    end;
    
    // Now extract the link
    TorDownloadLinkPage.SetText('Extracting Download Link...', '');
    LoadStringsFromFile(ExpandConstant('{tmp}\tor.check'), html);
    TorDownloadLinkPage.ProgressBar.Style := npbstNormal;
    TorDownloadLinkPage.SetProgress(2, GetArrayLength(html)+1);
    link := ExtractDownloadLink(html, TorDownloadLinkPage);
    // This is a very (very very) simplistic check that we found it.
    if Length(link) < 3 then begin
      // if not: ... we've got a problem!
      Result := 'Failed to extract the Tor Download Link from ' + tor + #13#10 + #13#10 +
        'Most probably the page layout has been altered recently.'#13#10 +
        'Please ckeck for an updated version of The Onion Pack or raise an issue at our GitHub page.';
      WizardForm.PreparingLabel.WordWrap := True;
      // ToDo: Add link to github & a procedure:
      // https://stackoverflow.com/questions/38934332/how-can-i-make-a-button-or-a-text-in-inno-setup-that-opens-web-page-when-clicked 
      Exit;
    end else begin
      // Check if we're in 64bit mode.
      if Is64BitInstallMode() = True then begin
        // Let's try to use the 64bit version of Tor then
        link64 := link;
        if StringChangeEx(link64, 'win32', 'win64', True) > 0 then begin
          // Check if file exists...
          if idpGetFileSize('https://www.torproject.org' + link64, size) then begin
            link := link64;
            debug('We are going to install the 64bit version of Tor @ ' + link);
          end;
        end;
      end;      
      // We finally have a link! Let's append it to the download queue:
      idpAddFile('https://www.torproject.org' + link, ExpandConstant('{tmp}\tor.zip'));

    end;
  finally
    TorDownloadLinkPage.Hide;
  end;
end;


procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);          
begin
  if CurUninstallStep = usUninstall then begin
  end;
end;


// Used while installing the python packages
// https://stackoverflow.com/questions/34336466/inno-setup-how-to-manipulate-progress-bar-on-run-section
procedure SetMarqueeProgress(Marquee: Boolean);
begin
  if Marquee then begin
    WizardForm.ProgressGauge.Style := npbstMarquee;
  end else begin
    WizardForm.ProgressGauge.Style := npbstNormal;
  end;
end;


// To be used for the lengthy status messages in the [Run] section
procedure SetupRunConfig();
begin
  SetMarqueeProgress(True);

  WizardForm.StatusLabel.WordWrap := True;
  WizardForm.StatusLabel.AdjustHeight();
end;


// Additional page to acknowledge Statement of Independence
// https://stackoverflow.com/questions/34592002/how-to-create-two-licensefile-pages-in-inno-setup
procedure CheckIndependenceAccepted(Sender: TObject);
begin
  // Update Next button when user (un)accepts the license
  WizardForm.NextButton.Enabled := IndependenceAcceptedRadio.Checked;
end;

function CloneLicenseRadioButton(Source: TRadioButton): TRadioButton;
begin
  Result := TRadioButton.Create(WizardForm);
  Result.Parent := IndependencePage.Surface;
  Result.Caption := Source.Caption;
  Result.Left := Source.Left;
  Result.Top := Source.Top;
  Result.Width := Source.Width;
  Result.Height := Source.Height;
  Result.OnClick := @CheckIndependenceAccepted;
end;

procedure CreateIndependencePage();
var
  IndependenceFileName: string;
  IndependenceFilePath: string;

begin
  
  IndependencePage :=
    CreateOutputMsgMemoPage(
      wpLicense, 'Statement of Independence', SetupMessage(msgLicenseLabel),
      'Please read the following Statement of Independence. You must ' +
      'acknowledge this statement before continuing with the installation.', '');

  // Shrink memo box to make space for radio buttons
  IndependencePage.RichEditViewer.Height := WizardForm.LicenseMemo.Height;

  // Load SoI
  // Loading ex-post, as Lines.LoadFromFile supports UTF-8,
  // contrary to LoadStringFromFile.
  IndependenceFileName := 'INDEPENDENCE';
  ExtractTemporaryFile(IndependenceFileName);
  IndependenceFilePath := ExpandConstant('{tmp}\' + IndependenceFileName);
  IndependencePage.RichEditViewer.Lines.LoadFromFile(IndependenceFilePath);
  DeleteFile(IndependenceFilePath);

  // Clone accept/do not accept radio buttons for the second license
  IndependenceAcceptedRadio :=
    CloneLicenseRadioButton(WizardForm.LicenseAcceptedRadio);
  IndependenceNotAcceptedRadio :=
    CloneLicenseRadioButton(WizardForm.LicenseNotAcceptedRadio);

  // Customize captions
  IndependenceAcceptedRadio.Caption := 'I acknowledge this statement.'
  IndependenceNotAcceptedRadio.Caption := 'I do not acknowledge this statement.'

  // Initially not accepted
  IndependenceNotAcceptedRadio.Checked := True;

end;

// To get the absolute path for any source file
function GetAbsSourcePath(const path: string): string;
var
  abs_path: string;

begin
  // check if path is absolute
  abs_path := ExpandFileName(path);
  if abs_path = path then begin
    Result := path;
  end else begin
    // if not: generate the absolute one.
    Result := ExpandConstant('{src}\' + path);
  end;
  debug('AbsPath for ' + path + ' -> ' + Result);
end;


function CheckIfExists(const FileName: string): Boolean;
var
  abs_path: string;
begin
  abs_path := GetAbsSourcePath(FileName);
  Result:=FileExists(abs_path);
  debug('Does ' + FileName + ' exist? -> ' + IntToStr(Integer(Result)));
end;

function create_pip_command(const path: string): string;
var
   r: string;
begin
    r := '-m pip install --no-warn-script-location --upgrade ""';
    r := r + ExtractFileName(path);
    Result := r + '""';
    debug('pip command: ' + Result);
end;

function ExtractFN(const path: string): string;
begin
  Result:= ExtractFileName(path);
  debug('FN of ' + path + ' -> ' + Result);
end;

// verify that filename exists. If not, emit MsgBox & set Error Flag.
procedure ConfirmInstallation(filename: string; msg: string);
begin
  if FileExists(ExpandConstant('{app}\Python\Scripts\' + filename)) = False then begin
      SetMarqueeProgress(False);
      TaskDialogMsgBox('Error',
                       msg,   
                       mbCriticalError,
                       MB_OK, [], 0);
      error := True;
      debug(filename + ' does NOT exist!');
  end else begin
      debug(filename + ' exist!');
  end;
end;

// Error Flag verification
function ConfirmNoInstallError(): Boolean;
begin
  Result := (error = False);
  debug('NoInstallError: ' + IntToStr(Integer(Result)));
end;

function IfInstallationError(): Boolean;
begin
  Result := (error = True);
  debug('InstallationError: ' + IntToStr(Integer(Result)));
end;
