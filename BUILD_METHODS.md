# Build Methods for GOG Checker

## ⚠️ CRITICAL: Always Use .spec Method

**Other PyInstaller methods consistently fail.** Only use the .spec method for reliable builds.

## 🎯 Recommended Build Process

### 1. Quick Build (Current Version)
```bash
build_spec.bat
```
- Uses existing spec file for current version
- Automatically detects version from `version_info.py`
- Provides clear success/failure feedback

### 2. Manual Spec Build
```bash
python -m PyInstaller --clean GOGChecker-v1.1.2.spec
```
- Direct PyInstaller with specific spec file
- Use `--clean` flag for fresh builds
- Replace version number as needed

## 🔧 Creating New Version Builds

### Step 1: Update Version
```bash
python increment_version.py patch  # or minor/major
```

### Step 2: Update Changelog
Edit `version_info.py` to add new version features

### Step 3: Create Spec File
Copy and rename existing spec file:
```bash
copy GOGChecker-v1.1.2.spec GOGChecker-v1.1.3.spec
```

Update the `name` field in the new spec file:
```python
name='GOGChecker-v1.1.3',
```

### Step 4: Build
```bash
build_spec.bat
```

## 🚫 Methods That Don't Work

These consistently fail and should be avoided:

❌ `python -m PyInstaller --onefile gog_api_gui.py`  
❌ `build_exe.bat` (direct PyInstaller)  
❌ `build_manual.bat` (verbose but still fails)  
❌ Any build method without a .spec file  

## 📁 Build Outputs

Successful builds create:
- `dist/GOGChecker-v[VERSION].exe` (40MB)
- Updated `build_info.json`
- Release notes in `RELEASE_NOTES_v[VERSION].md`

## 🔍 Troubleshooting

If build fails:
1. ✅ Ensure spec file exists and is correctly named
2. ✅ Check that version_info.py has correct version
3. ✅ Try manual spec build command
4. ✅ Check for any syntax errors in gog_api_gui.py

**Remember: The .spec method is the only reliable way to build this application!** 