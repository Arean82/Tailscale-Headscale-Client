@echo off
cd /d "%~dp0\.."

if not exist "locales" mkdir locales

echo Extracting strings to .ts files...
pyside6-lupdate pygui src -ts locales/en_US.ts
pyside6-lupdate pygui src -ts locales/ar_SA.ts
pyside6-lupdate pygui src -ts locales/fr_FR.ts
pyside6-lupdate pygui src -ts locales/es_ES.ts
echo.

echo Running Auto-Translation AI...
python scripts\auto_translate.py
echo.

echo Cleaning up protected CSS strings...
python scripts\cleanup_css.py
echo.

echo Translating Readme Documentation...
python scripts\translate_readme.py
echo.

echo Compiling .ts files to .qm files...
pyside6-lrelease locales/en_US.ts locales/ar_SA.ts locales/fr_FR.ts locales/es_ES.ts
echo Done!
pause
