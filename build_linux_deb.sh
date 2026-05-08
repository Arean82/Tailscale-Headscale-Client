#!/bin/bash
# Script to create a .deb package for Tailscale Client Pro with lifecycle management

APP_NAME="tailscale-client-pro"
VERSION="5.0.0"
MAINTAINER="Arean82 <arean82@example.com>"

# 1. Create directory structure
mkdir -p build/deb/DEBIAN
mkdir -p build/deb/usr/bin
mkdir -p build/deb/usr/share/applications
mkdir -p build/deb/opt/$APP_NAME

# 2. Create Control File
cat <<EOF > build/deb/DEBIAN/control
Package: $APP_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: amd64
Maintainer: $MAINTAINER
Description: Professional GUI client for Tailscale and Headscale.
EOF

# 3. Create Post-Install Script (Registering paths and icons)
cat <<EOF > build/deb/DEBIAN/postinst
#!/bin/bash
ln -sf /opt/$APP_NAME/TailscaleClientPro /usr/bin/$APP_NAME
chmod +x /usr/bin/$APP_NAME
update-desktop-database /usr/share/applications
echo "Tailscale Client Pro installed successfully."
EOF
chmod 755 build/deb/DEBIAN/postinst

# 4. Create Post-Remove Script (Cleanup)
cat <<EOF > build/deb/DEBIAN/postrm
#!/bin/bash
rm -f /usr/bin/$APP_NAME
update-desktop-database /usr/share/applications
echo "Tailscale Client Pro removed cleanly."
EOF
chmod 755 build/deb/DEBIAN/postrm

# 5. Copy files (Supports both OneDir and OneFile builds dynamically, prompting if both exist)
HAS_ONEDIR=0
HAS_ONEFILE=0

if [ -d "dist/TailscaleClientPro_OneDir" ]; then
    HAS_ONEDIR=1
fi
if [ -f "dist/Tailscale VPN Client Pro" ]; then
    HAS_ONEFILE=1
fi

CHOICE=""
if [ $HAS_ONEDIR -eq 1 ] && [ $HAS_ONEFILE -eq 1 ]; then
    echo "Both OneDir and OneFile builds were detected in dist/."
    echo "Which build would you like to package into the .deb?"
    echo "  1) OneFile (Single standalone executable)"
    echo "  2) OneDir  (Full unpacked directory)"
    read -p "Enter choice [1 or 2]: " CHOICE
    while [[ "$CHOICE" != "1" && "$CHOICE" != "2" ]]; do
        read -p "Invalid choice. Please enter 1 or 2: " CHOICE
    done
elif [ $HAS_ONEDIR -eq 1 ]; then
    CHOICE="2"
elif [ $HAS_ONEFILE -eq 1 ]; then
    CHOICE="1"
else
    echo "ERROR: No compiled builds found in dist/."
    echo "Please build with PyInstaller first using one of these commands:"
    echo "  pyinstaller TailscaleClient_OneFile.spec"
    echo "  pyinstaller TailscaleClient_OneDir.spec"
    exit 1
fi

if [ "$CHOICE" = "1" ]; then
    echo "Packaging OneFile build..."
    cp "dist/Tailscale VPN Client Pro" build/deb/opt/$APP_NAME/TailscaleClientPro
    chmod +x build/deb/opt/$APP_NAME/TailscaleClientPro
    # Copy assets so the desktop launcher can still find the icon file
    if [ -d "assets" ]; then
        cp -r assets build/deb/opt/$APP_NAME/
    fi
else
    echo "Packaging OneDir build..."
    cp -r dist/TailscaleClientPro_OneDir/* build/deb/opt/$APP_NAME/
    # Rename the inner executable to TailscaleClientPro so launcher & symlink find it perfectly
    if [ -f "build/deb/opt/$APP_NAME/Tailscale VPN Client Pro" ]; then
        mv "build/deb/opt/$APP_NAME/Tailscale VPN Client Pro" "build/deb/opt/$APP_NAME/TailscaleClientPro"
    fi
fi

# 6. Create Desktop Entry
cat <<EOF > build/deb/usr/share/applications/$APP_NAME.desktop
[Desktop Entry]
Name=Tailscale Client Pro
Comment=Manage your VPN connections
Exec=$APP_NAME
Icon=/opt/$APP_NAME/assets/icon.png
Terminal=false
Type=Application
Categories=Network;VPN;
EOF

# 7. Build the package
dpkg-deb --build build/deb dist/${APP_NAME}_${VERSION}_amd64.deb

echo "Professional .deb package created in dist/"
