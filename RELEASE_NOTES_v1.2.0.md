# GOG Games Build ID Checker v1.2.0 - "Deep Scan Edition"

**Release Date:** January 2, 2025  
**Build Name:** GOGChecker-v1.2.0-DeepScan.exe

## 🎯 **Quick Summary**

Major update adding **Deep Scan mode** for comprehensive game detection across all drives, **readable version display**, and **eliminated random PowerShell windows** during scanning.

---

## 🚀 **New Features**

### 🔍 **Deep Scan Mode**
- **Optional comprehensive scanning** across all available drive letters (A-Z)
- **Finds games in custom locations** that Quick Scan misses
- **Smart directory patterns** covering 50+ potential installation paths
- **User warning system** clearly explains longer scan times
- **Real-time progress updates** showing which directories are being scanned

### 📋 **Readable Version Column**
- **New "Installed Version" column** displays user-friendly version numbers (1.2.3)
- **Separate from Build IDs** - no longer shows cryptic numeric strings as versions
- **Smart version detection** from GOG metadata and executable properties
- **Better user experience** with meaningful version information

---

## 🔧 **Bug Fixes**

### 🚪 **Eliminated PowerShell Windows**
- **Fixed random console windows** appearing during version detection
- **Added `CREATE_NO_WINDOW` flags** to all subprocess calls
- **Silent background operations** - no more flickering windows
- **Professional user experience** with clean, non-intrusive scanning

---

## 🎨 **UI Improvements**

### 📐 **Better Layout Organization**
- **Two-row button layout** for cleaner appearance
- **Dedicated scan options row** with Deep Scan checkbox
- **Less crowded interface** with logical grouping
- **Improved visual hierarchy** and better spacing

---

## 💾 **Performance Enhancements**

### ⚡ **Smart Caching & Optimization**
- **Intelligent caching** prevents re-scanning same directories
- **Optimized file reading** with partial content loading
- **Faster Quick Scan** (5-10 seconds for standard installations)
- **Efficient deep scanning** with progress feedback

---

## 📊 **Technical Details**

### 🔍 **Deep Scan Coverage**
- **All drive letters** (C:, D:, E:, F:, etc.)
- **Standard game directories** (Program Files, Games, GOG Games)
- **User-specific paths** (Documents, Desktop, AppData)
- **Third-party locations** (Steam common, Epic Games)
- **Custom patterns** for non-standard installations

### 🏗️ **Build Information**
- **Version:** 1.2.0
- **Build Target:** Windows 10/11
- **Dependencies:** PySide6, Qt6
- **Size:** ~35MB standalone executable
- **No PowerShell windows:** ✅ Fixed

---

## 📋 **Usage Instructions**

1. **Quick Scan (Default):** Uncheck Deep Scan for fast scanning of common directories
2. **Deep Scan:** Check the Deep Scan option before clicking "Scan Games" for comprehensive searching
3. **Be Patient:** Deep Scan may take 2-5 minutes depending on number of drives and games
4. **Watch Progress:** Monitor the progress bar and log for real-time scanning updates

---

## ⚠️ **Important Notes**

- **Deep Scan Warning:** Shows confirmation dialog explaining longer scan times
- **Memory Usage:** Deep Scan uses more memory but releases it after completion
- **Network Required:** Update checking still requires internet connection
- **Windows Only:** Current build is Windows-specific

---

## 🔄 **Upgrade Path**

- **From v1.1.x:** Direct upgrade - all settings preserved
- **New Installation:** Download and run - no installation required
- **Portable:** Single executable, no registry changes

---

## 🐛 **Known Issues**

- Deep Scan may take several minutes on systems with many drives
- Some antivirus software may flag the executable (false positive)
- Requires Windows 10 or newer for optimal performance

---

**Happy Gaming! 🎮** 