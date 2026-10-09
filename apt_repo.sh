#!/bin/bash
# Build a signed, flat apt repository holding one .deb.
#
#   ./apt_repo.sh <cliss.deb> <output dir>
#
# Signs with the default secret key in the gpg keyring, and publishes its
# public half as cliss.gpg, which users point `signed-by` at. The release
# workflow deploys the output to GitHub Pages; users add it with
#   deb [signed-by=/etc/apt/keyrings/cliss.gpg] https://isurugunarathne.github.io/CLISS ./

set -euo pipefail

DEB="$1"
OUT="$2"

mkdir -p "$OUT"
cp "$DEB" "$OUT/$(dpkg-deb -f "$DEB" Package)_$(dpkg-deb -f "$DEB" Version)_all.deb"
cd "$OUT"

apt-ftparchive packages . > Packages
gzip -9kf Packages
apt-ftparchive \
    -o APT::FTPArchive::Release::Origin=CLISS \
    -o APT::FTPArchive::Release::Label=CLISS \
    -o APT::FTPArchive::Release::Description="CLISS - Command Line Interface Screen Savers" \
    release . > Release

gpg --batch --yes --clearsign -o InRelease Release
gpg --batch --yes --armor --detach-sign -o Release.gpg Release
gpg --batch --yes --export -o cliss.gpg \
    "$(gpg --list-secret-keys --with-colons | awk -F: '/^fpr/ { print $10; exit }')"

echo "apt repository ready in $OUT:"
ls -1
