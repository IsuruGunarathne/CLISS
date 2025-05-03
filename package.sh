#!/bin/bash

set -e

echo "🧹 Cleaning old package..."
rm -rf CLISS_PACKAGE/usr/local/bin/*
rm -f CLISS_PACKAGE.deb

echo "📂 Copying screensaver scripts..."
cp Animations/Matrix.sh CLISS_PACKAGE/usr/local/bin/matrix
cp Animations/LogStream.sh CLISS_PACKAGE/usr/local/bin/logstream
cp Animations/LoadingBar.sh CLISS_PACKAGE/usr/local/bin/loadingbar
cp Animations/SystemMonitor.sh CLISS_PACKAGE/usr/local/bin/systemmonitor
cp Animations/ASCIIWave.sh CLISS_PACKAGE/usr/local/bin/asciiwave
cp Animations/Progress.sh CLISS_PACKAGE/usr/local/bin/progress

echo "🔧 Setting executable permissions..."
chmod +x CLISS_PACKAGE/usr/local/bin/*

echo "📦 Building .deb package..."
dpkg-deb --build CLISS_PACKAGE

echo "✅ Package built: CLISS_PACKAGE.deb"
