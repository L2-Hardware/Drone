@echo off
rem Merge the drone parts (KiCad_Libs_Drone) into KiCad_Libs (your library repo, linked by bring_libs.bat).
rem Uses the Python that ships with KiCad if no system Python is found.
set SCRIPT=%~dp0tools\merge_libs.py
where python >nul 2>nul && (python "%SCRIPT%" %* & goto :end)
for %%V in (9.0 8.0) do (
  if exist "C:\Program Files\KiCad\%%V\bin\python.exe" (
    "C:\Program Files\KiCad\%%V\bin\python.exe" "%SCRIPT%" %*
    goto :end
  )
)
echo Python not found - install Python or run tools\merge_libs.py with KiCad's python.exe
:end
pause
