#!/bin/bash

set -e

echo "🔨 Rebuilding CLISS package..."
./package.sh

echo "📦 Installing CLISS package..."
sudo dpkg -i CLISS_PACKAGE.deb

echo "🔍 Checking and fixing any missing dependencies..."
sudo apt-get install -f -y

echo "✅ CLISS installed successfully!"
echo "🎬 Run it by typing: cliss"