#!/bin/bash
cd "$(dirname "$0")/.."

mkdir -p locales

echo "Extracting strings to .ts files..."
pyside6-lupdate pygui src -ts locales/en_US.ts
pyside6-lupdate pygui src -ts locales/ar_SA.ts
pyside6-lupdate pygui src -ts locales/fr_FR.ts
pyside6-lupdate pygui src -ts locales/es_ES.ts

echo ""
echo "Running Auto-Translation AI..."
python3 scripts/auto_translate.py

echo ""
echo "Cleaning up protected CSS strings..."
python3 scripts/cleanup_css.py

echo ""
echo "Translating Readme Documentation..."
python3 scripts/translate_readme.py

echo ""
echo "Compiling .ts files to .qm files..."
pyside6-lrelease locales/en_US.ts locales/ar_SA.ts locales/fr_FR.ts locales/es_ES.ts

echo "Done!"
