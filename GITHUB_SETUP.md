# GitHub Update Checker Setup Guide

## Overview

The GOG Update Checker now includes an automatic update checker that can detect new releases from your GitHub repository. This guide explains how to set it up.

## Setup Steps

### 1. Update Repository Information

First, edit the `GITHUB_REPO` variable in `gog_api_gui.py`:

```python
# Replace this line:
GITHUB_REPO = "YOUR_USERNAME/GOG-UpdateChecker"

# With your actual GitHub username and repository name:
GITHUB_REPO = "yourusername/GOG-UpdateChecker"
```

### 2. Create GitHub Releases

When you want to release a new version:

1. **Update the version** in `gog_api_gui.py`:
   ```python
   APP_VERSION = "1.1.5"  # Increment this for new releases
   ```

2. **Create a Git tag** for the release:
   ```bash
   git tag v1.1.5
   git push origin v1.1.5
   ```

3. **Create a GitHub Release**:
   - Go to your repository on GitHub
   - Click "Releases" → "Create a new release"
   - Tag version: `v1.1.5` (must match the tag you created)
   - Release title: `v1.1.5` or `GOG Update Checker v1.1.5`
   - Description: Add release notes (what's new, what's fixed, etc.)
   - Attach binary files if you have compiled versions
   - Click "Publish release"

### 3. Release Notes Format

The update checker will display your release notes. Use this format for best results:

```markdown
## What's New
- ✨ Added automatic update checking
- 🔧 Improved GOG game detection
- 🐛 Fixed DLC build ID handling

## Bug Fixes
- Fixed crash when scanning certain game directories
- Improved error handling for API failures

## Technical Changes
- Updated to Qt6 for better performance
- Added GitHub API integration
```

## How It Works

### Version Comparison
The update checker compares version numbers intelligently:
- `1.1.5` vs `1.1.4` → Update available
- `1.2.0` vs `1.1.9` → Update available
- `2.0.0` vs `1.9.9` → Update available

### Update Process
1. App checks GitHub API on startup (if enabled)
2. Compares current version with latest release tag
3. Shows update dialog if newer version found
4. Opens browser to GitHub release page for download

### User Settings
Users can control update checking via the Help menu:
- ✅ **Check for Updates** - Manual update check
- ✅ **Auto-check Updates on Startup** - Toggle automatic checking

## API Rate Limits

GitHub API allows 60 requests per hour for unauthenticated requests, which is more than enough for update checking.

## Example Workflow

1. **Development**: Work on new features
2. **Testing**: Test the application thoroughly
3. **Version Bump**: Update `APP_VERSION` in code
4. **Commit & Push**: `git commit -am "Release v1.1.5" && git push`
5. **Tag**: `git tag v1.1.5 && git push origin v1.1.5`
6. **GitHub Release**: Create release on GitHub with tag `v1.1.5`
7. **Users Notified**: Users will see update notification on next startup

## Repository Structure

Your repository should have:
```
GOG-UpdateChecker/
├── gog_api_gui.py          # Main application
├── requirements.txt        # Dependencies
├── README.md              # Project documentation
├── icon.ico               # Application icon
└── releases/              # Optional: store release binaries
    ├── v1.1.4/
    │   └── gog-checker.exe
    └── v1.1.5/
        └── gog-checker.exe
```

## Troubleshooting

### No Updates Detected
- Check that `GITHUB_REPO` is correct
- Verify the release tag matches the version pattern (e.g., `v1.1.5`)
- Ensure the release is published (not draft)

### Network Issues
- The app handles network failures gracefully
- Users won't see errors for silent startup checks
- Manual checks will show error dialogs

### Version Parsing
- Use semantic versioning: `MAJOR.MINOR.PATCH`
- Tags should start with `v`: `v1.1.5`
- Version in code should not have `v`: `1.1.5`

## Security Notes

- The update checker only reads public release information
- No authentication tokens required
- Opens system browser for downloads (secure)
- Does not automatically download or install updates 