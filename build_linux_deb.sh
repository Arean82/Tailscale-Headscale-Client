#!/bin/bash
# Script to create a .deb package for Tailscale Client Pro with lifecycle management

APP_NAME="tailscale-client-pro"
VERSION="1.0.0"
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

# 5. Copy files
cp -r dist/TailscaleClientPro/* build/deb/opt/$APP_NAME/

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
