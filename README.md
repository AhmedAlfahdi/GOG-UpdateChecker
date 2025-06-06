# GOG Games Build ID Checker

A modern Qt6 GUI application to detect installed GOG games on your PC and check them for updates using build IDs from the gog-games.to API.

## Features

### Main Build ID Checker
- **Installed Game Detection**: Automatically scans your PC for installed GOG games
- **Build ID Comparison**: Compares installed build IDs with latest available build IDs  
- **Intelligent Version Detection**: Prioritizes build IDs over version strings for accurate comparison
- **Update Status Display**: Shows which games are up-to-date or need updates based on build ID comparison
- **Changelog Viewing**: Display changelogs for game updates when available
- **GOG Galaxy Integration**: Detects GOG Galaxy installation and games
- **Registry Scanning**: Scans Windows registry for comprehensive game detection
- **Directory Scanning**: Searches common GOG installation directories
- **Modern Interface**: Beautiful Qt6 dark theme with responsive design
- **Real-time Logging**: Detailed scan logs and operation status
- **Game Statistics**: Shows total games, up-to-date count, and updates available
- **Clickable Links**: Clickable changelog URLs and status links to game pages
- **Font Size Controls**: Adjustable interface font sizes with keyboard shortcuts
- **Clickable Install Paths**: Click game paths to open installation folders

### API Explorer (Advanced)
- **Endpoint Discovery**: Automatically discover API endpoints
- **Manual Testing**: Test any endpoint with custom parameters
- **Response Analysis**: Analyze and understand API response structures
- **Multi-Method Support**: Test both GET and POST requests
- **JSON Structure Analysis**: Automatically parse and analyze JSON responses

### General
- **Cross-platform**: Designed for Windows with GOG support
- **Comprehensive Testing**: Built-in test suite for validation

### How Build ID Comparison Works
- **Build ID Priority**: The application first looks for build IDs in GOG metadata files (e.g., "buildId": "58465618714994950")
- **Fallback System**: If no build ID is found, falls back to GOG ID or version strings
- **Numeric Comparison**: For build IDs, performs intelligent numeric comparison to determine if an update is available
- **Accurate Updates**: Build IDs provide more precise update detection than version strings

## Prerequisites

- Python 3.7 or higher
- Windows OS (for GOG game detection features)
- Internet connection
- pip (Python package manager)

## Installation

1. **Clone or download this repository**
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Quick Start

- **Windows**: Double-click `run_gui.bat`
- **All Platforms**: Run `python launcher.py`

### Direct Launch

Run: `python gog_api_gui.py`

## Interface Features

### Modern Qt6 Design
- **Beautiful Interface**: Modern Qt6 interface with dark theme and native look
- **Better Performance**: Responsive UI with proper threading
- **Enhanced Styling**: Rich styling with gradients, shadows, and animations
- **Improved Layout**: Well-organized with splitters and resizable panels
- **Color Coding**: Visual status indicators with color-coded game entries
- **Professional Look**: Polished and professional appearance
- **Font Controls**: Menu-based font size controls with keyboard shortcuts (Ctrl+/-, Ctrl+0)
- **Clickable Elements**: Clickable status links and install paths for better interaction

## How It Works

### Game Detection Process

1. **GOG Galaxy Detection**
   - Searches for GOG Galaxy installation in common directories
   - Checks Windows registry for Galaxy client paths
   - Parses Galaxy configuration if available

2. **Registry Scanning**  
   - Scans `HKEY_LOCAL_MACHINE\SOFTWARE\GOG.com\Games`
   - Extracts game names, versions, installation paths
   - Retrieves executable information and game metadata

3. **Directory Scanning**
   - Searches common installation paths:
     - `%ProgramFiles(x86)%\GOG Games`
     - `%ProgramFiles%\GOG Games` 
     - `C:\GOG Games`, `D:\GOG Games`, etc.
   - Analyzes game directories for version information
   - Identifies game executables and validates installations

### Version Checking Process

1. **Installed Build ID Detection**
   - Extracts build IDs from GOG metadata files (.info files)
   - Prioritizes buildId field from JSON metadata
   - Falls back to version strings or GOG IDs if no build ID available
   - Analyzes executable metadata when needed

2. **Latest Build ID Retrieval**
   - Queries gog-games.to API for latest build ID information
   - Handles multiple API endpoint formats
   - Retrieves changelog information when available
   - Prioritizes build IDs over version strings in API responses

3. **Build ID Comparison**
   - Intelligent numeric comparison for build IDs (e.g., 58465618714994950 vs 58465618714994951)
   - Determines if installed build is older, newer, or same as latest
   - Falls back to string comparison for non-build ID versions
   - Displays precise update status based on comparison results

## Application Interface

### Main Components

