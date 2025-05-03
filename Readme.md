
# CLISS - Command Line Interface Screen Savers

CLISS is a collection of fun terminal screensavers for Linux. It includes fake system monitors, matrix animations, log streams, and more — all launched from a single `cliss` command.

## 📦 Package Contents

- `cliss` - Main launcher script (the only globally accessible command)
- Internal Screensavers (only used by `cliss`):
  - `matrix`
  - `logstream`
  - `loadingbar`
  - `systemmonitor`
  - `asciiwave`
  - `progress`

---

## 🚀 Installation

### 🛠 Build and Install with One Command

Use the provided script:

```bash
./clean_install.sh
```

This will:
- Rebuild the `.deb` package from source
- Install it using `dpkg`
- Fix any missing dependencies automatically

---

## 🧪 Manual Build and Install (Alternative)

### 1. Build the package

```bash
chmod +x package.sh
./package.sh
```

### 2. Install the package

```bash
sudo dpkg -i CLISS_PACKAGE.deb
```

If there are missing dependencies:

```bash
sudo apt-get install -f
```

---

## 🎬 Usage

Launch the CLI screensaver menu:

```bash
cliss
```

Select from options like Matrix, LogStream, ASCIIWave, and more.

⚠️ The individual screensaver scripts are not globally executable and should only be used through `cliss`.

---

## ❌ Uninstallation

To remove CLISS:

```bash
sudo dpkg -r cliss
```

To verify it's gone:

```bash
which cliss
```

Should return nothing.

---

## 📁 Repository Structure

```
Animations/
  ASCIIWave.sh
  LoadingBar.sh
  LogStream.sh
  Matrix.sh
  Progress.sh
  SystemMonitor.sh

CLISS_PACKAGE/
  DEBIAN/
    control
  usr/
    local/
      bin/
        cliss
    share/
      cliss/
        matrix
        logstream
        ...

cliss                 <-- launcher script
package.sh
clean_install.sh
README.md
```

---

## 📬 Maintainer

Created by **Your Name**  
<you@example.com>

Enjoy your command-line screensavers!