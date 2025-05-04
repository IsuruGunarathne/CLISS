#!/bin/bash

set -e

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
ANIMATIONS=()
for file in Animations/*.sh; do
    name=$(basename "$file" .sh)
    cp "$file" "CLISS_PACKAGE/usr/share/cliss/$name"
    chmod +x "CLISS_PACKAGE/usr/share/cliss/$name"
    ANIMATIONS+=("$name")
done

ANIM_COUNT=${#ANIMATIONS[@]}

echo "🎛 Generating cliss launcher..."
cat > CLISS_PACKAGE/usr/local/bin/cliss <<EOF
#!/bin/bash

BASE="/usr/share/cliss"
echo "Welcome to CLISS - Command Line Interface Screen Savers"
echo "--------------------------------------------------------"

options=(${ANIMATIONS[@]} "Quit")

select opt in "\${options[@]}"
do
    case \$opt in
EOF

for name in "${ANIMATIONS[@]}"; do
    echo "        $name) exec \"\$BASE/$name\" ;;" >> CLISS_PACKAGE/usr/local/bin/cliss
done

cat >> CLISS_PACKAGE/usr/local/bin/cliss <<EOF
        Quit) exit ;;
        *) echo "Invalid option. Please choose again." ;;
    esac
done
EOF

chmod +x CLISS_PACKAGE/usr/local/bin/cliss

echo "📝 Creating control file..."
cat > CLISS_PACKAGE/DEBIAN/control <<EOF
Package: cliss
Version: 1.0
Section: utils
Priority: optional
Architecture: all
Depends: bash
Maintainer: Your Name <you@example.com>
Description: CLISS - Command Line Interface Screen Savers
 A fun collection of $ANIM_COUNT terminal screensavers with animations and fake system activity.
EOF

echo "📦 Building .deb package..."
dpkg-deb --build CLISS_PACKAGE

echo "✅ Done: CLISS_PACKAGE.deb created"
