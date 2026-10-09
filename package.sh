#!/bin/bash

set -e

# Package version: CLISS_VERSION if set, otherwise the latest git tag (v1.2 -> 1.2)
VERSION="${CLISS_VERSION:-$(git describe --tags --abbrev=0 2>/dev/null || true)}"
VERSION="${VERSION#v}"
VERSION="${VERSION:-0.0}"
[[ "$VERSION" == *.* ]] || VERSION="$VERSION.0"

echo "🧹 Cleaning previous build..."
rm -rf CLISS_PACKAGE/usr/local/bin/*
rm -rf CLISS_PACKAGE/usr/share/cliss/*
rm -rf CLISS_PACKAGE/DEBIAN
rm -f CLISS_PACKAGE.deb

echo "📂 Creating required directories..."
mkdir -p CLISS_PACKAGE/usr/local/bin
mkdir -p CLISS_PACKAGE/usr/share/cliss
mkdir -p CLISS_PACKAGE/DEBIAN

echo "📥 Copying animations from Animations/"
ANIM_COUNT=0
for file in Animations/*.sh Animations/*.py; do
    [[ -f "$file" ]] || continue
    name=$(basename "$file")
    name="${name%.*}"
    cp "$file" "CLISS_PACKAGE/usr/share/cliss/$name"
    chmod +x "CLISS_PACKAGE/usr/share/cliss/$name"
    ANIM_COUNT=$((ANIM_COUNT + 1))
done

echo "🧰 Copying the shared rendering engine"
mkdir -p CLISS_PACKAGE/usr/share/cliss/lib
cp Animations/lib/*.py CLISS_PACKAGE/usr/share/cliss/lib/

echo "🎛 Installing cliss launcher..."
cp cliss CLISS_PACKAGE/usr/local/bin/cliss
chmod +x CLISS_PACKAGE/usr/local/bin/cliss

echo "📝 Creating control file..."
cat > CLISS_PACKAGE/DEBIAN/control <<EOF
Package: cliss
Version: $VERSION
Section: utils
Priority: optional
Architecture: all
Depends: bash, python3 (>= 3.6), coreutils
Maintainer: Isuru Gunarathne <isuru623@gmail.com>
Description: CLISS - Command Line Interface Screen Savers
 A collection of $ANIM_COUNT animated terminal screensavers: matrix rain, fire,
 plasma, starfield, fireworks, an aquarium, pipes and more.
EOF

echo "📦 Building .deb package..."
dpkg-deb --build CLISS_PACKAGE

echo "✅ Done: CLISS_PACKAGE.deb (version $VERSION) created"
