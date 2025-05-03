#!/bin/bash

set -e

echo "🧹 Cleaning previous build..."
rm -rf CLISS_PACKAGE/usr/local/bin/*
rm -rf CLISS_PACKAGE/usr/share/cliss/*
rm -f CLISS_PACKAGE.deb

echo "📂 Creating required directories..."
mkdir -p CLISS_PACKAGE/usr/local/bin
mkdir -p CLISS_PACKAGE/usr/share/cliss

echo "📥 Copying screensaver scripts to /usr/share/cliss/"
cp Animations/Matrix.sh CLISS_PACKAGE/usr/share/cliss/matrix
cp Animations/LogStream.sh CLISS_PACKAGE/usr/share/cliss/logstream
cp Animations/LoadingBar.sh CLISS_PACKAGE/usr/share/cliss/loadingbar
cp Animations/SystemMonitor.sh CLISS_PACKAGE/usr/share/cliss/systemmonitor
cp Animations/ASCIIWave.sh CLISS_PACKAGE/usr/share/cliss/asciiwave
cp Animations/Progress.sh CLISS_PACKAGE/usr/share/cliss/progress

echo "🎛 Copying cliss launcher script from root directory..."
cp cliss CLISS_PACKAGE/usr/local/bin/cliss

echo "🔧 Setting executable permissions..."
chmod +x CLISS_PACKAGE/usr/share/cliss/*
chmod +x CLISS_PACKAGE/usr/local/bin/cliss

echo "📦 Building .deb package..."
dpkg-deb --build CLISS_PACKAGE

echo "✅ Done: CLISS_PACKAGE.deb created"
