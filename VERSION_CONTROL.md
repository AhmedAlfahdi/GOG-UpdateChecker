# Version Control System

## Overview

The GOG Checker uses semantic versioning (MAJOR.MINOR.PATCH) with automated build scripts.

## Files

- `version_info.py` - Contains version numbers and changelog
- `build_versioned.py` - Automated build script with version control
- `increment_version.py` - Helper to increment version numbers
- `build_version.bat` - Windows batch file to run the build

## Version Scheme

**MAJOR.MINOR.PATCH** (e.g., 1.0.0)

- **MAJOR**: Breaking changes or major rewrites
- **MINOR**: New features that are backward compatible
- **PATCH**: Bug fixes and small improvements

## Usage

### Building Current Version

**⚠️ IMPORTANT: Always use the .spec method for builds as other methods consistently fail!**

**Recommended Method - Spec Build:**
```bash
build_spec.bat
```

**Manual Spec Build:**
```bash
python -m PyInstaller --clean GOGChecker-v[VERSION].spec
```

**Legacy Build (Creates spec file):**
```bash
python build_versioned.py
```

Or use the batch file:
```bash
build_version.bat
```

**Note:** Direct PyInstaller commands without .spec files are unreliable and should be avoided.

### Incrementing Versions

```bash
# Bug fixes (1.0.0 -> 1.0.1)
python increment_version.py patch

# New features (1.0.0 -> 1.1.0)
python increment_version.py minor

# Breaking changes (1.0.0 -> 2.0.0)
python increment_version.py major
```

### Workflow

1. **Make code changes**
2. **Increment version**: `python increment_version.py <type>`
3. **Update changelog** in `version_info.py`
4. **Build**: `python build_versioned.py`
5. **Release**: Use the generated exe and release notes

## Generated Files

Each build creates:
- `dist/GOGChecker-v{VERSION}.exe` - The executable
- `GOGChecker-v{VERSION}.spec` - PyInstaller spec file
- `build_info.json` - Build metadata
- `RELEASE_NOTES_v{VERSION}.md` - Release documentation

## Current Version

- **Version**: 1.2.0
- **Build Name**: GOGChecker-v1.2.0
- **Features**: Deep Scan mode, readable version column, enhanced game detection

## Version History

### v1.2.0 (2025-01-02)
- 🔍 **Deep Scan Mode**: Optional comprehensive directory scanning across all drives
- 📋 **Readable Version Column**: Added separate column for user-friendly version numbers (1.2.3)
- 🚀 **Enhanced Game Detection**: Finds games in custom/non-standard installation locations
- 🔧 **Fixed PowerShell Windows**: Eliminated random console windows during scanning
- 💾 **Better Performance**: Smart caching and optimized directory traversal
- 🎨 **Improved UI**: Two-row layout with better organization of scan options
- ⚠️ **User Warnings**: Clear notifications about Deep Scan time requirements

### v1.0.0 (2025-01-02)
- ✅ Separated Tags and Wiki into different columns
- ✅ Auto-sized columns to fit content
- ✅ Added horizontal scroll bar
- ✅ Moved Wiki column to last position
- ✅ Smart DLC detection (wiki only for main games)
- ✅ PCGamingWiki integration with 📚 icon
- ✅ Improved UI layout and user experience 