1. **Status Bar**: Shows API connection status and control buttons
2. **Installed Games Table**: Displays detected games with version information
3. **Scan Log Tab**: Real-time logging of scan operations and results  
4. **Changelog Tab**: Shows update changelogs for selected games
5. **Statistics Bar**: Displays total games, update counts, and quick actions

### Column Information

- **Game Name**: Detected name of the installed game
- **Installed Version**: Currently installed version on your system
- **Latest Version**: Latest available version from API
- **Update Status**: "Up to Date", "Update Available", or "Cannot Check"
- **Size**: Installation size of the game
- **Path**: Installation directory path

### How to Use

1. **Scan Games**: Click "Scan Games" to detect installed GOG games
2. **Check Updates**: Click "Check Updates" to compare with latest versions
3. **View Details**: Double-click any game to see detailed information and changelog
4. **Open Galaxy**: Click "Open GOG Galaxy" to launch the GOG client
5. **Monitor Logs**: Watch the scan log tab for detailed operation information

## API Integration

The application attempts to connect to various possible endpoints:
- `https://gog-games.to/api/games/search`
- `https://gog-games.to/api/search`
- `https://gog-games.to/api/changelog`

The app includes version checking and changelog retrieval functionality.

## Features in Detail

### Game Detection
- Multi-method scanning for comprehensive game discovery
- Handles various GOG installation configurations
- Extracts detailed metadata including versions and sizes
- Identifies game executables and validates installations

### Version Management  
- Semantic version comparison with intelligent parsing
- Handles edge cases in version formats
- Clear status indicators for update requirements
- Batch processing of multiple games

### User Interface
- Modern tabbed interface with organized information
- Real-time status updates and progress indication
- Detailed logging with timestamps
- Intuitive controls and clear visual feedback

## Configuration

The application uses these default settings:
- **Timeout**: 10 seconds for API requests
- **User Agent**: 'GOG-API-GUI/1.0'  
- **Theme**: Dark theme with blue accents
- **Scan Methods**: Registry + Directory + Galaxy detection

## Troubleshooting

### Common Issues

1. **No Games Detected**
   - Ensure GOG Galaxy is installed or games are in standard directories
   - Check that games were installed through GOG (not other sources)
   - Run as administrator if registry access is limited

2. **Version Information Missing**
   - Some games may not store version information accessibly
   - Manual version files may be missing or in non-standard formats
   - Try scanning again after running games at least once

3. **API Connection Failed**
   - Check your internet connection
   - Verify gog-games.to is accessible
   - Check firewall settings

4. **Application Won't Start**
   - Ensure Python 3.7+ is installed
   - Install required packages: `pip install -r requirements.txt`
   - Check Python path in system variables

### Debug Information

The application provides detailed logging in the "Scan Log" tab. This includes:
- Game detection progress and results
- API request information
- Version comparison details  
- Error messages with timestamps

## Technical Details

### Architecture
- **Frontend**: tkinter with ttk styling and modern tabbed interface
- **Game Scanner**: Multi-method detection system for Windows
- **Version Checker**: Semantic version comparison engine
- **API Client**: requests library with session management
- **Threading**: Background operations to prevent UI freezing

### Dependencies
- `requests`: HTTP library for API communication
- `tkinter`: Built-in Python GUI framework
- `winreg`: Windows registry access (Windows only)
- `subprocess`: System integration features
- `pathlib`: Modern path handling

## Development

### Extending the Application

To add new features:

1. **New Scan Methods**: Add to the `GOGGameScanner` class
2. **API Endpoints**: Add to the `GOGGamesAPI` class methods
3. **UI Components**: Modify the `create_widgets` method
4. **Version Formats**: Extend the `compare_versions` method

### Code Structure

```
gog_api_gui.py
├── GOGGameScanner        # Game detection and scanning
│   ├── find_gog_galaxy() # Locate GOG Galaxy installation
│   ├── find_gog_games()  # Multi-method game detection
│   └── Registry/Dir scan # Various scanning methods
├── GOGGamesAPI          # API interaction handler  
│   ├── get_game_version_info() # Version checking
│   └── get_changelog()  # Changelog retrieval
└── GOGGamesGUI         # Main GUI application
    ├── scan_installed_games() # Game scanning workflow
    ├── check_all_updates()    # Version checking workflow
    └── Display methods        # UI update and management
```

## License

This project is for educational and personal use. Please respect the terms of service of gog-games.to.

## Disclaimer

This application is not affiliated with GOG.com or gog-games.to. It's an independent client for educational purposes.

## Support

If you encounter issues:
1. Check the troubleshooting section
2. Review the scan log tab for detailed information
3. Ensure you have the latest version of the application 

