#include <.\IDP_1.5.1\idp.iss>

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

[ThirdParty]
UseRelativePaths=True

[Setup]
AppName={# ReadIni(INIFile, "theonionpack", "title")} 
AppVersion={# ReadIni(INIFile, "theonionpack", "version")}
AppCopyright={# ReadIni(INIFile, "theonionpack", "copyright")}
AppId={{9CF06087-6B33-44B0-B9EE-24A3EE0678C9}
UsePreviousAppDir=No
DefaultDirName=TheOnionPack
DisableWelcomePage=False
UninstallLogMode=new
PrivilegesRequired=lowest
; There's a 'bug' (better an annoyance) in Inno Script Studio that limits
; ExtraDiskSpaceRequired to 10000000 in the dialog window.
; It yet doesn't overwrite the value here - as long as we don't touch it. 
ExtraDiskSpaceRequired=83693568
MinVersion=0,6.0
LicenseFile={# LicenseFile}
WizardImageFile=compiler:WizModernImage-IS.bmp
WizardSmallImageFile=compiler:WizModernSmallImage-IS.bmp
OutputBaseFilename=TheOnionPackInstaller

[Files]
Source: "{tmp}\Python\*"; DestDir: "{app}\Python"; Flags: external recursesubdirs
Source: "{tmp}\Tor\*"; DestDir: "{app}\Tor"; Flags: external recursesubdirs
Source: "{tmp}\get-pip.py"; DestDir: "{app}\Python"; Flags: external deleteafterinstall
Source: "{# IndependenceFile}"; DestName: "INDEPENDENCE"; Flags: dontcopy
; Source: "torrc-defaults"; Flags: dontcopy
; Source: "{tmp}\torrc-defaults"; DestDir: "{app}\Tor\Data\"; Flags: external; BeforeInstall: CreateTorrcDefaults
; local package of TheOnionBox
Source: "{src}\{param:tob}"; DestDir: "{app}\Python"; DestName: "{param:tob}"; Flags: external; Check: FileExists(ExpandConstant('{src}\{param:tob}'))
; local package of TheOnionPack
Source: "{src}\{param:top}"; DestDir: "{app}\Python"; DestName: "{param:top}"; Flags: external; Check: FileExists(ExpandConstant('{src}\{param:top}'))

[Dirs]
Name: "{app}\Data"; Flags: uninsneveruninstall
Name: "{app}\Data\torrc"; Flags: uninsneveruninstall

[Icons]
Name: "{app}\TheOnionPack"; Filename: "{app}\Python\Scripts\theonionpack.exe"; WorkingDir: "{app}"; Parameters: "--tor: ""{app}\Tor"""; Comment: "Launching The Onion Pack..."

[Run]
Filename: "{app}\Python\python.exe"; Parameters: "get-pip.py ""pip>18"" --no-warn-script-location"; Flags: runhidden; StatusMsg: "Preparing the Python runtime environment..."; BeforeInstall: SetupRunConfig; AfterInstall: SetMarqueeProgress(False)
; We pip theonionbox as individual package - despite it's as well defined as dependency for theonionpack.
; This ensures that we can upgrade to the latest tob by simply re-running this (unmodified) installer.
; We can pip from a local package using /tob!
Filename: "{app}\Python\python.exe"; Parameters: "-m pip install --no-warn-script-location --upgrade ""{param:tob|theonionbox}"""; StatusMsg: "Now installing The Onion Pack. This may take some time, as a number of additional packages most probably have to be collected from the Internet..."; BeforeInstall: SetupRunConfig; AfterInstall: SetMarqueeProgress(False)
;The next line implements command line parameter /top (e.g. /top="theonionpack.tar.gz") to pip from a local package.
;Default value pips from PyPi. Using path relative to installer directory!
Filename: "{app}\Python\python.exe"; Parameters: "-m pip install --no-warn-script-location --upgrade ""{param:top|theonionpack}"""; StatusMsg: "Now installing The Onion Pack. This may take some time, as a number of additional packages most probably have to be collected from the Internet..."; BeforeInstall: SetupRunConfig; AfterInstall: SetMarqueeProgress(False)
Filename: "{app}\TheOnionPack.lnk"; WorkingDir: "{app}"; Flags: postinstall shellexec; Description: "Run The Onion Pack..."; Verb: "open"

[InstallDelete]
; To remove local pip packages
Type: files; Name: "{app}\Python\{param:tob}"; Check: FileExists(ExpandConstant('{app}\Python\{param:tob}'))
Type: files; Name: "{app}\Python\{param:top}"; Check: FileExists(ExpandConstant('{app}\Python\{param:top}'))

[UninstallRun]
Filename: "{cmd}"; Parameters: """{cmd}"" /S /C """"{app}\Python\Scripts\pip.exe"" freeze > ""{app}\unins.req"""""; Flags: runhidden
Filename: "{cmd}"; Parameters: """{cmd}"" /S /C """"{app}\Python\Scripts\pip.exe"" uninstall -y -r ""{app}\unins.req"""""; Flags: runhidden
Filename: "{app}\Python\python.exe"; Parameters: "-m pip uninstall -y pip setuptools wheel"; Flags: runhidden

[UninstallDelete]
Type: files; Name: "{app}\unins.req"
Type: dirifempty; Name: "{app}\Python\Lib\site-packages"
Type: dirifempty; Name: "{app}\Python\Lib"
Type: dirifempty; Name: "{app}\Python\service"
Type: dirifempty; Name: "{app}\Python\support\osxtemp"
Type: dirifempty; Name: "{app}\Python\support"
Type: dirifempty; Name: "{app}\Python\theonionbox\tob\system\windows"
Type: dirifempty; Name: "{app}\Python\theonionbox\tob\system"
Type: dirifempty; Name: "{app}\Python\theonionbox\tob"
Type: dirifempty; Name: "{app}\Python\theonionbox"
Type: files; Name: "{app}\Tor\Data\torrc-defaults"


[Code]
var
  // Custom page showing progress while extracting the Tor Download Link
  TorDownloadLinkPage: TOutputProgressWizardPage;

  // Independence Statement Acknowledgement Page
  IndependencePage: TOutputMsgMemoWizardPage;
  IndependenceAcceptedRadio: TRadioButton;
  IndependenceNotAcceptedRadio: TRadioButton;

procedure CreateIndependencePage(); forward;
procedure CheckIndependenceAccepted(Sender: TObject); forward;

procedure InitializeWizard();
begin
  
  // the target file shall end with '.zip' ... to later support unzipping!
  idpAddFile('https://www.python.org/ftp/python/{#py}/python-{#py}-embed-win32.zip', ExpandConstant('{tmp}\python.zip'));
  idpAddFile('https://bootstrap.pypa.io/get-pip.py', ExpandConstant('{tmp}\get-pip.py'));
 
  idpDownloadAfter(wpPreparing);

  // Initialize the custom page
  // The Tor Download Link (if found) will later (@ PrepareToInstall) be added
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
      // This enables pip operations later!
      pth := ExpandConstant('{tmp}\Python\python{#pth}._pth');    
      SaveStringsToFile(pth, ['', '# by TheOnionPack', '.\Lib\site-packages', 'import site'], true);
      
  end;
  if CurStep = ssPostInstall then 
    begin
  end;
end;

{
function NextButtonClick(CurPageID: Integer): Boolean;
begin
  LOG('NextButtonClick')
  Result:= True;
  if CurPageID = wpLicense then begin
    // Create the page to acknowledge the Statement of Independence
    CreateIndependencePage();
  end;
end;
}

procedure CurPageChanged(CurPageID: Integer);
begin

  // Update Next button when user gets to second license page
  if CurPageID = IndependencePage.ID then
  begin
    CheckIndependenceAccepted(nil);
  end;

end;


function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  html: array of string;
  tor, link: string;
  check: Boolean;

begin

  // Extract the Tor Download Link from the Tor Website
  // This serves as well to verify that an internet connection is present.
  
  TorDownloadLinkPage.SetText('Fetching Tor Download Webpage...', '');
  TorDownloadLinkPage.SetProgress(0, 1);
  TorDownloadLinkPage.Show;
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
    TorDownloadLinkPage.SetProgress(1, GetArrayLength(html));
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
      // We have a link! Let's append it to the download queue:
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
  { Update Next button when user (un)accepts the license }
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

procedure CreateTorrcDefaults();
var
  torrcFileName: string;
  lines: array of string;
  i: integer;
begin
  torrcFileName := 'torrc-defaults';
  ExtractTemporaryFile(torrcFileName);
  LoadStringsFromFile(ExpandConstant('{tmp}\' + torrcFileName), lines);
  for i := 0 to GetArrayLength(lines) - 1  do begin
    lines[i] := ExpandConstant(lines[i]);
  end;
  SaveStringsToFile(ExpandConstant('{tmp}\' + torrcFileName), lines, false);
end;

function CheckIfExists(const FileName: string): Boolean;
begin
  Result:=FileExists(CurrentFileName);
end;