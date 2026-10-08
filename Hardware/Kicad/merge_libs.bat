@echo off
rem Merges the new components in KiCad_Libs_ToAdd into the official library (KiCad_Libs junction
rem made by bring_libs.bat -> C:\git\PCB\Kicad_Libs). Then: commit + push in the Kicad_Libs repo.
rem Add --clean to empty KiCad_Libs_ToAdd after a successful merge.
cd /d "%~dp0"
set SCRIPT=%~dp0tools\merge_libs.py
where python >nul 2>nul && (python "%SCRIPT%" %* & goto :end)
for %%V in (9.0 8.0) do (
  if exist "C:\Program Files\KiCad\%%V\bin\python.exe" (
    "C:\Program Files\KiCad\%%V\bin\python.exe" "%SCRIPT%" %*
    goto :end
  )
)
echo Python not found: install Python or run tools\merge_libs.py with KiCad's python.exe
:end
pause