### How Build ID Comparison Works
- **Build ID Priority**: The application first looks for build IDs in GOG metadata files (e.g., "buildId": "58465618714994950")
- **Fallback System**: If no build ID is found, falls back to GOG ID or version strings
- **Numeric Comparison**: For build IDs, performs intelligent numeric comparison to determine if an update is available
- **Accurate Updates**: Build IDs provide more precise update detection than version strings

## Building Executable

You can create a standalone executable (.exe) file for easy distribution and use without requiring Python installation.

### Quick Build (Automated)

The easiest way to build the executable:

1. **Run the build script**: Double-click `build_exe.bat` or run it from command line
2. **Wait for completion**: The script will automatically handle all steps
3. **Find your exe**: The executable will be created in the `dist/` folder

### Manual Build (Step-by-Step)

If you prefer to build manually or need to customize the process:

#### Prerequisites
- Python 3.7+ installed and added to PATH
- All dependencies installed (`pip install -r requirements.txt`)

#### Step 1: Install PyInstaller
```bash
pip install pyinstaller
```

#### Step 2: Clean Previous Builds (Optional)
```bash
# Remove old build artifacts
rmdir /s /q build dist
del GOG-Games-Checker-WithHelp.spec
```

#### Step 3: Build the Executable

**Without custom icon:**
```bash
pyinstaller --onefile --windowed --name "GOG-Games-Checker-WithHelp" gog_api_gui.py
```

**With custom icon:**
```bash
pyinstaller --onefile --windowed --icon=icon.ico --name "GOG-Games-Checker-WithHelp" gog_api_gui.py
```

**Command Options Explained:**
- `--onefile`: Creates a single executable file (no additional folders needed)
- `--windowed`: No console window (GUI-only application)
- `--icon=icon.ico`: Custom icon file (optional, must be .ico format)
- `--name "GOG-Games-Checker-WithHelp"`: Custom name for the executable

#### Step 4: Locate Your Executable
The built executable will be located at:
```
dist/GOGChecker.exe
```

### Adding a Custom Icon

To give your executable a custom icon:

#### Option 1: Automatic (Recommended)
1. **Get an icon file**: Create or download a `.ico` file
2. **Name it `icon.ico`**: Place it in the same folder as your Python files
3. **Run the build**: Use `build_exe.bat` - it will automatically detect and use the icon

#### Option 2: Manual
1. **Get an icon file**: Any `.ico` file will work
2. **Update the build command**: Add `--icon=your_icon_name.ico` to the PyInstaller command
3. **Build normally**: The exe will use your custom icon

#### Creating Icon Files

**From existing images:**
- **Online converters**: Use websites like ico-convert.com or convertio.co
- **GIMP**: Free image editor with ICO export support
- **Paint.NET**: Free Windows image editor with ICO plugin

**Icon requirements:**
- **Format**: Must be `.ico` format for Windows
- **Size**: 16x16, 32x32, 48x48, 256x256 pixels (multi-size ICO recommended)
- **Location**: Place in the same directory as `gog_api_gui.py`

**Example sources for icons:**
- **Icons8**: Free icons with attribution
- **Flaticon**: Large collection of free icons
- **IconFinder**: Professional icon marketplace
- **Custom**: Create your own using image editing software

### Build Configuration

The build process creates several files:
- **`GOGChecker.spec`**: PyInstaller configuration file with all dependencies (can be reused)
- **`build/`**: Temporary build files (can be deleted)
- **`dist/GOGChecker.exe`**: Final executable (~8-10MB)
- **`icon.ico`**: Optional custom icon file (if provided)

### Rebuilding

For future rebuilds, you can either:
- **Use the batch file**: Run `build_exe.bat` again (recommended)
- **Use the spec file**: `pyinstaller GOGChecker.spec`
- **Manual build**: Use the PyInstaller command with hidden imports (see batch file)

### Distribution

The created executable (`GOGChecker.exe`) is completely self-contained and can be:
- Copied to any Windows computer
- Run without installing Python or dependencies
- Shared with others for easy use

### Build Troubleshooting

**Common Build Issues:**

1. **PyInstaller not found**
   - Solution: Add Python Scripts directory to PATH or use `py -m PyInstaller`

2. **Build fails with import errors**
   - Solution: Ensure all dependencies are installed (`pip install -r requirements.txt`)

3. **Large executable size**
   - Normal: The ~44MB size includes Python runtime and all dependencies
   - Alternative: Use `--onedir` instead of `--onefile` for faster loading

4. **Antivirus flags the executable**
   - Normal: Some antivirus software flags PyInstaller executables as false positives
   - Solution: Add exception in antivirus or build on a different machine

5. **Icon not showing/Custom icon not applied**
   - Check the icon file is named exactly `icon.ico`
   - Ensure the file is in the same directory as `gog_api_gui.py`
   - Verify the file is a valid .ico format (not just renamed .png/.jpg)
   - Try rebuilding: icons are embedded during the build process 