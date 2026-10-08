# KiCad_Libs_ToAdd

Inbox for new components that are not yet in the official library
([L2-Hardware/Kicad_Libs](https://github.com/L2-Hardware/Kicad_Libs)).

Same layout as the official library:

```
<eLib>/
    datasheet/
    <eLib>.3dshapes/
    <eLib>.pretty/
    <eLib>.kicad_sym      only the new symbols
    .gitignore
```

Workflow:
1. `bring_libs.bat` (once): junction `KiCad_Libs` -> `C:\git\PCB\Kicad_Libs`
2. `merge_libs.bat --clean`: merges everything here into the official library and empties this folder
3. Open the touched libraries in the Symbol Editor, save, then commit + push in the `Kicad_Libs` repo
4. Commit the (now empty) `KiCad_Libs_ToAdd` here

Usually this folder is empty (only this README).
