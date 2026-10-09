#!/bin/bash

set -e

echo "🔨 Rebuilding CLISS package..."
./package.sh

echo "📦 Installing CLISS package..."
sudo apt install -y ./CLISS_PACKAGE.deb

echo "✅ CLISS installed successfully!"
echo "🎬 Run it by typing: cliss"