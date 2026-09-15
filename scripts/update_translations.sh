#!/bin/bash
cd "$(dirname "$0")/.."

mkdir -p locales

# pyside6-lupdate does not recurse into directories for Python sources: passing
# `src` yields zero strings. The .py files must be listed explicitly or every
# self.tr() string in the code is silently absent from the catalogs.
PY_FILES=$(find src -name '*.py' | sort)
SOURCES="pygui $PY_FILES main.py"

echo "Extracting strings to .ts files..."
pyside6-lupdate $SOURCES -ts locales/en_US.ts
pyside6-lupdate $SOURCES -ts locales/ar_SA.ts
pyside6-lupdate $SOURCES -ts locales/fr_FR.ts
pyside6-lupdate $SOURCES -ts locales/es_ES.ts

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
