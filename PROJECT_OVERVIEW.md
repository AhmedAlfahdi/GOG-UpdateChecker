# GOG Games Build ID Checker - Project Overview

## What We've Built

A comprehensive Qt6 GUI application for detecting installed GOG games and checking for updates using build ID comparison from the gog-games.to API.

## Project Structure

```
GOG-API/
├── launcher.py              # Application launcher
├── gog_api_gui.py          # Main Qt6 build ID checker
├── requirements.txt        # Python dependencies (includes PySide6)
├── run_gui.bat            # Windows launcher
├── README.md              # Comprehensive documentation
└── PROJECT_OVERVIEW.md    # This file
```

## Application

### Qt6 Build ID Checker

#### Launcher (`launcher.py`)
- Modern interface with automatic dependency checking
- Installs required dependencies if missing
- Direct launch of main application

#### Main Application (`gog_api_gui.py`)
- **Purpose**: Advanced build ID checking with modern Qt6 interface
- **Features**:
  - **Professional UI**: Beautiful Qt6 dark theme with responsive design
  - **Enhanced Layout**: Splitter-based resizable interface
  - **Color Coding**: Visual status indicators for games
  - **Better Threading**: Proper Qt6 threading for responsive UI
  - **Rich Styling**: Modern buttons, frames, and visual elements
  - **Font Controls**: Adjustable font sizes with keyboard shortcuts
  - **Clickable Elements**: Status links to game pages and install path links
  - **Auto-Detection**: Scans PC for installed GOG games via registry and directories
  - **Build ID Extraction**: Extracts build IDs from GOG metadata files
  - **API Integration**: Queries multiple GOG APIs for latest build information
  - **Intelligent Comparison**: Numeric comparison of build IDs for precise update detection
  - **Real-time Logging**: Detailed scan and checking progress with timestamps
  - **Changelog Display**: Rich text display with clickable links for game information

## Key Technical Features

### Advanced Game Detection
- **Registry Scanning**: Searches Windows registry for GOG game installations
- **Directory Analysis**: Scans common GOG installation directories
- **GOG Galaxy Integration**: Detects and integrates with GOG Galaxy client
- **Metadata Parsing**: Extracts version information from various file formats

### Build ID-Based Version Checking
- **Priority System**: Prioritizes build IDs over version strings for accuracy
- **Numeric Comparison**: Intelligent comparison of large numeric build IDs
- **Fallback Logic**: Falls back to GOG IDs or version strings when build IDs unavailable
- **API Integration**: Queries multiple API sources for latest build information

### Robust API Handling
- **Multi-API Support**: Tries gog-games.to, GOGDB, and official GOG APIs
- **Graceful Fallbacks**: Continues operation if one API fails
- **Rate Limiting**: Respectful API usage with delays between requests
- **Error Recovery**: Comprehensive error handling and user feedback

### Modern UI Design
- **Dark Theme**: Professional dark interface throughout
- **Responsive Layout**: Resizable paned windows and proper column sizing
- **Real-time Updates**: Live display updates during scanning operations
- **Tabbed Interface**: Organized layout with game list, logs, and changelogs
- **Interactive Elements**: Clickable status links and install paths
- **Font Management**: User-configurable font sizes with persistence

### Threading for Responsiveness
- All scanning and API operations run in background threads
- UI remains responsive during long operations
- Real-time status updates and progress logging
- Graceful handling of user interactions during operations

## How to Use

1. **Quick Start**: Run `python launcher.py` or double-click `run_gui.bat` (Windows)
2. **Automatic Scanning**: The application automatically scans for installed GOG games
3. **Update Checking**: Review the results to see which games have updates available
4. **View Details**: Check the changelog tab for detailed update information
5. **Font Controls**: Use Ctrl+/- to adjust font size, Ctrl+0 to reset
6. **Quick Access**: Click status links to open game pages, click install paths to open folders

## Build ID Integration Approach

The application uses build IDs from GOG metadata files for precise version comparison:

- **Metadata Parsing**: Extracts build IDs from goggame-*.info files
- **API Querying**: Queries multiple APIs to get latest build information
- **Numeric Comparison**: Compares build IDs numerically for accurate update detection
- **Fallback System**: Uses GOG IDs or version strings when build IDs unavailable

## Future Enhancement Possibilities

- **Automated Updates**: Direct game updating capabilities
- **Notification System**: Alert users when new updates are available
- **Update History**: Track update history and changelog archives
- **Batch Operations**: Select and update multiple games at once
- **Custom Install Paths**: Support for non-standard installation directories
- **Export Features**: Export game lists and update reports

## Success Criteria Met

✅ **Build ID Comparison**: Accurate version checking using build IDs  
✅ **Automatic Detection**: Scans PC for installed GOG games  
✅ **API Integration**: Connects to multiple GOG APIs with robust error handling  
✅ **Update Checking**: Precise update detection and status display  
✅ **Professional UI**: Modern Qt6 dark theme with enhanced interface  
✅ **Real-time Feedback**: Live logging and progress updates  
✅ **Interactive Features**: Clickable links and font controls  
✅ **Cross-Platform**: Works on Windows with GOG support  

## Dependencies

- **Python 3.7+**: Core language requirement
- **PySide6**: Qt6 GUI framework
- **requests**: HTTP library for API communication
- **winreg**: Windows registry access (Windows only)
- **Standard Library**: json, threading, os, re, time, etc.

The project provides accurate, build ID-based version checking for GOG games with a modern Qt6 interface featuring clickable elements, font controls, and comprehensive game detection capabilities. 