#!/bin/bash
# Script to compile Tailscale Client Pro and build a macOS DMG Installer

APP_NAME="Tailscale VPN Client Pro"
APP_BUNDLE="TailscaleClientPro.app"
DMG_NAME="TailscaleClientPro_Setup.dmg"

echo "=== Starting macOS Build Process ==="

# 1. Clean previous builds
echo "Cleaning up old build/dist files..."
rm -rf build/ dist/*.app dist/*.dmg

# 2. Run PyInstaller
echo "Compiling application with PyInstaller..."
pyinstaller TailscaleClient_Mac.spec

if [ $? -ne 0 ]; then
    echo "ERROR: PyInstaller compilation failed!"
    exit 1
fi

if [ ! -d "dist/$APP_BUNDLE" ]; then
    echo "ERROR: App bundle 'dist/$APP_BUNDLE' was not created!"
    exit 1
fi

echo "Compilation successful! App bundle created at dist/$APP_BUNDLE"

# 3. Create DMG Installer with Applications Shortcut
echo "Packaging App bundle into a .dmg installer with Applications shortcut..."
rm -f "dist/$DMG_NAME"

# Create a temporary directory for DMG contents
DMG_TEMP="build/dmg_temp"
mkdir -p "$DMG_TEMP"

# Copy the app bundle to the temp directory
cp -R "dist/$APP_BUNDLE" "$DMG_TEMP/"

# Create a symbolic link to /Applications for standard drag-and-drop installation
ln -s /Applications "$DMG_TEMP/Applications"

# Generate the compressed DMG
hdiutil create -volname "$APP_NAME" -srcfolder "$DMG_TEMP" -ov -format UDZO "dist/$DMG_NAME"

if [ $? -eq 0 ]; then
    echo "=== SUCCESS! macOS DMG Installer created at dist/$DMG_NAME ==="
else
    echo "ERROR: DMG creation failed!"
    exit 1
fi

# Clean up temporary files
rm -rf "$DMG_TEMP"
