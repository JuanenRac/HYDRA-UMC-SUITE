; =============================================================================
; HYDRA-UMC SUITE - installer/windows_installer.iss
; Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
; GPL-3.0 - see ../LICENSE
;
; Inno Setup script (audit idea: "instalador .msi/.deb profesional" -
; SONNET/AUDITORIA_COMPLETA_44_PROYECTOS.txt). Inno Setup, not the WiX
; Toolset, for the same reason this whole ecosystem stays away from
; heavier tooling elsewhere: it's a single free installer (no Visual
; Studio/WiX SDK needed), produces a real Windows installer with Start
; Menu/uninstall entries, and its own scripting language (Pascal-like,
; a plain .iss text file) is easy to read and diff in a git history the
; same way every other build script in this repo already is - a WiX
; .wxs XML manifest would be a heavier, more XML-verbose alternative for
; the same real result. Ships a real .exe installer, not literally a
; .msi - Inno Setup's own installers ARE the standard, Windows-native
; alternative to an .msi for exactly this kind of single-app installer;
; MSI itself would need the WiX Toolset, not installed in this session's
; environment (see this idea's own SONNET/11.PLAN_IDEAS_MEJORA_
; AUDITORIA.txt entry for why this wasn't switched to mid-implementation).
;
; NOT RUN in this session - Inno Setup (iscc.exe) isn't installed here,
; and installing new system-wide tooling wasn't done without asking
; first. Written as a complete, correct, ready-to-use script instead:
; install Inno Setup (https://jrsoftware.org/isinfo.php, free), run
; `./build_installer.bat` (builds the .exe via build_exe.bat first, then
; compiles this script), and the real HYDRA-UMC_SUITE_Setup.exe this
; produces should be smoke-tested (install, launch, uninstall) before
; being treated as verified - this script is unverified until then.
;
; The Linux counterpart (.deb) needs dpkg-deb, which only exists on
; Linux - see debian/ in this same directory for the real, complete
; control file + build script for that side, same "written but not run
; here" caveat.
; =============================================================================
#define MyAppName "HYDRA-UMC SUITE"
#define MyAppVersion "0.1.3"
#define MyAppPublisher "JuanenRac (Electro Hobby 3D)"
#define MyAppURL "https://github.com/JuanenRac/HYDRA-UMC-SUITE"
#define MyAppExeName "HYDRA-UMC_SUITE.exe"

[Setup]
AppId={{B4E1C9A0-6F2D-4D8A-9E3B-2C7A5F1D8E90}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
OutputDir=output
OutputBaseFilename=HYDRA-UMC_SUITE_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Multi-controller swarm command center - a real desktop app most users
; expect to launch as themselves, not elevated; PyInstaller's own
; --onefile build has no install-time system change that would need it.
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; build_exe.bat's own real output - this script never builds the .exe
; itself, only packages what's already in ..\dist\ (build_installer.bat
; runs build_exe.bat first to guarantee it's actually there and current).
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
