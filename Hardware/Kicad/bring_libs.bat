@echo off
rem Creates the "KiCad_Libs" junction to the local clone of the official library
rem (https://github.com/L2-Hardware/Kicad_Libs), expected in C:\git\PCB\Kicad_Libs
rem i.e. three levels above this folder: <...>\PCB\Drone\Hardware\Kicad -> <...>\PCB\Kicad_Libs
cd /d "%~dp0"
set TARGET=%~dp0..\..\..\Kicad_Libs
if exist "KiCad_Libs" (
  echo KiCad_Libs junction already exists.
  goto :end
)
if not exist "%TARGET%" (
  echo Library not found in %TARGET%
  echo Clone it with: git clone https://github.com/L2-Hardware/Kicad_Libs.git
  goto :end
)
mklink /J "KiCad_Libs" "%TARGET%"
:end
pause
