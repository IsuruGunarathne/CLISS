
# CLISS - Command Line Interface Screen Savers

CLISS is a collection of fun terminal screensavers for Linux. It includes fake system monitors, matrix animations, log streams, and more.

## 📦 Package Contents

- `matrix` - Matrix-style character rain
- `logstream` - Fake server logs
- `loadingbar` - Repeating progress bar animation
- `systemmonitor` - Fake CPU and memory monitor
- `asciiwave` - Wavy ASCII pattern
- `progress` - Simulated build/install progress
- `cliss` - Main launcher script with interactive menu

---

## 🚀 Installation

### 1. Build the package

Run the provided `package.sh` script from the root of the repository:

```bash
chmod +x package.sh
./package.sh
```

This will generate the `CLISS_PACKAGE.deb` file.

### 2. Install the package

```bash
sudo dpkg -i CLISS_PACKAGE.deb
```

If there are missing dependencies, run:

```bash
sudo apt-get install -f
```

### 3. Run the screensavers

Launch the main selector:

```bash
cliss
```

Or run individual ones:

```bash
matrix
logstream
loadingbar
systemmonitor
asciiwave
progress
```

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
        matrix
        logstream
        ...
CLISS_PACKAGE.deb
package.sh
README.md
```

---

## 📬 Maintainer

Created by **Your Name**  
<you@example.com>

Enjoy your terminal screensavers!