If you want a local copy of Kicad Libraries for each board project, inside the KiCad directory run:

git submodule add https://data.elios-tech.com:3000/enrico.rossi/KiCad_Libs.git
git commit -m "Added Kicad Libs submodule"
git push

If you don't want a local copy of the libraries for each project but you are ok with having a single local copy of it in a different folder and want to link to it from the board project folder, just run the "bring_libs.bat".
This will create a junction link.