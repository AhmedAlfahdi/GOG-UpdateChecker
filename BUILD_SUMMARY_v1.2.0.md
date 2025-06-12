# Build Summary - GOG Checker v1.2.0

## ✅ **Build Successful!**

**Build Date:** January 2, 2025  
**Build Time:** ~1 minute 30 seconds  
**Executable:** `GOGChecker-v1.2.0-DeepScan.exe`  
**Size:** 41.5 MB (compressed with UPX)

---

## 🔧 **Fixes Applied**

### ✅ **PowerShell Window Issue - RESOLVED**
- **Problem:** Random PowerShell windows appearing during scanning
- **Solution:** Added `creationflags=subprocess.CREATE_NO_WINDOW` to all subprocess calls
- **Files Fixed:** 
  - Version detection subprocess call (line ~1040)
  - GOG Galaxy launcher subprocess call (line ~3236)
- **Result:** Silent background operations, no more flickering windows

---

## 🚀 **Key Features in v1.2.0**

1. **🔍 Deep Scan Mode** - Comprehensive multi-drive scanning
2. **📋 Readable Version Column** - User-friendly version display (1.2.3)  
3. **🔧 No PowerShell Windows** - Silent background operations
4. **🎨 Improved UI Layout** - Two-row button organization
5. **⚡ Better Performance** - Smart caching and optimization

---

## 📁 **Files Created**

```
✅ GOGChecker-v1.2.0-DeepScan.exe      (41.5 MB) - Main executable
✅ GOGChecker-v1.2.0-DeepScan.spec     - PyInstaller spec file
✅ build_v1.2.0.bat                    - Build script
✅ RELEASE_NOTES_v1.2.0.md             - Detailed release notes
✅ VERSION_CONTROL.md                  - Updated version history
```

---

## 🎯 **Release Summary**

**v1.2.0 "Deep Scan Edition"** adds comprehensive game detection across all drives while fixing the annoying PowerShell window issue. Users can now choose between Quick Scan (fast) or Deep Scan (thorough) modes, with clear warnings about scan times. The new readable version column makes it easier to understand game versions without cryptic build IDs.

**Ready for distribution! 🎮** 