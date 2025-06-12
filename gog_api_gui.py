#!/usr/bin/env python3
"""
GOG Games Build ID Checker - Qt6 GUI
Modern Qt6-based interface for checking GOG game updates using build IDs
"""

import sys
import os
import re
import json
import time
import threading
import urllib.request
import urllib.error
try:
    import winreg
except ImportError:
    winreg = None

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTreeWidget, QTreeWidgetItem, QTabWidget, QTextEdit, QTextBrowser, QPushButton,
    QLabel, QSplitter, QFrame, QProgressBar, QMessageBox, QHeaderView,
    QSizePolicy, QSpacerItem, QMenuBar, QMenu, QCheckBox
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSettings
from PySide6.QtGui import QFont, QIcon, QPalette, QColor, QAction, QKeySequence

# Import the game scanner from the original file
import winreg
import subprocess

# Version information
APP_VERSION = "1.2.0"
GITHUB_REPO = "AhmedAlfahdi/GOG-UpdateChecker"
UPDATE_CHECK_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


class GitHubUpdateChecker:
    """Class to check for application updates from GitHub releases"""
    
    def __init__(self):
        """Initialize the update checker"""
        self.current_version = APP_VERSION
        self.latest_version = None
        self.download_url = None
        self.release_notes = None
        
    def check_for_updates(self):
        """Check GitHub for the latest release"""
        try:
            request = urllib.request.Request(UPDATE_CHECK_URL)
            request.add_header('User-Agent', f'GOG-UpdateChecker/{self.current_version}')
            
            with urllib.request.urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                
                self.latest_version = data.get('tag_name', '').lstrip('v')
                self.download_url = data.get('html_url')
                self.release_notes = data.get('body', 'No release notes available.')
                
                return {
                    'current_version': self.current_version,
                    'latest_version': self.latest_version,
                    'update_available': self._is_newer_version(self.latest_version, self.current_version),
                    'download_url': self.download_url,
                    'release_notes': self.release_notes
                }
                
        except Exception as e:
            return {
                'error': f'Failed to check for updates: {str(e)}',
                'current_version': self.current_version
            }
    
    def _is_newer_version(self, latest, current):
        """Compare version strings to determine if an update is available"""
        try:
            # Split versions into parts and convert to integers for comparison
            latest_parts = [int(x) for x in latest.split('.') if x.isdigit()]
            current_parts = [int(x) for x in current.split('.') if x.isdigit()]
            
            # Pad shorter version with zeros
            max_length = max(len(latest_parts), len(current_parts))
            latest_parts.extend([0] * (max_length - len(latest_parts)))
            current_parts.extend([0] * (max_length - len(current_parts)))
            
            return latest_parts > current_parts
        except:
            # If version parsing fails, compare as strings
            return latest != current


class AppUpdateCheckThread(QThread):
    """Thread for checking application updates without blocking the UI"""
    update_checked = Signal(dict)
    
    def __init__(self):
        super().__init__()
        self.update_checker = GitHubUpdateChecker()
    
    def run(self):
        """Run the update check in background"""
        result = self.update_checker.check_for_updates()
        self.update_checked.emit(result)


class GOGGameScanner:
    """Scanner class for detecting installed GOG games - reused from original implementation"""
    
    def __init__(self):
        """Initialize the GOG game scanner"""
        self.found_games = []
        self.progress_callback = None
        
    def find_gog_galaxy(self):
        """Find GOG Galaxy installation"""
        # Common GOG Galaxy installation paths
        possible_paths = [
            "C:\\Program Files (x86)\\GOG Galaxy\\GalaxyClient.exe",
            "C:\\Program Files\\GOG Galaxy\\GalaxyClient.exe",
            "C:\\Users\\{}\\AppData\\Local\\GOG.com\\Galaxy\\GalaxyClient.exe".format(os.getenv('USERNAME', 'User')),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # Try registry
        if winreg:
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\GOG.com\GalaxyClient\paths")
                client_path = winreg.QueryValueEx(key, "client")[0]
                if os.path.exists(client_path):
                    return client_path
            except:
                pass
        
        return None
        
    def find_gog_games(self, deep_scan=False):
        """Find all installed GOG games"""
        self.found_games = []
        
        if self.progress_callback:
            scan_type = "Deep Scan" if deep_scan else "Quick Scan"
            self.progress_callback(f"Starting {scan_type} - Scanning Windows registry...")
        
        # Scan registry
        registry_games = self._scan_registry()
        
        if self.progress_callback:
            if deep_scan:
                self.progress_callback("Deep Scan - Searching all common directories (this may take longer)...")
            else:
                self.progress_callback("Quick Scan - Scanning standard game directories...")
        
        # Scan directories
        directory_games = self._scan_directories(deep_scan=deep_scan)
        
        if self.progress_callback:
            self.progress_callback("Processing found games...")
        
        # Combine and deduplicate
        all_games = registry_games + directory_games
        unique_games = {}
        
        for game in all_games:
            game_name = game.get('name', '').lower()
            if game_name and game_name not in unique_games:
                unique_games[game_name] = game
        
        self.found_games = list(unique_games.values())
        
        if self.progress_callback:
            scan_type = "Deep scan" if deep_scan else "Quick scan"
            self.progress_callback(f"{scan_type} complete - found {len(self.found_games)} games")
        
        return self.found_games
    
    def _scan_registry(self):
        """Scan Windows registry for GOG games"""
        games = []
        
        if not winreg:
            return games
        
        registry_paths = [
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
        ]
        
        for registry_path in registry_paths:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, registry_path) as key:
                    gog_keys = []
                    
                    try:
                        i = 0
                        while True:
                            subkey_name = winreg.EnumKey(key, i)
                            if 'gog' in subkey_name.lower() or subkey_name.startswith('1'):
                                gog_keys.append(subkey_name)
                            i += 1
                    except WindowsError:
                        pass
                    
                    for gog_key in gog_keys:
                        game_info = self._extract_game_info_from_registry(key, gog_key)
                        if game_info:
                            games.append(game_info)
                            
            except Exception:
                continue
        
        return games 
    
    def _extract_game_info_from_registry(self, parent_key, game_key):
        """Extract game information from registry entry"""
        try:
            with winreg.OpenKey(parent_key, game_key) as key:
                game_info = {}
                
                # Get basic info
                try:
                    game_info['name'] = winreg.QueryValueEx(key, 'DisplayName')[0]
                except:
                    game_info['name'] = game_key
                
                try:
                    game_info['install_path'] = winreg.QueryValueEx(key, 'InstallLocation')[0]
                except:
                    game_info['install_path'] = "Unknown"
                
                # Try to get version
                version_keys = ['DisplayVersion', 'Version', 'VersionMajor', 'VersionMinor']
                for version_key in version_keys:
                    try:
                        version_value = winreg.QueryValueEx(key, version_key)[0]
                        cleaned_version = self._clean_version_string(version_value)
                        if cleaned_version:
                            game_info['installed_version'] = cleaned_version
                            break
                    except:
                        continue
                else:
                    game_info['installed_version'] = "Unknown"
                
                # Get size info
                try:
                    size_bytes = winreg.QueryValueEx(key, 'EstimatedSize')[0]
                    game_info['size'] = f"{size_bytes / 1024:.1f} MB"
                except:
                    path = game_info.get('install_path', '')
                    if path and path != "Unknown" and os.path.exists(path):
                        game_info['size'] = self._get_directory_size(path)
                    else:
                        game_info['size'] = "Unknown"
                
                return game_info
                
        except Exception:
            return None
    
    def _clean_version_string(self, version_str):
        """Clean and validate version string"""
        if not version_str:
            return None
        
        version_str = str(version_str).strip()
        
        # Remove common prefixes
        prefixes = ['v', 'ver', 'version', 'rel', 'release']
        for prefix in prefixes:
            if version_str.lower().startswith(prefix):
                version_str = version_str[len(prefix):].strip('.: ')
                break
        
        # Remove trailing zeros in X.Y.Z.0 format
        parts = version_str.split('.')
        while len(parts) > 2 and parts[-1] == '0':
            parts.pop()
        
        clean_version = '.'.join(parts)
        return clean_version if self._is_valid_version(clean_version) else None
    
    def _scan_directories(self, deep_scan=False):
        """Scan common directories for GOG games"""
        games = []
        
        if deep_scan:
            # Deep scan: check all common drive letters and directories
            search_paths = self._get_deep_scan_paths()
        else:
            # Quick scan: most common GOG installation directories (optimized for speed)
            search_paths = [
                "C:\\Program Files (x86)\\GOG Games",
                "C:\\Program Files\\GOG Games", 
                "C:\\GOG Games",
                "D:\\GOG Games",
                "C:\\Games\\GOG",
                "D:\\Games\\GOG",
                "C:\\Games",
                "D:\\Games"
            ]
        
        total_paths = len(search_paths)
        for i, path in enumerate(search_paths):
            if self.progress_callback and deep_scan:
                progress_percent = (i / total_paths) * 100
                self.progress_callback(f"Deep Scan - Checking directory {i+1}/{total_paths}: {path[:50]}{'...' if len(path) > 50 else ''}")
            
            if os.path.exists(path):
                try:
                    items = os.listdir(path)
                    
                    for item in items:
                        item_path = os.path.join(path, item)
                        if os.path.isdir(item_path):
                            if self._is_gog_game_directory(item_path):
                                game_info = self._analyze_game_directory(item_path, item)
                                if game_info:
                                    games.append(game_info)
                                    
                except Exception:
                    pass
        return games
    
    def _get_deep_scan_paths(self):
        """Get comprehensive list of directories for deep scan"""
        import string
        
        search_paths = []
        
        # Check all available drive letters
        available_drives = []
        for drive_letter in string.ascii_uppercase:
            drive_path = f"{drive_letter}:\\"
            if os.path.exists(drive_path):
                available_drives.append(drive_letter)
        
        # Common directory patterns for each drive
        common_patterns = [
            "\\Program Files (x86)\\GOG Games",
            "\\Program Files\\GOG Games",
            "\\GOG Games",
            "\\Games\\GOG",
            "\\Games\\GOG Games",
            "\\Games",
            "\\Gaming\\GOG",
            "\\Gaming\\GOG Games",
            "\\Steam\\steamapps\\common",  # Sometimes GOG games are moved here
            "\\Epic Games\\",
            "\\GOG.com",
            "\\Software\\GOG",
            "\\Applications\\GOG",
            "\\Programs\\GOG"
        ]
        
        # User-specific directories
        username = os.getenv('USERNAME', 'User')
        user_patterns = [
            f"\\Users\\{username}\\Documents\\GOG Games",
            f"\\Users\\{username}\\Games\\GOG",
            f"\\Users\\{username}\\Games",
            f"\\Users\\{username}\\Desktop\\GOG Games",
            f"\\Users\\{username}\\Downloads\\GOG Games",
            f"\\Users\\{username}\\AppData\\Local\\GOG.com\\Galaxy\\Games",
            f"\\Users\\{username}\\AppData\\Roaming\\GOG.com\\Galaxy\\Games"
        ]
        
        # Build complete path list
        for drive in available_drives:
            # Add common patterns
            for pattern in common_patterns:
                search_paths.append(f"{drive}:{pattern}")
            
            # Add user-specific patterns (only for C: drive to avoid duplicates)
            if drive == 'C':
                for pattern in user_patterns:
                    search_paths.append(f"{drive}:{pattern}")
        
        # Add some absolute paths that might exist
        additional_paths = [
            "C:\\Program Files (x86)\\GOG.com\\Games",
            "C:\\Program Files\\GOG.com\\Games", 
            "C:\\ProgramData\\GOG.com\\Galaxy\\Games",
            "D:\\Steam\\steamapps\\common",
            "E:\\Games",
            "F:\\Games",
            "G:\\Games"
        ]
        
        search_paths.extend(additional_paths)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_paths = []
        for path in search_paths:
            if path not in seen:
                seen.add(path)
                unique_paths.append(path)
        
        return unique_paths
    
    def _find_gog_metadata(self, directory):
        """Find GOG metadata file in directory"""
        try:
            for file in os.listdir(directory):
                if file.lower().startswith('goggame-') and file.lower().endswith('.info'):
                    return file
        except:
            pass
        return None
    
    def _is_gog_game_directory(self, directory_path):
        """Check if directory contains GOG game files"""
        try:
            files = os.listdir(directory_path)
            for file in files:
                if file.lower().startswith('goggame-') and file.lower().endswith('.info'):
                    return True
        except:
            pass
        return False
    
    def _analyze_game_directory(self, game_path, folder_name):
        """Analyze a directory to extract game information"""
        try:
            game_info = {
                'name': folder_name,
                'install_path': game_path,
                'installed_version': "Unknown",
                'size': self._get_directory_size(game_path)
            }
            
            # Look for GOG metadata files
            gog_version = self._detect_gog_metadata_version(game_path)
            if gog_version:
                game_info['installed_version'] = gog_version
            
            # Look for executable files
            exe_files = []
            try:
                for file in os.listdir(game_path):
                    if file.endswith('.exe') and not file.lower().startswith(('unins', 'setup', 'install', 'crash', 'error')):
                        exe_files.append(file)
                
                if exe_files:
                    game_info['executable'] = exe_files[0]
                else:
                    return None
                    
            except:
                return None
            
            return game_info
            
        except Exception:
            return None
    
    def _detect_gog_metadata_version(self, game_path):
        """Detect version from GOG metadata files"""
        try:
            for file in os.listdir(game_path):
                if file.lower().startswith('goggame-') and file.lower().endswith('.info'):
                    match = re.search(r'goggame-(\d+)\.info', file.lower())
                    if match:
                        gog_id = match.group(1)
                        info_path = os.path.join(game_path, file)
                        
                        # Parse file for build ID
                        try:
                            with open(info_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                            
                            # Look for build ID patterns
                            build_id_patterns = [
                                r'"buildId"\s*:\s*"([^"]+)"',
                                r'"build_id"\s*:\s*"([^"]+)"',
                                r'"build"\s*:\s*"([^"]+)"'
                            ]
                            
                            for pattern in build_id_patterns:
                                match = re.search(pattern, content, re.IGNORECASE)
                                if match:
                                    build_id = match.group(1).strip('"\'')
                                    if build_id and build_id.isdigit() and len(build_id) >= 8:
                                        return build_id
                            
                            # Fallback to GOG ID
                            return gog_id
                            
                        except:
                            return gog_id
            
            return None
        except Exception:
            pass
        return None

    def _parse_gog_info_file(self, file_path, gog_id):
        """Parse GOG .info file to extract build ID information"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            # First priority: Look for buildId
            build_id_patterns = [
                r'"buildId"\s*:\s*"([^"]+)"',
                r'"build_id"\s*:\s*"([^"]+)"',
                r'"build"\s*:\s*"([^"]+)"',
                r'buildId[:\s=]+([^\s\n\r,}]+)',
                r'build_id[:\s=]+([^\s\n\r,}]+)',
                r'build[:\s=]+([^\s\n\r,}]+)'
            ]
            
            for pattern in build_id_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    build_id = match.group(1).strip('"\'')
                    if build_id and build_id != gog_id and build_id.isdigit() and len(build_id) >= 5:
                        return build_id
            
            # Second priority: Look for version information
            version_patterns = [
                r'"version"\s*:\s*"([^"]+)"',
                r'"versionName"\s*:\s*"([^"]+)"',
                r'version[:\s=]+([^\s\n\r,}]+)'
            ]
            
            for pattern in version_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    version = match.group(1).strip('"\'')
                    if version and version != gog_id:
                        return version
            
            return None
            
        except Exception:
            return None
    
    def _extract_version_from_text(self, text):
        """Extract version number from text using various patterns"""
        if not text:
            return None
            
        # Enhanced patterns for version detection
        patterns = [
            # Standard version patterns
            r'version\s*[:=]\s*([0-9]+(?:\.[0-9]+)+)',
            r'v\.?\s*([0-9]+(?:\.[0-9]+)+)',
            r'ver\.?\s*([0-9]+(?:\.[0-9]+)+)',
            # Specific version formats
            r'([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)',  # X.Y.Z.W
            r'([0-9]+\.[0-9]+\.[0-9]+)',          # X.Y.Z
            r'([0-9]+\.[0-9]+)',                  # X.Y (only if reasonable)
            # Build/release patterns
            r'build\s*[:=]\s*([0-9]+(?:\.[0-9]+)*)',
            r'release\s*[:=]\s*([0-9]+(?:\.[0-9]+)*)',
            r'rev\s*[:=]\s*([0-9]+(?:\.[0-9]+)*)',
            r'revision\s*[:=]\s*([0-9]+(?:\.[0-9]+)*)',
            # Game-specific patterns
            r'game\s*version\s*[:=]\s*([0-9]+(?:\.[0-9]+)+)',
            r'client\s*version\s*[:=]\s*([0-9]+(?:\.[0-9]+)+)',
            r'app\s*version\s*[:=]\s*([0-9]+(?:\.[0-9]+)+)',
            # Generic number patterns (more specific)
            r'\b([0-9]{1,2}\.[0-9]{1,3}\.[0-9]{1,4})\b',  # Bounded version numbers
        ]
        
        text_lower = text.lower()
        
        # Try each pattern and validate results
        for pattern in patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                version = match.strip()
                print(f"DEBUG _extract_version_from_text: Found potential version '{version}' with pattern '{pattern}'")
                
                if self._is_valid_version(version):
                    # Additional check for X.Y format - should be reasonable numbers
                    parts = version.split('.')
                    if len(parts) == 2:
                        try:
                            major, minor = int(parts[0]), int(parts[1])
                            # Only accept X.Y if numbers seem reasonable for a version
                            if major > 20 or minor > 999:  # Probably not a version
                                continue
                        except ValueError:
                            continue
                    
                    print(f"DEBUG _extract_version_from_text: Accepting version '{version}'")
                    return version
        
        print(f"DEBUG _extract_version_from_text: No valid version found in text")
        return None
    
    def _is_valid_version(self, version):
        """Validate if a version string looks reasonable"""
        if not version:
            return False
        
        parts = version.split('.')
        if len(parts) > 5 or len(parts) < 1:
            return False
        
        try:
            nums = [int(p) for p in parts]
            if any(n > 9999 for n in nums):
                return False
            return True
        except ValueError:
            return False
    
    def _get_directory_size(self, path):
        """Get directory size in human readable format"""
        try:
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except:
                        continue
            
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if total_size < 1024.0:
                    return f"{total_size:.1f} {unit}"
                total_size /= 1024.0
            
            return f"{total_size:.1f} PB"
            
        except:
            return "Unknown"


class GameScanThread(QThread):
    """Thread for scanning games without blocking the UI"""
    games_found = Signal(list)
    log_message = Signal(str)
    scan_progress = Signal(str)  # New signal for scan progress updates
    
    def __init__(self, deep_scan=False):
        super().__init__()
        self.scanner = GOGGameScanner()
        self.deep_scan = deep_scan
    
    def run(self):
        """Run the game scanning in a separate thread"""
        try:
            scan_type = "deep scan" if self.deep_scan else "quick scan"
            self.log_message.emit(f"🔄 Starting {scan_type}...")
            self.scan_progress.emit("Initializing scan...")
            
            if self.deep_scan:
                self.log_message.emit("⚠️ Deep scan enabled - this will take longer but finds more games")
            
            # Connect scanner progress to our signals
            self.scanner.progress_callback = self.scan_progress.emit
            
            games = self.scanner.find_gog_games(deep_scan=self.deep_scan)
            self.games_found.emit(games)
            
            scan_type_caps = "Deep scan" if self.deep_scan else "Quick scan" 
            self.log_message.emit(f"✅ {scan_type_caps} completed! Found {len(games)} games")
        except Exception as e:
            self.log_message.emit(f"❌ Error during scan: {str(e)}")


class UpdateCheckThread(QThread):
    """Thread for checking game updates without blocking the UI"""
    update_progress = Signal(dict)
    log_message = Signal(str)
    finished = Signal()
    progress_update = Signal(int, str)  # New signal for progress updates
    network_error_detected = Signal()  # Signal for network connectivity issues
    
    def __init__(self, games):
        super().__init__()
        self.games = games
    
    def run(self):
        """Run the update checking in a separate thread"""
        try:
            self.log_message.emit("🔄 Starting version checking...")
            
            for i, game in enumerate(self.games):
                game_name = game.get('name', '')
                install_path = game.get('install_path', '')
                
                # Emit progress update
                self.progress_update.emit(i, f"Analyzing {game_name}")
                
                self.log_message.emit(f"🎮 Checking: {game_name}")
                
                # Detect version from GOG files
                detected_version = self.detect_version_from_gog_files(install_path)
                
                # Detect readable version (like 1.2.26) separately from build ID
                readable_version = self.detect_readable_version_from_gog_files(install_path)
                
                # Extract actual GOG ID for API calls
                actual_gog_id = None
                if install_path and os.path.exists(install_path):
                    try:
                        for file in os.listdir(install_path):
                            if file.lower().startswith('goggame-') and file.lower().endswith('.info'):
                                match = re.search(r'goggame-(\d+)\.info', file.lower())
                                if match:
                                    actual_gog_id = match.group(1)
                                    break
                    except:
                        pass
                
                if detected_version:
                    game['installed_version'] = detected_version
                    if actual_gog_id:
                        game['gog_id'] = actual_gog_id
                
                # Store the readable version separately
                game['readable_version'] = readable_version if readable_version else '-'
                
                # If no readable version found, try to get it from GOGDB later
                if not readable_version and actual_gog_id:
                    self.log_message.emit(f"   📋 Will attempt to get version from GOGDB for GOG ID: {actual_gog_id}")
                
                if detected_version:
                    if detected_version.isdigit() and len(detected_version) >= 8:
                        self.log_message.emit(f"   🎯 Found Build ID: {detected_version}")
                    else:
                        self.log_message.emit(f"   🎯 Found GOG ID: {detected_version}")
                else:
                    self.log_message.emit(f"   ❌ Could not detect version/build ID")
                
                # Get latest version info from APIs
                self.progress_update.emit(i, f"Fetching data for {game_name}")
                self.log_message.emit(f"   🌐 Fetching from GOG Database API...")
                api_id = actual_gog_id if actual_gog_id else detected_version
                self.log_message.emit(f"   🔧 Using API ID: {api_id} (actual_gog_id: {actual_gog_id}, detected_version: {detected_version})")
                version_info = self.get_latest_version_info(game_name, api_id)
                
                time.sleep(0.3)  # Reduced rate limiting for faster processing
                
                if version_info and 'error' not in version_info:
                    game['latest_version'] = version_info.get('latest_version', 'Unknown')
                    game['changelog'] = version_info.get('changelog', 'No changelog available')
                    game['tags'] = version_info.get('tags', '🎮')
                    source = version_info.get('source', 'unknown')
                    
                    # If we didn't find a readable version locally, try to use the one from API
                    if game['readable_version'] == '-':
                        api_readable_version = version_info.get('readable_version')
                        if api_readable_version:
                            game['readable_version'] = api_readable_version
                            self.log_message.emit(f"   🎯 Got readable version from API: {api_readable_version}")
                    
                    # Compare versions
                    installed_version = game.get('installed_version', 'Unknown')
                    latest_version = game['latest_version']
                    
                    if installed_version == 'Unknown':
                        game['update_status'] = 'Cannot Check - No Installed Version'
                    elif latest_version == 'Unknown':
                        game['update_status'] = 'Cannot Check - No Latest Version'
                    elif source in ['local_detection', 'local_fallback']:
                        # For local fallbacks, show as "reference" status
                        if installed_version == latest_version:
                            if source == 'local_detection':
                                game['update_status'] = 'DLC - Base Game Reference'
                                self.log_message.emit(f"   📦 DLC uses base game build ID: {installed_version}")
                            else:
                                game['update_status'] = 'Local Reference Only'
                                self.log_message.emit(f"   📋 Using local build ID as reference: {installed_version}")
                        else:
                            # Even if there's a mismatch, for local sources we should show a friendlier message
                            if source == 'local_detection':
                                game['update_status'] = 'DLC - Base Game Reference'
                                self.log_message.emit(f"   📦 DLC reference (install: {installed_version}, ref: {latest_version})")
                            else:
                                game['update_status'] = 'Local Reference Only'
                                self.log_message.emit(f"   📋 Local reference (install: {installed_version}, ref: {latest_version})")
                            # Update latest version to match installed to avoid confusion
                            game['latest_version'] = installed_version
                    elif installed_version == latest_version:
                        game['update_status'] = 'Up to Date'
                        version_type = "Build ID" if latest_version.isdigit() and len(latest_version) >= 8 else "Version"
                        self.log_message.emit(f"   ✅ {version_type}s match - same version! ({installed_version})")
                    else:
                        # For build IDs, do numeric comparison
                        if (installed_version.isdigit() and latest_version.isdigit() and 
                            len(installed_version) >= 8 and len(latest_version) >= 8):
                            try:
                                installed_build = int(installed_version)
                                latest_build = int(latest_version)
                                if installed_build < latest_build:
                                    game['update_status'] = 'Update Available'
                                    self.log_message.emit(f"   🔄 Build ID comparison: older build detected: {installed_version} → {latest_version}")
                                elif installed_build > latest_build:
                                    game['update_status'] = 'Newer Version Installed'
                                    self.log_message.emit(f"   ⬆️ Build ID comparison: newer build installed: {installed_version} vs {latest_version}")
                                else:
                                    game['update_status'] = 'Up to Date'
                                    self.log_message.emit(f"   ✅ Build IDs match: {installed_version}")
                            except ValueError:
                                game['update_status'] = 'Different Version'
                                self.log_message.emit(f"   🔄 Version comparison failed, versions differ: {installed_version} ≠ {latest_version}")
                        else:
                            game['update_status'] = 'Different Version'
                            self.log_message.emit(f"   🔄 Versions differ: {installed_version} ≠ {latest_version}")
                else:
                    game['update_status'] = 'Not in Database'
                    game['latest_version'] = 'Unknown'
                    game['changelog'] = 'Changelog not available'
                
                # Keep readable version as dash if no real version found - don't use build IDs
                # The "Installed Version" column should only show actual version numbers, not build IDs
                
                # Emit progress update
                self.progress_update.emit(i + 1, f"Completed {game_name}")
                self.update_progress.emit(game.copy())
                self.log_message.emit(f"   ✅ Completed check for {game_name}\n")
            
            self.log_message.emit("🎉 Version check completed!")
            self.finished.emit()
            
        except Exception as e:
            self.log_message.emit(f"❌ Error during version checking: {str(e)}")
            self.finished.emit()
    
    def detect_version_from_gog_files(self, install_path):
        """Detect build ID from GOG metadata files"""
        try:
            if not install_path or not os.path.exists(install_path):
                return None
            
            # Cache for build ID detection too
            if hasattr(self, '_build_id_cache') and install_path in self._build_id_cache:
                return self._build_id_cache[install_path]
            
            if not hasattr(self, '_build_id_cache'):
                self._build_id_cache = {}
            
            # Get all .info files and just use the first one for speed
            info_files = [f for f in os.listdir(install_path) if f.lower().startswith('goggame-') and f.lower().endswith('.info')]
            if info_files:
                file = info_files[0]  # Just check the first one
                match = re.search(r'goggame-(\d+)\.info', file.lower())
                if match:
                    gog_id = match.group(1)
                    info_path = os.path.join(install_path, file)
                    
                    # Parse file for build ID
                    try:
                        with open(info_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read(500)  # Read only first 500 chars for speed
                        
                        # Look for build ID patterns
                        build_id_pattern = r'"buildId"\s*:\s*"([^"]+)"'  # Most common pattern first
                        match = re.search(build_id_pattern, content, re.IGNORECASE)
                        if match:
                            build_id = match.group(1).strip('"\'')
                            if build_id and build_id.isdigit() and len(build_id) >= 8:
                                self._build_id_cache[install_path] = build_id
                                return build_id
                        
                        # Quick fallback to GOG ID
                        self._build_id_cache[install_path] = gog_id
                        return gog_id
                        
                    except:
                        self._build_id_cache[install_path] = gog_id
                        return gog_id
            
            self._build_id_cache[install_path] = None
            return None
        except:
            return None
    
    def detect_readable_version_from_gog_files(self, install_path):
        """Detect readable version (like 1.2.26) from GOG metadata files"""
        try:
            if not install_path or not os.path.exists(install_path):
                return None
            
            # Cache for this path to avoid re-scanning
            if hasattr(self, '_version_cache') and install_path in self._version_cache:
                return self._version_cache[install_path]
            
            if not hasattr(self, '_version_cache'):
                self._version_cache = {}
            
            # Check GOG metadata files first (only check first .info file for speed)
            info_files = [f for f in os.listdir(install_path) if f.lower().startswith('goggame-') and f.lower().endswith('.info')]
            if info_files:
                info_path = os.path.join(install_path, info_files[0])  # Just check the first one
                
                try:
                    with open(info_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(1000)  # Read only first 1000 chars for speed
                    
                    # Look for version patterns (prioritize readable versions over build IDs)
                    version_patterns = [
                        # Standard JSON patterns - most common first
                        r'"version"\s*:\s*"([^"]+)"',
                        r'"versionName"\s*:\s*"([^"]+)"',
                        r'"productVersion"\s*:\s*"([^"]+)"',
                        # Alternative formats
                        r'version[:\s=]+([0-9]+(?:\.[0-9]+)+)',
                        # Quick pattern for X.Y.Z
                        r'([0-9]+\.[0-9]+\.[0-9]+)',
                    ]
                    
                    for pattern in version_patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        for match in matches:
                            version = match.strip('"\'')
                            # Check if it looks like a readable version (not a build ID)
                            if version and not (version.isdigit() and len(version) >= 8):
                                # Quick validation for version-like strings
                                if self._is_valid_version(version):
                                    self._version_cache[install_path] = version
                                    return version
                    
                except Exception:
                    pass
            
            # Check for version in game executable files (only if no version found in metadata)
            try:
                exe_files = [f for f in os.listdir(install_path) if f.endswith('.exe') and not f.lower().startswith(('unins', 'setup', 'install', 'crash', 'error', 'redist'))]
                if exe_files:
                    exe_path = os.path.join(install_path, exe_files[0])  # Check only the first main executable
                    version = self._get_exe_version(exe_path)
                    if version:
                        self._version_cache[install_path] = version
                        return version
            except Exception:
                pass
            
            # Quick fallback: Check only the most common version files
            quick_check_files = ['version.txt', 'VERSION']
            for config_file in quick_check_files:
                config_path = os.path.join(install_path, config_file)
                if os.path.exists(config_path):
                    try:
                        with open(config_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read(500)  # Read only first 500 chars
                        
                        version = self._extract_version_from_text(content)
                        if version and self._is_valid_version(version):
                            self._version_cache[install_path] = version
                            return version
                    except:
                        continue
            
            # Cache the "not found" result to avoid re-scanning
            self._version_cache[install_path] = None
            return None
            
        except Exception as e:
            print(f"DEBUG: Exception in version detection: {e}")
            return None
    
    def _looks_like_version(self, text):
        """Check if text looks like a version number"""
        if not text:
            return False
        
        # Must contain at least one dot
        if '.' not in text:
            return False
        
        # Should start with a number
        if not text[0].isdigit():
            return False
        
        # Should be reasonable length (versions are typically 3-15 chars)
        if len(text) < 3 or len(text) > 15:
            return False
        
        # Check if it follows version pattern (numbers and dots, maybe some letters)
        import re
        if re.match(r'^[0-9]+(?:\.[0-9]+)+(?:[a-zA-Z].*)?$', text):
            return True
        
        return False
    
    def _get_exe_version(self, exe_path):
        """Try to get version from Windows executable file properties"""
        try:
            # Try to use win32api if available
            try:
                import win32api
                import win32con
                
                # Get file version info
                info = win32api.GetFileVersionInfo(exe_path, "\\")
                ms = info['FileVersionMS']
                ls = info['FileVersionLS']
                
                # Extract version components
                version = f"{win32api.HIWORD(ms)}.{win32api.LOWORD(ms)}.{win32api.HIWORD(ls)}.{win32api.LOWORD(ls)}"
                
                # Clean up version (remove trailing .0s)
                parts = version.split('.')
                while len(parts) > 2 and parts[-1] == '0':
                    parts.pop()
                
                clean_version = '.'.join(parts)
                if clean_version != "0.0":
                    print(f"DEBUG: Extracted version from PE: {clean_version}")
                    return clean_version
                    
            except ImportError:
                print("DEBUG: win32api not available, trying alternative method")
                pass
            except Exception as e:
                print(f"DEBUG: win32api failed: {e}")
                pass
            
            # Alternative method using subprocess and PowerShell
            try:
                import subprocess
                
                # Use PowerShell to get file version
                ps_command = f'''
                $file = Get-Item "{exe_path}"
                if ($file.VersionInfo.FileVersion) {{
                    $file.VersionInfo.FileVersion
                }} elseif ($file.VersionInfo.ProductVersion) {{
                    $file.VersionInfo.ProductVersion
                }}
                '''
                
                result = subprocess.run(
                    ['powershell', '-Command', ps_command],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    version = result.stdout.strip()
                    if version and version != "0.0.0.0":
                                                 # Clean up version
                        clean_version = self._clean_version_string_thread(version)
                        if clean_version and self._is_valid_version(clean_version):
                            print(f"DEBUG: Extracted version from PowerShell: {clean_version}")
                            return clean_version
                
            except Exception as e:
                print(f"DEBUG: PowerShell method failed: {e}")
                pass
            
            return None
            
        except Exception as e:
            print(f"DEBUG: All version extraction methods failed: {e}")
            return None
    
    def _clean_version_string_thread(self, version_str):
        """Clean and validate version string for thread use"""
        if not version_str:
            return None
        
        version_str = str(version_str).strip()
        
        # Remove common prefixes
        prefixes = ['v', 'ver', 'version', 'rel', 'release']
        for prefix in prefixes:
            if version_str.lower().startswith(prefix):
                version_str = version_str[len(prefix):].strip('.: ')
                break
        
        # Remove trailing zeros in X.Y.Z.0 format
        parts = version_str.split('.')
        while len(parts) > 2 and parts[-1] == '0':
            parts.pop()
        
        clean_version = '.'.join(parts)
        return clean_version if self._is_valid_version(clean_version) else None
    
    def _extract_version_from_text(self, text):
        """Extract version number from text using various patterns"""
        if not text:
            return None
            
        # Enhanced patterns for version detection
        patterns = [
            # Standard version patterns
            r'version\s*[:=]\s*([0-9]+(?:\.[0-9]+)+)',
            r'v\.?\s*([0-9]+(?:\.[0-9]+)+)',
            r'ver\.?\s*([0-9]+(?:\.[0-9]+)+)',
            # Specific version formats
            r'([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)',  # X.Y.Z.W
            r'([0-9]+\.[0-9]+\.[0-9]+)',          # X.Y.Z
            r'([0-9]+\.[0-9]+)',                  # X.Y (only if reasonable)
            # Build/release patterns
            r'build\s*[:=]\s*([0-9]+(?:\.[0-9]+)*)',
            r'release\s*[:=]\s*([0-9]+(?:\.[0-9]+)*)',
            r'rev\s*[:=]\s*([0-9]+(?:\.[0-9]+)*)',
            r'revision\s*[:=]\s*([0-9]+(?:\.[0-9]+)*)',
            # Game-specific patterns
            r'game\s*version\s*[:=]\s*([0-9]+(?:\.[0-9]+)+)',
            r'client\s*version\s*[:=]\s*([0-9]+(?:\.[0-9]+)+)',
            r'app\s*version\s*[:=]\s*([0-9]+(?:\.[0-9]+)+)',
            # Generic number patterns (more specific)
            r'\b([0-9]{1,2}\.[0-9]{1,3}\.[0-9]{1,4})\b',  # Bounded version numbers
        ]
        
        text_lower = text.lower()
        
        # Try each pattern and validate results
        for pattern in patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                version = match.strip()
                print(f"DEBUG _extract_version_from_text: Found potential version '{version}' with pattern '{pattern}'")
                
                if self._is_valid_version(version):
                    # Additional check for X.Y format - should be reasonable numbers
                    parts = version.split('.')
                    if len(parts) == 2:
                        try:
                            major, minor = int(parts[0]), int(parts[1])
                            # Only accept X.Y if numbers seem reasonable for a version
                            if major > 20 or minor > 999:  # Probably not a version
                                continue
                        except ValueError:
                            continue
                    
                    print(f"DEBUG _extract_version_from_text: Accepting version '{version}'")
                    return version
        
        print(f"DEBUG _extract_version_from_text: No valid version found in text")
        return None
    
    def _is_valid_version(self, version):
        """Validate if a version string looks reasonable"""
        if not version:
            return False
        
        parts = version.split('.')
        if len(parts) > 5 or len(parts) < 1:
            return False
        
        try:
            nums = [int(p) for p in parts]
            if any(n > 9999 for n in nums):
                return False
            return True
        except ValueError:
            return False
    
    def get_latest_version_info(self, game_name, gog_id=None):
        """Get latest version info from APIs with multiple fallbacks"""
        try:
            # Handle DLC/expansion games - if it's a DLC, try to find the base game
            base_game_name = game_name
            is_dlc = False
            if any(dlc_keyword in game_name.lower() for dlc_keyword in [' - ', ': ', ' dlc', ' expansion', ' pack']):
                is_dlc = True
                # Extract base game name (everything before the first ' - ' or ': ')
                for separator in [' - ', ': ']:
                    if separator in game_name:
                        base_game_name = game_name.split(separator)[0]
                        self.log_message.emit(f"   📦 Detected DLC/Expansion: {game_name} → Base game: {base_game_name}")
                        break
            
            self.log_message.emit(f"   🔧 get_latest_version_info called with: game_name='{game_name}', gog_id='{gog_id}', is_dlc={is_dlc}")
            
            # Method 1: Try GOGDB API (if available)
            if gog_id:
                self.log_message.emit(f"   🌐 Method 1: Trying GOGDB API for GOG ID {gog_id}")
                gogdb_result = self.try_gogdb_api(gog_id, base_game_name, game_name, is_dlc)
                if gogdb_result and 'error' not in gogdb_result:
                    self.log_message.emit(f"   ✅ Method 1 succeeded, returning: {gogdb_result.get('latest_version')}")
                    return gogdb_result
                else:
                    self.log_message.emit(f"   ❌ Method 1 failed or returned error")
            
            # Method 2: Use installed build ID as "latest" (fallback for DLC)
            if gog_id and is_dlc:
                self.log_message.emit(f"   🎯 Method 2: Using installed build ID as reference for DLC")
                result = {
                    'latest_version': gog_id,  # Use the same gog_id that was detected as installed
                    'changelog': f"DLC/Expansion for {base_game_name}\n\nNote: DLCs typically share the same build ID as the base game. No separate version checking available for individual DLCs.\n\nInstalled Build ID: {gog_id}",
                    'build_id': gog_id,
                    'source': 'local_detection',
                    'base_game': base_game_name
                }
                self.log_message.emit(f"   ✅ Method 2 returning: {result['latest_version']}")
                return result
            
            # Method 3: For unknown games, create a reasonable response
            if gog_id:
                self.log_message.emit(f"   ℹ️ Method 3: Creating local reference for GOG ID {gog_id}")
                result = {
                    'latest_version': gog_id,  # Use the same gog_id that was detected as installed
                    'changelog': f"Build ID: {gog_id}\n\nNote: Unable to fetch version information from online databases. This may be because:\n- The game is not in the GOGDB database\n- The API is temporarily unavailable\n- The game is a newer release not yet indexed\n\nYour installed build ID is being used as reference.",
                    'build_id': gog_id,
                    'source': 'local_fallback'
                }
                self.log_message.emit(f"   ✅ Method 3 returning: {result['latest_version']}")
                return result
            
            self.log_message.emit(f"   ❌ No version information available for this game")
            return {"error": "No version information available"}
            
        except Exception as e:
            self.log_message.emit(f"   ❌ get_latest_version_info Error: {str(e)}")
            return {"error": str(e)}
    
    def try_gogdb_api(self, gog_id, base_game_name, game_name, is_dlc):
        """Try to fetch from GOGDB API with proper error handling"""
        try:
            url = f"https://www.gogdb.org/data/products/{gog_id}/product.json"
            headers = {
                'User-Agent': 'GOG-Games-Build-ID-Checker/1.0',
                'Accept': 'application/json'
            }
            
            self.log_message.emit(f"   🌐 Querying GOGDB API: {url}")
            request = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(request, timeout=10) as response:
                if response.status == 200:
                    self.log_message.emit(f"   ✅ GOGDB API responded successfully (HTTP {response.status})")
                    data = json.loads(response.read().decode('utf-8'))
                    
                    builds = data.get('builds', [])
                    if builds:
                        # Filter builds by current OS
                        current_os = self.get_current_os()
                        self.log_message.emit(f"   🖥️ Current OS detected: {current_os}")
                        
                        # Filter builds for current OS
                        os_builds = self.filter_builds_by_os(builds, current_os)
                        
                        if os_builds:
                            latest_build = os_builds[-1]  # Get latest build for current OS
                            self.log_message.emit(f"   📋 Found {len(os_builds)} builds for {current_os}, using latest build ID: {latest_build.get('id', '')}")
                        else:
                            # Fallback to latest build overall if no OS-specific build found
                            latest_build = builds[-1]
                            self.log_message.emit(f"   ⚠️ No {current_os} builds found, falling back to latest overall build: {latest_build.get('id', '')}")
                        
                        version = latest_build.get('version', 'Unknown')
                        build_id = latest_build.get('id', '')
                        
                        # Try to extract a readable version from the API data
                        readable_api_version = None
                        
                        # Check if version field contains a readable version
                        if version and version != 'Unknown' and not (str(version).isdigit() and len(str(version)) >= 8):
                            readable_api_version = str(version)
                        
                        # Also check product-level version info
                        product_version = data.get('version', None)
                        if product_version and not (str(product_version).isdigit() and len(str(product_version)) >= 8):
                            readable_api_version = str(product_version)
                        
                        # Extract tags information from product data
                        tags_info = self.extract_tags_from_data(data, gog_id)
                        
                        self.log_message.emit(f"   📋 Total builds available: {len(builds)}, selected build: {build_id}")
                        
                        if build_id and str(build_id).isdigit() and len(str(build_id)) >= 8:
                            latest_version = str(build_id)
                        else:
                            latest_version = str(gog_id)
                        
                        # Fetch changelog from GOGDB release notes
                        changelog = self.fetch_changelog_from_gogdb(gog_id)
                        if not changelog:
                            changelog = f"Build ID: {build_id}"
                            if version and version != 'Unknown':
                                changelog += f"\nVersion: {version}"
                            
                            # Add OS information
                            build_os = latest_build.get('os', 'Unknown')
                            if build_os != 'Unknown':
                                changelog += f"\nPlatform: {build_os}"
                            
                            # For DLCs, mention they share the base game's build ID
                            if is_dlc:
                                changelog += f"\n\nNote: This DLC/Expansion shares the build ID with the base game '{base_game_name}'"
                        
                        return {
                            'latest_version': latest_version,
                            'changelog': changelog,
                            'build_id': build_id,
                            'tags': tags_info,
                            'source': 'gogdb.org',
                            'base_game': base_game_name if is_dlc else game_name,
                            'readable_version': readable_api_version  # Add the readable version if found
                        }
                    else:
                        self.log_message.emit(f"   ⚠️ GOGDB API returned no builds for GOG ID {gog_id}")
                else:
                    self.log_message.emit(f"   ❌ GOGDB API returned HTTP {response.status}")
                    
        except urllib.error.HTTPError as e:
            self.log_message.emit(f"   ❌ GOGDB API HTTP Error {e.code}: {e.reason}")
            if e.code == 404:
                self.log_message.emit(f"   ℹ️ GOG ID {gog_id} not found in GOGDB database")
        except urllib.error.URLError as e:
            self.log_message.emit(f"   ❌ GOGDB API Network Error: {e.reason}")
            # Signal network issue detected
            if hasattr(self, 'network_error_detected'):
                self.network_error_detected.emit()
        except Exception as e:
            self.log_message.emit(f"   ❌ GOGDB API Unexpected Error: {str(e)}")
        
        return None
    
    def get_current_os(self):
        """Detect the current operating system"""
        import platform
        system = platform.system().lower()
        
        if system == 'windows':
            return 'windows'
        elif system == 'darwin':
            return 'osx'  # GOG/GOGDB typically uses 'osx' for macOS
        elif system == 'linux':
            return 'linux'
        else:
            return 'windows'  # Default fallback to Windows
    
    def filter_builds_by_os(self, builds, target_os):
        """Filter builds by operating system"""
        filtered_builds = []
        
        for build in builds:
            # Check various possible OS field names in the build data
            build_os = None
            
            # Try different field names that might contain OS information
            for os_field in ['os', 'platform', 'operating_system', 'system']:
                if os_field in build:
                    build_os = str(build[os_field]).lower()
                    break
            
            # If no OS field found, check if there are OS-specific files or installers
            if not build_os and 'files' in build:
                files = build.get('files', [])
                for file_info in files:
                    if isinstance(file_info, dict):
                        file_os = file_info.get('os', '').lower()
                        if file_os:
                            build_os = file_os
                            break
            
            # Match OS with some flexibility for naming variations
            if build_os:
                if target_os == 'windows' and any(win_variant in build_os for win_variant in ['windows', 'win', 'pc']):
                    filtered_builds.append(build)
                elif target_os == 'osx' and any(mac_variant in build_os for mac_variant in ['osx', 'mac', 'macos', 'darwin']):
                    filtered_builds.append(build)
                elif target_os == 'linux' and 'linux' in build_os:
                    filtered_builds.append(build)
        
        return filtered_builds
    
    def extract_tags_from_data(self, product_data, gog_id):
        """Extract tags information from GOGDB product data"""
        try:
            tags = []
            
            # Get tags from product data
            if 'tags' in product_data:
                tag_list = product_data['tags']
                if isinstance(tag_list, list):
                    # Take up to 3 most relevant tags
                    relevant_tags = []
                    for tag in tag_list[:5]:  # Look at first 5 tags
                        if isinstance(tag, dict):
                            tag_name = tag.get('name', '')
                        else:
                            tag_name = str(tag)
                        
                        # Filter for relevant tags
                        if tag_name and not any(skip in tag_name.lower() for skip in ['windows', 'english', 'offline']):
                            relevant_tags.append(tag_name)
                            if len(relevant_tags) >= 3:
                                break
                    
                    tags = relevant_tags
            
            # Get features as additional tags
            if 'features' in product_data:
                features = product_data['features']
                if isinstance(features, list):
                    for feature in features[:2]:  # Take up to 2 features
                        if isinstance(feature, dict):
                            feature_name = feature.get('name', '')
                            if feature_name and len(feature_name) < 15:
                                tags.append(f"⭐{feature_name}")
                        elif isinstance(feature, str) and len(feature) < 15:
                            tags.append(f"⭐{feature}")
            
            # Format tags for display
            if tags:
                return " • ".join(tags[:3])  # Limit to 3 tags
            else:
                return "🎮"  # Just the gaming icon if no tags
                
        except Exception as e:
            self.log_message.emit(f"   ⚠️ Could not extract tags: {str(e)}")
            return "🎮"
    
    def fetch_changelog_from_gogdb(self, gog_id):
        """Fetch changelog from GOGDB release notes page"""
        try:
            # Try to fetch release notes from GOGDB
            changelog_url = f"https://www.gogdb.org/product/{gog_id}/releasenotes"
            headers = {
                'User-Agent': 'GOG-Games-Build-ID-Checker/1.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }
            
            request = urllib.request.Request(changelog_url, headers=headers)
            
            with urllib.request.urlopen(request, timeout=15) as response:
                if response.status == 200:
                    html_content = response.read().decode('utf-8', errors='ignore')
                    
                    # Parse HTML to extract release notes
                    changelog = self.parse_release_notes_html(html_content)
                    if changelog:
                        return f"📄 Release Notes from GOGDB:\n\n{changelog}"
                    
        except Exception as e:
            self.log_message.emit(f"   ⚠️ Could not fetch changelog from GOGDB: {str(e)}")
        
        return None
    
    def parse_release_notes_html(self, html_content):
        """Parse HTML content to extract release notes"""
        try:
            import re
            
            # Look for release notes content - this is a simplified parser
            # Look for common patterns in GOGDB release notes
            
            # Pattern 1: Look for release notes section
            release_pattern = r'<div[^>]*class="[^"]*release[^"]*"[^>]*>(.*?)</div>'
            matches = re.findall(release_pattern, html_content, re.DOTALL | re.IGNORECASE)
            
            if matches:
                # Clean up HTML tags and extract text
                changelog_text = ""
                for match in matches[:5]:  # Limit to first 5 releases
                    # Remove HTML tags
                    clean_text = re.sub(r'<[^>]+>', '', match)
                    # Clean up whitespace
                    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                    if clean_text and len(clean_text) > 10:
                        changelog_text += clean_text + "\n\n"
                
                if changelog_text:
                    return changelog_text.strip()
            
            # Pattern 2: Look for version information
            version_pattern = r'Version\s+([0-9\.]+)[^<]*([^<]*(?:changelog|changes|notes|update)[^<]*)'
            version_matches = re.findall(version_pattern, html_content, re.DOTALL | re.IGNORECASE)
            
            if version_matches:
                changelog_text = ""
                for version, notes in version_matches[:3]:  # Limit to first 3 versions
                    clean_notes = re.sub(r'<[^>]+>', '', notes)
                    clean_notes = re.sub(r'\s+', ' ', clean_notes).strip()
                    if clean_notes:
                        changelog_text += f"Version {version}: {clean_notes}\n\n"
                
                if changelog_text:
                    return changelog_text.strip()
            
            # Pattern 3: Look for any meaningful content about updates
            content_pattern = r'<p[^>]*>(.*?(?:update|change|fix|add|improve|release).*?)</p>'
            content_matches = re.findall(content_pattern, html_content, re.DOTALL | re.IGNORECASE)
            
            if content_matches:
                changelog_text = ""
                for match in content_matches[:5]:  # Limit to first 5 paragraphs
                    clean_text = re.sub(r'<[^>]+>', '', match)
                    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                    if clean_text and len(clean_text) > 20:
                        changelog_text += "• " + clean_text + "\n"
                
                if changelog_text:
                    return changelog_text.strip()
            
            # Fallback: extract first meaningful paragraph
            paragraph_pattern = r'<p[^>]*>([^<]{50,})</p>'
            para_matches = re.findall(paragraph_pattern, html_content)
            
            if para_matches:
                first_para = para_matches[0]
                clean_text = re.sub(r'\s+', ' ', first_para).strip()
                if len(clean_text) > 30:
                    return f"Release Information: {clean_text}"
            
            return None
            
        except Exception as e:
            return None 


class MainWindow(QMainWindow):
    """Main Qt6 window for the GOG Games Build ID Checker"""
    
    def __init__(self):
        super().__init__()
        self.installed_games = []
        self.scan_thread = None
        self.update_thread = None
        self.app_update_thread = None
        
        # Progress tracking
        self.progress_start_time = None
        self.progress_total_items = 0
        self.progress_completed_items = 0
        self.current_operation = "idle"  # Track current operation phase
        
        # Font size management
        self.settings = QSettings("GOGTools", "BuildIDChecker")
        self.base_font_size = int(self.settings.value("font_size", 13))  # Increased default from 11 to 13
        self.current_font_size = self.base_font_size
        
        # Theme management - check if user wants to follow system theme
        follow_system = self.settings.value("follow_system_theme", True, type=bool)
        if follow_system:
            self.current_theme = self.detect_system_theme()
        else:
            self.current_theme = self.settings.value("theme", "dark")
        
        self.init_ui()
        self.create_menu_bar()
        self.apply_theme(self.current_theme)  # Apply saved theme
        self.apply_font_sizes()
        self.setup_shortcuts()
        # Update theme menu checks after everything is initialized
        if hasattr(self, 'follow_system_action'):
            self.update_theme_menu_checks()
        
        # Check for app updates on startup (if enabled)
        check_updates_on_startup = self.settings.value("check_updates_on_startup", True, type=bool)
        if check_updates_on_startup:
            # Delay the update check by 2 seconds to let the UI fully load
            QTimer.singleShot(2000, self.check_app_updates_silent)
        
        self.auto_scan()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("GOG Games Build ID Checker")
        
        # Set window icon
        try:
            if os.path.exists("icon.ico"):
                self.setWindowIcon(QIcon("icon.ico"))
        except Exception as e:
            print(f"Could not load window icon: {e}")
        
        self.setGeometry(100, 100, 1400, 900)
        self.setMinimumSize(1200, 700)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Header section
        self.create_header(main_layout)
        
        # Control buttons
        self.create_controls(main_layout)
        
        # Main content area with splitter
        self.create_main_content(main_layout)
        
        # Status bar
        self.create_status_bar()
    
    def create_header(self, parent_layout):
        """Create the header section"""
        header_layout = QVBoxLayout()
        
        # Main title
        title_label = QLabel("GOG Games Build ID Checker")
        title_font = QFont("Segoe UI", 24, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #3498DB; margin: 10px 0;")
        
        # Subtitle
        subtitle_label = QLabel("Compare installed game build IDs with latest versions from GOG APIs")
        subtitle_font = QFont("Segoe UI", 12)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("color: #BDC3C7; margin-bottom: 15px;")
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        
        parent_layout.addLayout(header_layout)
    
    def create_controls(self, parent_layout):
        """Create the control buttons section"""
        controls_frame = QFrame()
        controls_frame.setFrameStyle(QFrame.StyledPanel)
        # Store reference for theme updates
        self.controls_frame = controls_frame
        
        controls_frame.setStyleSheet("""
            QFrame {
                background-color: #34495E;
                border: 1px solid #5D6D7E;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        controls_layout = QVBoxLayout(controls_frame)
        controls_layout.setSpacing(10)
        
        # First row: Main buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        # Scan button
        self.scan_button = QPushButton("🔍 Scan Games")
        self.scan_button.clicked.connect(self.scan_games)
        
        # Check updates button
        self.update_button = QPushButton("🔄 Check Updates")
        self.update_button.clicked.connect(self.check_updates)
        self.update_button.setEnabled(False)
        
        # Refresh button
        self.refresh_button = QPushButton("🔄 Refresh")
        self.refresh_button.clicked.connect(self.refresh_all)
        
        # Open GOG Galaxy button
        self.galaxy_button = QPushButton("🎮 Open GOG Galaxy")
        self.galaxy_button.clicked.connect(self.open_gog_galaxy)
        
        # Help button
        self.help_button = QPushButton("❓ Help")
        self.help_button.clicked.connect(self.show_help)
        
        # Style buttons (will be updated by theme)
        self.button_style_template = """
            QPushButton {{
                background-color: {accent_blue};
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 12px;
                font-weight: bold;
                min-width: 120px;
            }}
            QPushButton:hover {{
                background-color: {accent_hover};
            }}
            QPushButton:pressed {{
                background-color: {accent_pressed};
            }}
            QPushButton:disabled {{
                background-color: #7F8C8D;
                color: #BDC3C7;
            }}
        """
        
        # Apply initial button style (will be updated by theme)
        button_style = self.button_style_template.format(
            accent_blue="#3498DB",
            accent_hover="#2980B9", 
            accent_pressed="#21618C"
        )
        
        for button in [self.scan_button, self.update_button, self.refresh_button, self.galaxy_button, self.help_button]:
            button.setStyleSheet(button_style)
        
        # Add buttons to first row
        buttons_layout.addWidget(self.scan_button)
        buttons_layout.addWidget(self.update_button)
        buttons_layout.addWidget(self.refresh_button)
        buttons_layout.addWidget(self.galaxy_button)
        buttons_layout.addWidget(self.help_button)
        buttons_layout.addStretch()
        
        # Statistics labels
        self.stats_label = QLabel("Ready to scan")
        self.stats_label.setStyleSheet("color: #ECF0F1; font-size: 12px; font-weight: bold;")
        buttons_layout.addWidget(self.stats_label)
        
        # Second row: Deep scan checkbox and options
        options_layout = QHBoxLayout()
        options_layout.setSpacing(10)
        
        # Deep scan checkbox
        self.deep_scan_checkbox = QCheckBox("🔍 Deep Scan (slower but finds more games)")
        self.deep_scan_checkbox.setStyleSheet("""
            QCheckBox {
                color: #ECF0F1;
                font-size: 11px;
                padding: 5px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #5D6D7E;
                border-radius: 3px;
                background-color: #34495E;
            }
            QCheckBox::indicator:checked {
                background-color: #3498DB;
                border-color: #2980B9;
            }
            QCheckBox::indicator:checked:hover {
                background-color: #2980B9;
            }
        """)
        self.deep_scan_checkbox.setToolTip(
            "Deep Scan searches all common drive letters and game directories.\n"
            "This takes longer but finds games in non-standard locations.\n"
            "Quick Scan only checks the most common GOG game directories."
        )
        
        options_layout.addWidget(self.deep_scan_checkbox)
        options_layout.addStretch()
        
        # Add both rows to the main layout
        controls_layout.addLayout(buttons_layout)
        controls_layout.addLayout(options_layout)
        
        parent_layout.addWidget(controls_frame)
    
    def create_main_content(self, parent_layout):
        """Create the main content area with games table and tabs"""
        # Main splitter
        main_splitter = QSplitter(Qt.Vertical)
        main_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #5D6D7E;
                height: 3px;
            }
        """)
        
        # Top section: Games table
        games_widget = self.create_games_table()
        main_splitter.addWidget(games_widget)
        
        # Bottom section: Tabs
        tabs_widget = self.create_tabs()
        main_splitter.addWidget(tabs_widget)
        
        # Set splitter proportions
        main_splitter.setStretchFactor(0, 2)  # Games table gets more space
        main_splitter.setStretchFactor(1, 1)  # Tabs get less space
        
        parent_layout.addWidget(main_splitter)
    
    def create_games_table(self):
        """Create the games table widget"""
        # Container frame
        table_frame = QFrame()
        table_frame.setFrameStyle(QFrame.StyledPanel)
        # Store reference for theme updates
        self.table_frame = table_frame
        
        table_frame.setStyleSheet("""
            QFrame {
                background-color: #2C3E50;
                border: 1px solid #5D6D7E;
                border-radius: 8px;
            }
        """)
        
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(10, 10, 10, 10)
        
        # Table header
        table_header = QLabel("📋 Installed GOG Games")
        table_header.setStyleSheet("color: #3498DB; font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        table_layout.addWidget(table_header)
        
        # Games tree widget
        self.games_tree = QTreeWidget()
        self.games_tree.setHeaderLabels([
            "Game Name", 
            "Installed Version",
            "Installed Build/Version", 
            "Latest Build/Version", 
            "Status", 
            "Size", 
            "Tags",
            "Install Path",
            "📚 Wiki"
        ])
        
        # Configure tree widget
        self.games_tree.setAlternatingRowColors(True)
        self.games_tree.setRootIsDecorated(False)
        self.games_tree.setSelectionBehavior(QTreeWidget.SelectRows)
        self.games_tree.setSelectionMode(QTreeWidget.SingleSelection)
        self.games_tree.setSortingEnabled(True)
        
        # Connect item click for status column links only
        self.games_tree.itemClicked.connect(self.on_item_clicked)
        
        # Enable horizontal scrollbar and auto-resize columns to content
        header = self.games_tree.header()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)  # Auto-size all columns to content
        header.setStretchLastSection(False)  # Don't stretch last section
        
        # Enable horizontal scrollbar when needed
        self.games_tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Style the tree widget
        self.games_tree.setStyleSheet("""
            QTreeWidget {
                background-color: #34495E;
                color: #ECF0F1;
                border: 1px solid #5D6D7E;
                border-radius: 5px;
                font-size: 11px;
                gridline-color: #5D6D7E;
                selection-background-color: #3498DB;
            }
            QTreeWidget::item {
                padding: 8px;
                border-bottom: 1px solid #5D6D7E;
            }
            QTreeWidget::item:hover {
                background-color: #4A5F7A;
            }
            QTreeWidget::item:selected {
                background-color: #3498DB;
                color: white;
            }
            QTreeWidget::item:selected:hover {
                background-color: #2980B9;
                color: white;
            }
            QTreeWidget::item:selected:!active {
                background-color: #2980B9;
                color: white;
            }
            QHeaderView::section {
                background-color: #2C3E50;
                color: #3498DB;
                border: 1px solid #5D6D7E;
                padding: 8px;
                font-weight: bold;
            }
        """)
        
        # Set mouse cursor to pointer when hovering over status column
        self.games_tree.setMouseTracking(True)
        self.games_tree.entered.connect(self.on_mouse_enter_item)
        
        # Connect selection signal
        self.games_tree.itemSelectionChanged.connect(self.on_game_selected)
        
        table_layout.addWidget(self.games_tree)
        
        return table_frame
    
    def create_tabs(self):
        """Create the tabbed interface for logs and changelog"""
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #5D6D7E;
                background-color: #2C3E50;
                border-radius: 5px;
            }
            QTabBar::tab {
                background-color: #34495E;
                color: #ECF0F1;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #3498DB;
                color: white;
            }
            QTabBar::tab:hover {
                background-color: #4A5F7A;
            }
        """)
        
        # Scan Log tab
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1C2833;
                color: #ECF0F1;
                border: none;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
                padding: 10px;
            }
        """)
        self.tab_widget.addTab(self.log_text, "📋 Scan Log")
        
        # Changelog tab
        self.changelog_text = QTextBrowser()
        self.changelog_text.setReadOnly(True)
        self.changelog_text.setOpenExternalLinks(True)  # Enable clickable links
        self.changelog_text.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse | Qt.LinksAccessibleByKeyboard
        )
        self.changelog_text.setStyleSheet("""
            QTextBrowser {
                background-color: #1C2833;
                color: #ECF0F1;
                border: none;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
                padding: 10px;
            }
            QTextBrowser a {
                color: #3498DB;
                text-decoration: underline;
            }
            QTextBrowser a:hover {
                color: #5DADE2;
            }
        """)
        self.changelog_text.setHtml("Select a game to view changelog information")
        self.tab_widget.addTab(self.changelog_text, "📄 Changelog")
        
        return self.tab_widget
    
    def create_status_bar(self):
        """Create the status bar"""
        self.status_bar = self.statusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #34495E;
                color: #ECF0F1;
                border-top: 1px solid #5D6D7E;
                font-size: 11px;
            }
        """)
        
        # Create progress bar for the bottom right
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setMaximumHeight(16)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #5D6D7E;
                border-radius: 3px;
                background-color: #2C3E50;
                text-align: center;
                font-size: 10px;
                color: #ECF0F1;
            }
            QProgressBar::chunk {
                background-color: #3498DB;
                border-radius: 2px;
            }
        """)
        
        # Create network connectivity indicator
        self.network_indicator = QLabel()
        self.network_indicator.setFixedSize(16, 16)
        self.network_indicator.setToolTip("Network connectivity status - Click to test")
        self.network_indicator.setCursor(Qt.PointingHandCursor)
        self.network_indicator.setStyleSheet("""
            QLabel {
                border: 1px solid #5D6D7E;
                border-radius: 8px;
                background-color: #7F8C8D;
                margin: 2px;
            }
        """)
        
        # Make network indicator clickable
        self.network_indicator.mousePressEvent = self.on_network_indicator_clicked
        
        # Add widgets to status bar (right side)
        self.status_bar.addPermanentWidget(self.network_indicator)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        # Start network monitoring
        self.check_network_connectivity()
        
        # Set up network check timer
        self.network_timer = QTimer()
        self.network_timer.timeout.connect(self.check_network_connectivity)
        self.network_timer.start(30000)  # Check every 30 seconds
        
        self.status_bar.showMessage("Ready")
    
    def create_menu_bar(self):
        """Create menu bar with font size controls and help"""
        menubar = self.menuBar()
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        # Font size submenu
        font_menu = view_menu.addMenu("Font Size")
        
        # Increase font size
        increase_action = QAction("&Increase Font Size", self)
        increase_action.setShortcut(QKeySequence.ZoomIn)
        increase_action.triggered.connect(self.increase_font_size)
        font_menu.addAction(increase_action)
        
        # Decrease font size
        decrease_action = QAction("&Decrease Font Size", self)
        decrease_action.setShortcut(QKeySequence.ZoomOut)
        decrease_action.triggered.connect(self.decrease_font_size)
        font_menu.addAction(decrease_action)
        
        # Reset font size
        reset_action = QAction("&Reset Font Size", self)
        reset_action.setShortcut(QKeySequence("Ctrl+0"))
        reset_action.triggered.connect(self.reset_font_size)
        font_menu.addAction(reset_action)
        
        font_menu.addSeparator()
        
        # Preset font sizes
        small_action = QAction("&Small (10px)", self)
        small_action.triggered.connect(lambda: self.set_font_size(10))
        font_menu.addAction(small_action)
        
        normal_action = QAction("&Normal (13px)", self)
        normal_action.triggered.connect(lambda: self.set_font_size(13))
        font_menu.addAction(normal_action)
        
        large_action = QAction("&Large (14px)", self)
        large_action.triggered.connect(lambda: self.set_font_size(14))
        font_menu.addAction(large_action)
        
        extra_large_action = QAction("&Extra Large (18px)", self)
        extra_large_action.triggered.connect(lambda: self.set_font_size(18))
        font_menu.addAction(extra_large_action)
        
        # Theme submenu in View menu
        view_menu.addSeparator()
        theme_menu = view_menu.addMenu("Theme")
        
        # Follow system theme
        follow_system_action = QAction("🔄 &Follow System Theme", self)
        follow_system_action.setCheckable(True)
        follow_system_action.triggered.connect(self.enable_system_theme_following)
        theme_menu.addAction(follow_system_action)
        
        theme_menu.addSeparator()
        
        # Dark theme
        dark_action = QAction("🌙 &Dark Theme", self)
        dark_action.setCheckable(True)
        dark_action.triggered.connect(lambda: self.set_theme("dark"))
        theme_menu.addAction(dark_action)
        
        # Light theme
        light_action = QAction("☀️ &Light Theme", self)
        light_action.setCheckable(True)
        light_action.triggered.connect(lambda: self.set_theme("light"))
        theme_menu.addAction(light_action)
        
        # Store theme actions for later reference
        self.follow_system_action = follow_system_action
        self.dark_theme_action = dark_action
        self.light_theme_action = light_action
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        # Help action
        help_action = QAction("&Help", self)
        help_action.setShortcut(QKeySequence.HelpContents)
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)
        
        # Status Guide action
        status_guide_action = QAction("&Status Guide", self)
        status_guide_action.triggered.connect(self.show_status_guide)
        help_menu.addAction(status_guide_action)
        
        help_menu.addSeparator()
        
        # Check for Updates action
        update_action = QAction("🔄 &Check for Updates", self)
        update_action.triggered.connect(self.check_app_updates)
        help_menu.addAction(update_action)
        
        # Auto-check updates toggle
        auto_update_action = QAction("🔄 &Auto-check Updates on Startup", self)
        auto_update_action.setCheckable(True)
        auto_update_action.setChecked(self.settings.value("check_updates_on_startup", True, type=bool))
        auto_update_action.triggered.connect(self.toggle_auto_update_check)
        help_menu.addAction(auto_update_action)
        
        help_menu.addSeparator()
        
        # About action
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        # Style the menu bar
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #34495E;
                color: #ECF0F1;
                border-bottom: 1px solid #5D6D7E;
                padding: 2px;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QMenuBar::item:selected {
                background-color: #3498DB;
            }
            QMenu {
                background-color: #2C3E50;
                color: #ECF0F1;
                border: 1px solid #5D6D7E;
            }
            QMenu::item {
                padding: 5px 20px;
            }
            QMenu::item:selected {
                background-color: #3498DB;
            }
            QMenu::separator {
                height: 1px;
                background-color: #5D6D7E;
                margin: 2px 0;
            }
        """)
    
    def increase_font_size(self):
        """Increase font size by 1px"""
        if self.current_font_size < 24:  # Maximum font size
            self.current_font_size += 1
            self.apply_font_sizes()
            self.save_font_settings()
            self.status_bar.showMessage(f"Font size increased to {self.current_font_size}px", 2000)
    
    def decrease_font_size(self):
        """Decrease font size by 1px"""
        if self.current_font_size > 8:  # Minimum font size
            self.current_font_size -= 1
            self.apply_font_sizes()
            self.save_font_settings()
            self.status_bar.showMessage(f"Font size decreased to {self.current_font_size}px", 2000)
    
    def reset_font_size(self):
        """Reset font size to default"""
        self.current_font_size = 13  # Increased default from 11 to 13
        self.apply_font_sizes()
        self.save_font_settings()
        self.status_bar.showMessage("Font size reset to default (13px)", 2000)
    
    def set_font_size(self, size):
        """Set specific font size"""
        self.current_font_size = size
        self.apply_font_sizes()
        self.save_font_settings()
        self.status_bar.showMessage(f"Font size set to {size}px", 2000)
    
    def apply_font_sizes(self):
        """Apply current font size to all relevant widgets"""
        try:
            # Update table font
            if hasattr(self, 'games_tree'):
                font = self.games_tree.font()
                font.setPointSize(self.current_font_size)
                self.games_tree.setFont(font)
                
                # Update header font
                header = self.games_tree.header()
                header_font = header.font()
                header_font.setPointSize(self.current_font_size)
                header.setFont(header_font)
            
            # Update log text font
            if hasattr(self, 'log_text'):
                log_font = self.log_text.font()
                log_font.setPointSize(self.current_font_size)
                self.log_text.setFont(log_font)
            
            # Update changelog text font
            if hasattr(self, 'changelog_text'):
                changelog_font = self.changelog_text.font()
                changelog_font.setPointSize(self.current_font_size)
                self.changelog_text.setFont(changelog_font)
            
            # Update status bar font
            if hasattr(self, 'status_bar'):
                status_font = self.status_bar.font()
                status_font.setPointSize(self.current_font_size - 1)  # Slightly smaller
                self.status_bar.setFont(status_font)
            
            # Update stats label font
            if hasattr(self, 'stats_label'):
                stats_font = self.stats_label.font()
                stats_font.setPointSize(self.current_font_size)
                self.stats_label.setFont(stats_font)
            
        except Exception as e:
            print(f"Error applying font sizes: {e}")
    
    def save_font_settings(self):
        """Save font size settings"""
        self.settings.setValue("font_size", self.current_font_size)
    
    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # F1 for help
        help_shortcut = QKeySequence("F1")
        help_action = QAction(self)
        help_action.setShortcut(help_shortcut)
        help_action.triggered.connect(self.show_help)
        self.addAction(help_action)
    
    def show_help(self):
        """Show the main help dialog"""
        help_dialog = QMessageBox(self)
        help_dialog.setWindowTitle("GOG Games Build ID Checker - Help")
        help_dialog.setIcon(QMessageBox.Information)
        
        help_text = """
<h3>🎮 GOG Games Build ID Checker - Help</h3>

<h4>📋 Overview</h4>
<p>This application scans your installed GOG games and checks for available updates by comparing build IDs.</p>

<h4>🚀 How to Use</h4>
<ol>
<li><b>Scan Games:</b> Click "Scan Games" to detect installed GOG games</li>
<li><b>Deep Scan:</b> Check the "Deep Scan" option for comprehensive searching (slower but finds more games)</li>
<li><b>Check Updates:</b> Click "Check Updates" to compare with latest versions</li>
<li><b>View Details:</b> Click on any game to see changelog information</li>
<li><b>Open Folders:</b> Click on install paths to open game folders</li>
</ol>

<h4>🔍 Scan Modes</h4>
<ul>
<li><b>Quick Scan:</b> Searches common GOG installation directories (fast, ~5-10 seconds)</li>
<li><b>Deep Scan:</b> Searches all drives and possible game directories (thorough, may take several minutes)</li>
</ul>
<p><i>Use Deep Scan if Quick Scan doesn't find all your games, especially if you have games installed in custom locations.</i></p>

<h4>📊 Column Information</h4>
<ul>
<li><b>Game Name:</b> Name of the installed game</li>
<li><b>Installed Build/Version:</b> Currently installed version on your system</li>
<li><b>Latest Build/Version:</b> Latest available version from online databases</li>
<li><b>Status:</b> Update status (see Status Guide for details)</li>
<li><b>Size:</b> Installation size of the game</li>
<li><b>Install Path:</b> Directory where the game is installed</li>
</ul>

<h4>⌨️ Keyboard Shortcuts</h4>
<ul>
<li><b>Ctrl++:</b> Increase font size</li>
<li><b>Ctrl+-:</b> Decrease font size</li>
<li><b>Ctrl+0:</b> Reset font size</li>
<li><b>F1:</b> Show this help</li>
</ul>

<h4>💡 Tips</h4>
<ul>
<li>Check the "Scan Log" tab for detailed information about the scanning process</li>
<li>Use "Refresh All" to re-scan and check for updates in one step</li>
<li>Status messages provide specific information about each game's update status</li>
</ul>
        """
        
        help_dialog.setText(help_text)
        help_dialog.exec()
    
    def show_status_guide(self):
        """Show the status guide dialog with detailed explanations"""
        status_dialog = QMessageBox(self)
        status_dialog.setWindowTitle("Status Guide - Build ID Reference")
        status_dialog.setIcon(QMessageBox.Information)
        
        status_text = """
<h3>📊 Status Messages Guide</h3>

<h4>✅ Positive Statuses</h4>
<table border="1" cellpadding="5">
<tr><td><b>Up to Date</b></td><td>✅ Your installed version matches the latest available version</td></tr>
<tr><td><b>DLC - Base Game Reference</b></td><td>📦 DLC/Expansion using the base game's build ID (normal behavior)</td></tr>
<tr><td><b>Local Reference Only</b></td><td>📋 Using your installed build ID as reference (API unavailable)</td></tr>
</table>

<h4>🔄 Update Statuses</h4>
<table border="1" cellpadding="5">
<tr><td><b>Update Available</b></td><td>🔄 A newer version is available for download</td></tr>
<tr><td><b>Newer Version Installed</b></td><td>⬆️ You have a newer version than what's officially available</td></tr>
<tr><td><b>Different Version</b></td><td>🔄 Version differs but numeric comparison not possible</td></tr>
</table>

<h4>❌ Issue Statuses</h4>
<table border="1" cellpadding="5">
<tr><td><b>Cannot Check - No Installed Version</b></td><td>❌ Could not detect your installed version</td></tr>
<tr><td><b>Cannot Check - No Latest Version</b></td><td>❌ Could not retrieve latest version from online</td></tr>
<tr><td><b>Not in Database</b></td><td>❌ Game not found in online databases</td></tr>
</table>

<h4>📦 Special Cases</h4>
<p><b>DLC/Expansions:</b> Many DLCs share the same build ID as their base game. This is normal behavior and not an error.</p>

<p><b>Local Reference:</b> When online databases are unavailable, the app uses your installed build ID as a reference point.</p>

<p><b>Build ID vs Version:</b> Build IDs are numeric identifiers that provide more precise version tracking than traditional version strings.</p>

<h4>💡 Troubleshooting</h4>
<ul>
<li>If many games show "Not in Database", check your internet connection</li>
<li>DLC entries showing "DLC - Base Game Reference" is expected behavior</li>
<li>Check the Scan Log tab for detailed error messages</li>
</ul>
        """
        
        status_dialog.setText(status_text)
        status_dialog.exec()
    
    def show_about(self):
        """Show the about dialog"""
        about_dialog = QMessageBox(self)
        about_dialog.setWindowTitle("About GOG Games Build ID Checker")
        about_dialog.setIcon(QMessageBox.Information)
        
        about_text = f"""
<h3>🎮 GOG Games Build ID Checker</h3>

<p><b>Version:</b> {APP_VERSION}</p>
<p><b>Description:</b> A Qt6-based application for checking GOG game updates using build IDs</p>

<h4>✨ Features</h4>
<ul>
<li>Automatic GOG game detection</li>
<li>Build ID comparison for precise update checking</li>
<li>DLC-aware processing</li>
<li>Comprehensive status reporting</li>
<li>Dark theme interface</li>
<li>Detailed logging and debugging</li>
</ul>

<h4>🔧 Technologies</h4>
<ul>
<li>Python 3.13</li>
<li>PySide6 (Qt6)</li>
<li>GOG metadata parsing</li>
<li>GOGDB API integration</li>
</ul>

<h4>📝 Recent Updates</h4>
<ul>
<li>✅ Fixed DLC build ID handling</li>
<li>✅ Added local reference fallbacks</li>
<li>✅ Improved status messages</li>
<li>✅ Enhanced error reporting</li>
<li>✅ Added comprehensive help system</li>
</ul>

<p><i>Developed to help GOG users stay up-to-date with their game collection.</i></p>
        """
        
        about_dialog.setText(about_text)
        about_dialog.exec()
    
    def check_app_updates(self):
        """Check for application updates from GitHub"""
        if self.app_update_thread and self.app_update_thread.isRunning():
            self.log_message("Update check already in progress...")
            return
        
        self.log_message("🔄 Checking for application updates...")
        self.status_bar.showMessage("Checking for updates...")
        
        # Start update check thread
        self.app_update_thread = AppUpdateCheckThread()
        self.app_update_thread.update_checked.connect(self.on_app_update_checked)
        self.app_update_thread.start()
    
    def check_app_updates_silent(self):
        """Check for application updates silently (no UI feedback unless update found)"""
        if self.app_update_thread and self.app_update_thread.isRunning():
            return
        
        # Start update check thread
        self.app_update_thread = AppUpdateCheckThread()
        self.app_update_thread.update_checked.connect(self.on_app_update_checked_silent)
        self.app_update_thread.start()
    
    def on_app_update_checked_silent(self, result):
        """Handle the result of the silent app update check"""
        if 'error' in result:
            # Don't show errors for silent checks
            return
        
        current_version = result.get('current_version', APP_VERSION)
        latest_version = result.get('latest_version', 'Unknown')
        update_available = result.get('update_available', False)
        download_url = result.get('download_url', '')
        release_notes = result.get('release_notes', '')
        
        if update_available:
            # Only show notification if an update is available
            self.status_bar.showMessage(f"Update available: v{latest_version} (Check Help menu)")
            self.show_update_dialog(current_version, latest_version, download_url, release_notes)
    
    def on_app_update_checked(self, result):
        """Handle the result of the app update check"""
        if 'error' in result:
            self.log_message(f"❌ Update check failed: {result['error']}")
            self.status_bar.showMessage("Update check failed")
            
            # Show error dialog
            error_dialog = QMessageBox(self)
            error_dialog.setWindowTitle("Update Check Failed")
            error_dialog.setIcon(QMessageBox.Warning)
            error_dialog.setText(f"Failed to check for updates:\n{result['error']}")
            error_dialog.exec()
            return
        
        current_version = result.get('current_version', APP_VERSION)
        latest_version = result.get('latest_version', 'Unknown')
        update_available = result.get('update_available', False)
        download_url = result.get('download_url', '')
        release_notes = result.get('release_notes', '')
        
        self.log_message(f"✅ Current version: {current_version}")
        self.log_message(f"✅ Latest version: {latest_version}")
        
        if update_available:
            self.log_message("🎉 New version available!")
            self.status_bar.showMessage(f"Update available: v{latest_version}")
            self.show_update_dialog(current_version, latest_version, download_url, release_notes)
        else:
            self.log_message("✅ You have the latest version!")
            self.status_bar.showMessage("You have the latest version")
            
            # Show up-to-date dialog
            info_dialog = QMessageBox(self)
            info_dialog.setWindowTitle("No Updates Available")
            info_dialog.setIcon(QMessageBox.Information)
            info_dialog.setText(f"You are running the latest version ({current_version}).")
            info_dialog.exec()
    
    def show_update_dialog(self, current_version, latest_version, download_url, release_notes):
        """Show dialog when an update is available"""
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Update Available")
        dialog.setIcon(QMessageBox.Information)
        
        # Format release notes for display
        formatted_notes = release_notes.replace('\n', '<br>').replace('\r\n', '<br>')
        if len(formatted_notes) > 500:
            formatted_notes = formatted_notes[:500] + "..."
        
        update_text = f"""
<h3>🎉 New Version Available!</h3>

<p><b>Current Version:</b> {current_version}</p>
<p><b>Latest Version:</b> {latest_version}</p>

<h4>📝 Release Notes:</h4>
<p style="font-size: 11px; color: #666;">{formatted_notes}</p>

<p>Would you like to download the latest version?</p>
        """
        
        dialog.setText(update_text)
        dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        dialog.setDefaultButton(QMessageBox.Yes)
        
        result = dialog.exec()
        
        if result == QMessageBox.Yes and download_url:
            # Open download URL in default browser
            try:
                import webbrowser
                webbrowser.open(download_url)
                self.log_message(f"🌐 Opened download page: {download_url}")
            except Exception as e:
                self.log_message(f"❌ Failed to open download page: {e}")
                # Show URL in a dialog as fallback
                url_dialog = QMessageBox(self)
                url_dialog.setWindowTitle("Download URL")
                url_dialog.setIcon(QMessageBox.Information)
                url_dialog.setText(f"Please visit:\n{download_url}")
                url_dialog.exec()
    
    def toggle_auto_update_check(self):
        """Toggle automatic update checking on startup"""
        current_setting = self.settings.value("check_updates_on_startup", True, type=bool)
        new_setting = not current_setting
        self.settings.setValue("check_updates_on_startup", new_setting)
        
        status_msg = "enabled" if new_setting else "disabled"
        self.status_bar.showMessage(f"Auto-update check {status_msg}", 2000)
        self.log_message(f"✅ Auto-update check on startup {status_msg}")
    
    def set_theme(self, theme_name):
        """Set the application theme"""
        self.current_theme = theme_name
        self.apply_theme(theme_name)
        self.save_theme_settings()
        
        # Update menu checkmarks
        self.dark_theme_action.setChecked(theme_name == "dark")
        self.light_theme_action.setChecked(theme_name == "light")
        
        self.status_bar.showMessage(f"Switched to {theme_name} theme", 2000)
    
    def apply_theme(self, theme_name):
        """Apply the specified theme to the application"""
        if theme_name == "light":
            self.apply_light_theme()
        else:
            self.apply_dark_theme()
        
        # Update menu checkmarks
        if hasattr(self, 'dark_theme_action') and hasattr(self, 'light_theme_action'):
            self.dark_theme_action.setChecked(theme_name == "dark")
            self.light_theme_action.setChecked(theme_name == "light")
    
    def apply_dark_theme(self):
        """Apply dark theme to the application"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2C3E50;
                color: #ECF0F1;
            }
            QWidget {
                background-color: #2C3E50;
                color: #ECF0F1;
            }
            QLabel {
                color: #ECF0F1;
            }
        """)
        
        # Apply dark theme to menu bar specifically
        if hasattr(self, 'menuBar'):
            self.menuBar().setStyleSheet("""
                QMenuBar {
                    background-color: #34495E;
                    color: #ECF0F1;
                    border-bottom: 1px solid #5D6D7E;
                    padding: 2px;
                }
                QMenuBar::item {
                    background-color: transparent;
                    padding: 5px 10px;
                    border-radius: 3px;
                    color: #ECF0F1;
                }
                QMenuBar::item:selected {
                    background-color: #3498DB;
                    color: white;
                }
                QMenu {
                    background-color: #2C3E50;
                    color: #ECF0F1;
                    border: 1px solid #5D6D7E;
                }
                QMenu::item {
                    padding: 5px 20px;
                    color: #ECF0F1;
                }
                QMenu::item:selected {
                    background-color: #3498DB;
                    color: white;
                }
                QMenu::separator {
                    height: 1px;
                    background-color: #5D6D7E;
                    margin: 2px 0;
                }
            """)
        
        # Update existing styled components to dark theme
        self.update_component_themes("dark")
    
    def apply_light_theme(self):
        """Apply light theme to the application"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #FFFFFF;
                color: #1F2937;
            }
            QWidget {
                background-color: #FFFFFF;
                color: #1F2937;
            }
            QLabel {
                color: #1F2937;
            }
        """)
        
        # Apply light theme to menu bar specifically
        if hasattr(self, 'menuBar'):
            self.menuBar().setStyleSheet("""
                QMenuBar {
                    background-color: #F8F9FA;
                    color: #1F2937;
                    border-bottom: 1px solid #E5E7EB;
                    padding: 2px;
                }
                QMenuBar::item {
                    background-color: transparent;
                    padding: 5px 10px;
                    border-radius: 3px;
                    color: #1F2937;
                }
                QMenuBar::item:selected {
                    background-color: #E5E7EB;
                    color: #111827;
                }
                QMenu {
                    background-color: #FFFFFF;
                    color: #1F2937;
                    border: 1px solid #D1D5DB;
                }
                QMenu::item {
                    padding: 5px 20px;
                    color: #1F2937;
                }
                QMenu::item:selected {
                    background-color: #F3F4F6;
                    color: #111827;
                }
                QMenu::separator {
                    height: 1px;
                    background-color: #D1D5DB;
                    margin: 2px 0;
                }
            """)
        
        # Update existing styled components to light theme
        self.update_component_themes("light")
    
    def update_component_themes(self, theme):
        """Update individual component themes"""
        if theme == "dark":
            # Dark theme colors
            bg_primary = "#2C3E50"
            bg_secondary = "#34495E" 
            bg_tertiary = "#1C2833"
            text_primary = "#ECF0F1"
            text_secondary = "#BDC3C7"
            accent_blue = "#3498DB"
            accent_hover = "#2980B9"
            accent_pressed = "#21618C"
            border_color = "#5D6D7E"
            success_color = "#46, 204, 113"
            warning_color = "#241, 196, 15"
            error_color = "#231, 76, 60"
            table_bg = "#34495E"
        else:
            # Light theme colors - improved contrast and consistency
            bg_primary = "#FFFFFF"
            bg_secondary = "#F9FAFB"
            bg_tertiary = "#F3F4F6"
            text_primary = "#111827"
            text_secondary = "#6B7280"
            accent_blue = "#2563EB"
            accent_hover = "#1D4ED8"
            accent_pressed = "#1E40AF"
            border_color = "#D1D5DB"
            success_color = "#10, 185, 96"
            warning_color = "#217, 119, 6"
            error_color = "#185, 28, 28"
            table_bg = "#FFFFFF"
        
        # Update header
        if hasattr(self, 'title_label'):
            # This will be applied when components are recreated
            pass
        
        # Update games tree
        if hasattr(self, 'games_tree'):
            # Define alternating row colors based on theme
            if theme == "dark":
                alternate_base = "#34495E"  # Keep current dark alternating color
            else:
                alternate_base = "#F8FAFC"  # Very light gray for light theme alternating rows
            
            self.games_tree.setStyleSheet(f"""
                QTreeWidget {{
                    background-color: {table_bg};
                    color: {text_primary};
                    border: 1px solid {border_color};
                    border-radius: 5px;
                    font-size: 11px;
                    gridline-color: {border_color};
                    selection-background-color: {accent_blue};
                    alternate-background-color: {alternate_base};
                }}
                QTreeWidget::item {{
                    padding: 8px;
                    border-bottom: 1px solid {border_color};
                }}
                QTreeWidget::item:hover {{
                    background-color: {"#4A5F7A" if theme == "dark" else "#F3F4F6"};
                }}
                QTreeWidget::item:selected {{
                    background-color: {accent_blue};
                    color: white;
                }}
                QTreeWidget::item:selected:hover {{
                    background-color: {accent_hover};
                    color: white;
                }}
                QTreeWidget::item:selected:!active {{
                    background-color: {accent_hover};
                    color: white;
                }}
                QHeaderView::section {{
                    background-color: {bg_secondary};
                    color: {accent_blue};
                    border: 1px solid {border_color};
                    padding: 8px;
                    font-weight: bold;
                }}
            """)
        
        # Update tabs
        if hasattr(self, 'tab_widget'):
            self.tab_widget.setStyleSheet(f"""
                QTabWidget::pane {{
                    border: 1px solid {border_color};
                    background-color: {bg_secondary};
                    border-radius: 5px;
                }}
                QTabBar::tab {{
                    background-color: {bg_tertiary};
                    color: {text_primary};
                    padding: 10px 20px;
                    margin-right: 2px;
                    border-top-left-radius: 5px;
                    border-top-right-radius: 5px;
                    font-weight: bold;
                }}
                QTabBar::tab:selected {{
                    background-color: {accent_blue};
                    color: white;
                }}
                QTabBar::tab:hover {{
                    background-color: {"#4A5F7A" if theme == "dark" else "#F3F4F6"};
                }}
            """)
        
        # Update log text
        if hasattr(self, 'log_text'):
            self.log_text.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {bg_tertiary};
                    color: {text_primary};
                    border: none;
                    font-family: 'Consolas', 'Monaco', monospace;
                    font-size: 11px;
                    padding: 10px;
                }}
            """)
        
        # Update changelog text
        if hasattr(self, 'changelog_text'):
            self.changelog_text.setStyleSheet(f"""
                QTextBrowser {{
                    background-color: {bg_tertiary};
                    color: {text_primary};
                    border: none;
                    font-family: 'Segoe UI', sans-serif;
                    font-size: 11px;
                    padding: 10px;
                }}
                QTextBrowser a {{
                    color: {accent_blue};
                    text-decoration: underline;
                }}
                QTextBrowser a:hover {{
                    color: {accent_hover};
                }}
            """)
        
        # Update buttons
        if hasattr(self, 'button_style_template'):
            button_style = self.button_style_template.format(
                accent_blue=accent_blue,
                accent_hover=accent_hover,
                accent_pressed=accent_pressed
            )
            for button in [self.scan_button, self.update_button, self.refresh_button, self.galaxy_button, self.help_button]:
                if hasattr(self, button.objectName() or 'button'):
                    button.setStyleSheet(button_style)
        
        # Update controls frame
        if hasattr(self, 'controls_frame'):
            controls_style = f"""
                QFrame {{
                    background-color: {bg_secondary};
                    border: 1px solid {border_color};
                    border-radius: 8px;
                    padding: 10px;
                }}
            """
            self.controls_frame.setStyleSheet(controls_style)
        
        # Update table frame
        if hasattr(self, 'table_frame'):
            table_frame_style = f"""
                QFrame {{
                    background-color: {bg_secondary};
                    border: 1px solid {border_color};
                    border-radius: 8px;
                }}
            """
            self.table_frame.setStyleSheet(table_frame_style)
        
        # Update header labels
        if hasattr(self, 'title_label') or theme == "light":
            # Update title color
            pass  # Colors are updated via main stylesheet
        
        # Update deep scan checkbox theme
        if hasattr(self, 'deep_scan_checkbox'):
            checkbox_style = f"""
                QCheckBox {{
                    color: {text_primary};
                    font-size: 11px;
                    padding: 5px;
                }}
                QCheckBox::indicator {{
                    width: 16px;
                    height: 16px;
                    border: 1px solid {border_color};
                    border-radius: 3px;
                    background-color: {bg_secondary};
                }}
                QCheckBox::indicator:checked {{
                    background-color: {accent_blue};
                    border-color: {accent_hover};
                }}
                QCheckBox::indicator:checked:hover {{
                    background-color: {accent_hover};
                }}
            """
            self.deep_scan_checkbox.setStyleSheet(checkbox_style)
        
        # Update statistics label
        if hasattr(self, 'stats_label'):
            self.stats_label.setStyleSheet(f"color: {text_primary}; font-size: 12px; font-weight: bold;")
        
        # Update progress bar theme
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setStyleSheet(f"""
                QProgressBar {{
                    border: 1px solid {border_color};
                    border-radius: 3px;
                    background-color: {bg_tertiary};
                    text-align: center;
                    font-size: 10px;
                    color: {text_primary};
                }}
                QProgressBar::chunk {{
                    background-color: {accent_blue};
                    border-radius: 2px;
                }}
            """)
        
        # Update network indicator to match theme
        if hasattr(self, 'network_indicator'):
            # Trigger a network status recheck to apply theme colors
            QTimer.singleShot(100, self.check_network_connectivity)
        
        # Force redraw of games display to apply new colors
        if hasattr(self, 'installed_games') and self.installed_games:
            self.update_games_display()
    
    def detect_system_theme(self):
        """Detect Windows system theme (light/dark mode)"""
        try:
            import winreg
            
            # Check Windows 10/11 dark mode setting
            registry_path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_path)
            
            # AppsUseLightTheme: 0 = dark mode, 1 = light mode
            apps_use_light_theme, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            
            if apps_use_light_theme == 0:
                self.log_message("🌙 Auto-detected system dark theme")
                return "dark"
            else:
                self.log_message("☀️ Auto-detected system light theme")
                return "light"
                
        except Exception as e:
            self.log_message(f"⚠️ Could not detect system theme, defaulting to dark: {str(e)}")
            return "dark"
    
    def enable_system_theme_following(self):
        """Enable automatic system theme following"""
        self.settings.setValue("follow_system_theme", True)
        self.current_theme = self.detect_system_theme()
        self.apply_theme(self.current_theme)
        self.update_theme_menu_checks()
        self.log_message("🔄 Now following system theme automatically")
    
    def update_theme_menu_checks(self):
        """Update theme menu checkmarks based on current settings"""
        follow_system = self.settings.value("follow_system_theme", True, type=bool)
        
        self.follow_system_action.setChecked(follow_system)
        self.dark_theme_action.setChecked(not follow_system and self.current_theme == "dark")
        self.light_theme_action.setChecked(not follow_system and self.current_theme == "light")
    
    def save_theme_settings(self):
        """Save current theme to settings and disable system following"""
        self.settings.setValue("theme", self.current_theme)
        self.settings.setValue("follow_system_theme", False)  # User manually chose theme
        self.update_theme_menu_checks()
    
    def log_message(self, message):
        """Add a message to the log"""
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        # Safety check - only log if log_text widget exists
        if hasattr(self, 'log_text') and self.log_text is not None:
            self.log_text.append(formatted_message)
            
            # Auto-scroll to bottom
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        else:
            # Fallback to console if GUI log not available
            print(formatted_message)
    
    def update_statistics(self):
        """Update the statistics display"""
        if not self.installed_games:
            self.stats_label.setText("No games found")
            return
        
        total_games = len(self.installed_games)
        up_to_date = len([g for g in self.installed_games if g.get('update_status') == 'Up to Date'])
        updates_available = len([g for g in self.installed_games if g.get('update_status') == 'Update Available'])
        
        stats_text = f"📊 Total: {total_games} | ✅ Up to Date: {up_to_date} | 🔄 Updates Available: {updates_available}"
        self.stats_label.setText(stats_text)
    
    def start_progress(self, total_items, operation_name="Processing"):
        """Start progress tracking"""
        import time
        self.progress_start_time = time.time()
        self.progress_total_items = total_items
        self.progress_completed_items = 0
        self.progress_bar.setMaximum(total_items)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(f"{operation_name}... 0/{total_items}")
        self.progress_bar.setVisible(True)
    
    def update_progress(self, completed_items=None):
        """Update progress bar with ETA calculation"""
        if completed_items is not None:
            self.progress_completed_items = completed_items
        else:
            self.progress_completed_items += 1
        
        if self.progress_total_items == 0:
            return
        
        # Calculate progress percentage
        progress_percent = (self.progress_completed_items / self.progress_total_items) * 100
        self.progress_bar.setValue(self.progress_completed_items)
        
        # Calculate ETA only if we have meaningful progress
        if self.progress_completed_items > 0 and self.progress_start_time:
            import time
            elapsed_time = time.time() - self.progress_start_time
            
            # Only calculate ETA if we have at least 2 items completed to get a better estimate
            if self.progress_completed_items >= 2:
                items_per_second = self.progress_completed_items / elapsed_time
                remaining_items = self.progress_total_items - self.progress_completed_items
                
                if items_per_second > 0 and remaining_items > 0:
                    eta_seconds = remaining_items / items_per_second
                    
                    # Format ETA
                    if eta_seconds < 60:
                        eta_text = f"{int(eta_seconds)}s"
                    elif eta_seconds < 3600:
                        eta_text = f"{int(eta_seconds // 60)}m {int(eta_seconds % 60)}s"
                    else:
                        eta_text = f"{int(eta_seconds // 3600)}h {int((eta_seconds % 3600) // 60)}m"
                    
                    # Only update format if it hasn't been set by detailed progress handler
                    current_format = self.progress_bar.format()
                    if "Analyzing" not in current_format and "Fetching" not in current_format and "Completed" not in current_format:
                        format_text = f"{self.progress_completed_items}/{self.progress_total_items} - ETA: {eta_text}"
                        self.progress_bar.setFormat(format_text)
                else:
                    if "Analyzing" not in self.progress_bar.format() and "Fetching" not in self.progress_bar.format():
                        format_text = f"{self.progress_completed_items}/{self.progress_total_items} - Calculating..."
                        self.progress_bar.setFormat(format_text)
            else:
                if "Analyzing" not in self.progress_bar.format() and "Fetching" not in self.progress_bar.format():
                    format_text = f"{self.progress_completed_items}/{self.progress_total_items} - Calculating..."
                    self.progress_bar.setFormat(format_text)
        
        # Hide progress bar when complete
        if self.progress_completed_items >= self.progress_total_items:
            QTimer.singleShot(2000, self.hide_progress)  # Hide after 2 seconds
    
    def hide_progress(self):
        """Hide the progress bar"""
        self.progress_bar.setVisible(False)
        self.progress_start_time = None
        self.progress_total_items = 0
        self.progress_completed_items = 0
        self.current_operation = "idle"
    
    def check_network_connectivity(self):
        """Check network connectivity and update indicator"""
        try:
            # Quick connectivity test to a reliable server
            import socket
            socket.setdefaulttimeout(3)
            
            # Try to connect to Google's DNS server
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(("8.8.8.8", 53))
                self.update_network_status(True)
                
        except Exception:
            self.update_network_status(False)
    
    def update_network_status(self, is_connected):
        """Update the network indicator visual status"""
        if is_connected:
            # Green indicator for connected
            color = "#27AE60" if self.current_theme == "dark" else "#16A085"
            self.network_indicator.setStyleSheet(f"""
                QLabel {{
                    border: 1px solid {"#5D6D7E" if self.current_theme == "dark" else "#BDC3C7"};
                    border-radius: 8px;
                    background-color: {color};
                    margin: 2px;
                }}
            """)
            self.network_indicator.setToolTip("🌐 Network connected - Online services available")
        else:
            # Red indicator for disconnected
            color = "#E74C3C" if self.current_theme == "dark" else "#C0392B"
            self.network_indicator.setStyleSheet(f"""
                QLabel {{
                    border: 1px solid {"#5D6D7E" if self.current_theme == "dark" else "#BDC3C7"};
                    border-radius: 8px;
                    background-color: {color};
                    margin: 2px;
                }}
            """)
            self.network_indicator.setToolTip("❌ Network disconnected - Update checking may fail")
    
    def on_network_error_detected(self):
        """Handle network error detection from update thread"""
        # Immediately recheck network status
        self.check_network_connectivity()
        # Show orange indicator for API issues even if general connectivity exists
        if hasattr(self, 'network_indicator'):
            color = "#F39C12" if self.current_theme == "dark" else "#E67E22"
            self.network_indicator.setStyleSheet(f"""
                QLabel {{
                    border: 1px solid {"#5D6D7E" if self.current_theme == "dark" else "#BDC3C7"};
                    border-radius: 8px;
                    background-color: {color};
                    margin: 2px;
                }}
            """)
            self.network_indicator.setToolTip("⚠️ Network issues detected - Some API calls may be failing")
            
            # Reset to normal status after 10 seconds
            QTimer.singleShot(10000, self.check_network_connectivity)
    
    def on_network_indicator_clicked(self, event):
        """Handle clicking on the network indicator for manual testing"""
        # Show testing status
        self.network_indicator.setStyleSheet(f"""
            QLabel {{
                border: 1px solid {"#5D6D7E" if self.current_theme == "dark" else "#BDC3C7"};
                border-radius: 8px;
                background-color: #3498DB;
                margin: 2px;
            }}
        """)
        self.network_indicator.setToolTip("🔄 Testing network connectivity...")
        self.status_bar.showMessage("Testing network connectivity...")
        
        # Perform network test after short delay to show the blue indicator
        QTimer.singleShot(500, self.perform_manual_network_test)
    
    def perform_manual_network_test(self):
        """Perform manual network connectivity test"""
        self.check_network_connectivity()
        
        # Show result in status bar briefly
        current_tooltip = self.network_indicator.toolTip()
        if "connected" in current_tooltip:
            self.status_bar.showMessage("Network test: Connected ✅", 3000)
        elif "disconnected" in current_tooltip:
            self.status_bar.showMessage("Network test: Disconnected ❌", 3000)
        else:
            self.status_bar.showMessage("Network test: Issues detected ⚠️", 3000)
    
    def auto_scan(self):
        """Automatically start scanning on startup"""
        QTimer.singleShot(1000, self.scan_games)  # Delay to allow UI to fully load
    
    def scan_games(self):
        """Start scanning for installed games"""
        if self.scan_thread and self.scan_thread.isRunning():
            return
        
        # Check if deep scan is enabled
        deep_scan_enabled = self.deep_scan_checkbox.isChecked()
        
        # Show warning for deep scan
        if deep_scan_enabled:
            from PySide6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self, 
                "Deep Scan Warning",
                "Deep Scan will search all available drives and common directories for GOG games.\n\n"
                "This process may take significantly longer (several minutes) but will find games "
                "installed in non-standard locations.\n\n"
                "Do you want to continue with Deep Scan?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                return
        
        self.scan_button.setEnabled(False)
        self.update_button.setEnabled(False)
        
        scan_type = "Deep Scan" if deep_scan_enabled else "Quick Scan"
        self.status_bar.showMessage(f"Starting {scan_type}...")
        
        # Start progress for the entire workflow (scanning + updates)
        # We'll estimate total items after scanning
        self.start_progress(1, f"{scan_type} in progress")
        self.current_operation = "scanning"
        
        self.scan_thread = GameScanThread(deep_scan=deep_scan_enabled)
        self.scan_thread.games_found.connect(self.on_games_found)
        self.scan_thread.scan_progress.connect(self.on_scan_progress)
        self.scan_thread.log_message.connect(self.log_message)
        self.scan_thread.finished.connect(self.on_scan_finished)
        self.scan_thread.start()
    
    def check_updates(self):
        """Start checking for game updates"""
        if not self.installed_games:
            QMessageBox.information(self, "No Games", "No games found to check for updates.")
            return
        
        if self.update_thread and self.update_thread.isRunning():
            return
        
        self.update_button.setEnabled(False)
        self.scan_button.setEnabled(False)
        self.status_bar.showMessage("Checking for updates...")
        
        # Continue existing progress or start new if called independently
        if self.current_operation not in ["preparing_updates", "scanning"]:
            # Called independently (not from scan), start fresh progress
            self.start_progress(len(self.installed_games), "Checking updates")
        else:
            # Continue from scanning phase
            self.current_operation = "updating"
        
        self.update_thread = UpdateCheckThread(self.installed_games)
        self.update_thread.update_progress.connect(self.on_update_progress)
        self.update_thread.progress_update.connect(self.on_detailed_progress_unified)
        self.update_thread.network_error_detected.connect(self.on_network_error_detected)
        self.update_thread.log_message.connect(self.log_message)
        self.update_thread.finished.connect(self.on_update_finished)
        self.update_thread.start()
    
    def refresh_all(self):
        """Refresh everything"""
        self.installed_games.clear()
        self.games_tree.clear()
        if hasattr(self, 'changelog_text') and self.changelog_text is not None:
            self.changelog_text.setHtml("Select a game to view changelog information")
        if hasattr(self, 'log_text') and self.log_text is not None:
            self.log_text.clear()
        self.scan_games()
    
    def open_gog_galaxy(self):
        """Open GOG Galaxy if installed"""
        scanner = GOGGameScanner()
        galaxy_path = scanner.find_gog_galaxy()
        
        if galaxy_path:
            try:
                subprocess.Popen([galaxy_path], creationflags=subprocess.CREATE_NO_WINDOW)
                self.log_message("🎮 GOG Galaxy launched successfully")
                self.status_bar.showMessage("GOG Galaxy opened")
            except Exception as e:
                self.log_message(f"❌ Failed to open GOG Galaxy: {str(e)}")
                QMessageBox.warning(self, "Error", f"Failed to open GOG Galaxy:\n{str(e)}")
        else:
            self.log_message("❌ GOG Galaxy not found")
            QMessageBox.information(self, "GOG Galaxy Not Found", 
                                  "GOG Galaxy is not installed or could not be found.")
    
    def on_scan_progress(self, status_text):
        """Handle scan progress updates"""
        if self.current_operation == "scanning":
            self.status_bar.showMessage(status_text)
            self.progress_bar.setFormat(f"1/? - {status_text}")
    
    def on_games_found(self, games):
        """Handle games found signal"""
        self.installed_games = games
        self.update_games_display(preserve_selection=False)  # New games, don't preserve selection
        self.update_statistics()
    
    def on_scan_finished(self):
        """Handle scan finished signal"""
        self.scan_button.setEnabled(True)
        if self.installed_games:
            self.update_button.setEnabled(True)
        
        # Transition to update checking phase
        if self.installed_games:
            # Update progress tracking for the update phase
            total_operations = 1 + len(self.installed_games)  # 1 for scan + games for updates
            self.progress_total_items = total_operations
            self.progress_completed_items = 1  # Scanning is done
            self.progress_bar.setMaximum(total_operations)
            self.progress_bar.setValue(1)
            self.current_operation = "preparing_updates"
            
            self.status_bar.showMessage("Scan completed, preparing to check updates...")
            self.progress_bar.setFormat(f"1/{total_operations} - Scan complete, starting updates...")
            
            # Auto-start update checking
            QTimer.singleShot(1000, self.check_updates)
        else:
            # No games found, complete the progress
            self.update_progress(1)
            self.status_bar.showMessage("Scan completed - no games found")
    
    def on_detailed_progress_unified(self, update_completed_count, status_text):
        """Handle detailed progress updates from the update thread (unified workflow)"""
        # Calculate total progress: 1 (scan) + update_completed_count
        total_completed = 1 + update_completed_count
        
        # Update progress bar values
        self.progress_completed_items = total_completed
        self.progress_bar.setValue(total_completed)
        
        # Calculate ETA if we have enough data
        eta_text = ""
        if total_completed >= 2 and self.progress_start_time:
            import time
            elapsed_time = time.time() - self.progress_start_time
            items_per_second = total_completed / elapsed_time
            remaining_items = self.progress_total_items - total_completed
            
            if items_per_second > 0 and remaining_items > 0:
                eta_seconds = remaining_items / items_per_second
                
                # Format ETA
                if eta_seconds < 60:
                    eta_text = f" - ETA: {int(eta_seconds)}s"
                elif eta_seconds < 3600:
                    eta_text = f" - ETA: {int(eta_seconds // 60)}m {int(eta_seconds % 60)}s"
                else:
                    eta_text = f" - ETA: {int(eta_seconds // 3600)}h {int((eta_seconds % 3600) // 60)}m"
        
        # Update progress bar format with current operation and ETA
        if hasattr(self, 'progress_bar') and self.progress_bar.isVisible():
            format_text = f"{total_completed}/{self.progress_total_items}{eta_text}"
            self.progress_bar.setFormat(format_text)
        
        # Update status bar with current operation
        if total_completed < self.progress_total_items:
            self.status_bar.showMessage(f"{status_text}")
        else:
            self.status_bar.showMessage("All operations completed")
            
        # Auto-hide when complete
        if total_completed >= self.progress_total_items:
            QTimer.singleShot(2000, self.hide_progress)
    
    def on_detailed_progress(self, completed_count, status_text):
        """Handle detailed progress updates from the update thread (standalone)"""
        # This is for when update checking is called independently
        if self.current_operation == "updating" and self.progress_total_items > len(self.installed_games):
            # Use unified handler
            self.on_detailed_progress_unified(completed_count, status_text)
            return
        
        # Store the original completed items
        original_completed = self.progress_completed_items
        
        # Update progress bar values
        self.progress_completed_items = completed_count
        self.progress_bar.setValue(completed_count)
        
        # Calculate ETA if we have enough data
        eta_text = ""
        if self.progress_completed_items >= 2 and self.progress_start_time:
            import time
            elapsed_time = time.time() - self.progress_start_time
            items_per_second = self.progress_completed_items / elapsed_time
            remaining_items = self.progress_total_items - self.progress_completed_items
            
            if items_per_second > 0 and remaining_items > 0:
                eta_seconds = remaining_items / items_per_second
                
                # Format ETA
                if eta_seconds < 60:
                    eta_text = f" - ETA: {int(eta_seconds)}s"
                elif eta_seconds < 3600:
                    eta_text = f" - ETA: {int(eta_seconds // 60)}m {int(eta_seconds % 60)}s"
                else:
                    eta_text = f" - ETA: {int(eta_seconds // 3600)}h {int((eta_seconds % 3600) // 60)}m"
        
        # Update progress bar format with current operation and ETA
        if hasattr(self, 'progress_bar') and self.progress_bar.isVisible():
            format_text = f"{completed_count}/{self.progress_total_items}{eta_text}"
            self.progress_bar.setFormat(format_text)
        
        # Update status bar with current operation
        if completed_count < self.progress_total_items:
            self.status_bar.showMessage(f"{status_text}")
        else:
            self.status_bar.showMessage("Update check completed")
            
        # Auto-hide when complete
        if completed_count >= self.progress_total_items:
            QTimer.singleShot(2000, self.hide_progress)
    
    def on_update_progress(self, game):
        """Handle update progress signal"""
        # Find and update the game in our list
        for i, existing_game in enumerate(self.installed_games):
            if existing_game.get('name') == game.get('name'):
                self.installed_games[i] = game
                break
        
        self.update_games_display()
        self.update_statistics()
    
    def on_update_finished(self):
        """Handle update check finished signal"""
        self.update_button.setEnabled(True)
        self.scan_button.setEnabled(True)
        self.status_bar.showMessage("Update check completed")
    
    def update_games_display(self, preserve_selection=True):
        """Update the games tree widget"""
        # Store the currently selected game name to restore later
        selected_game_name = None
        if preserve_selection:
            selected_items = self.games_tree.selectedItems()
            if selected_items:
                selected_game_name = selected_items[0].text(0)
        
        # Temporarily disconnect selection change signal to prevent issues during rebuild
        try:
            self.games_tree.itemSelectionChanged.disconnect()
        except:
            pass  # Signal may not be connected yet
        
        self.games_tree.clear()
        
        if not self.installed_games:
            item = QTreeWidgetItem(["No GOG games found", "", "", "", "Not scanned", "", "", "", ""])
            self.games_tree.addTopLevelItem(item)
            # Reconnect signal
            self.games_tree.itemSelectionChanged.connect(self.on_game_selected)
            return
        
        # Count duplicate game names
        game_name_counts = {}
        for game in self.installed_games:
            name = game.get('name', 'Unknown Game')
            game_name_counts[name] = game_name_counts.get(name, 0) + 1
        
        # Debug: Print duplicate detection results
        duplicates_found = [name for name, count in game_name_counts.items() if count > 1]
        if duplicates_found:
            print(f"DEBUG: Found duplicate games: {duplicates_found}")
            for name, count in game_name_counts.items():
                if count > 1:
                    print(f"  - {name}: {count} occurrences")
        
        # Track which occurrence of each duplicate game we're processing
        game_occurrence_counter = {}
        selected_item_to_restore = None
        
        for game in self.installed_games:
            name = game.get('name', 'Unknown Game')
            readable_version = game.get('readable_version', '-')
            installed_version = game.get('installed_version', 'Unknown')
            latest_version = game.get('latest_version', 'Checking...')
            status = game.get('update_status', 'Unknown')
            size = game.get('size', 'Unknown')
            tags_value = game.get('tags', '🎮')
            path = game.get('install_path', 'Unknown')
            
            # Track occurrence number for duplicates
            game_occurrence_counter[name] = game_occurrence_counter.get(name, 0) + 1
            is_duplicate = game_name_counts[name] > 1
            occurrence_num = game_occurrence_counter[name]
            
            # Truncate path if too long
            if len(path) > 60:
                path = "..." + path[-57:]
            
            # Determine if this is a DLC/expansion
            is_dlc = any(dlc_keyword in name.lower() for dlc_keyword in [' - ', ': ', ' dlc', ' expansion', ' pack'])
            wiki_value = "📚" if not is_dlc else ""
            
            item = QTreeWidgetItem([name, readable_version, installed_version, latest_version, status, size, tags_value, path, wiki_value])
            
            # Get theme-appropriate colors
            if self.current_theme == "light":
                tags_color = QColor(75, 85, 99)     # Dark gray for tags
                wiki_color = QColor(59, 130, 246)   # Blue for clickable wiki
                wiki_disabled_color = QColor(156, 163, 175)  # Light gray for non-clickable
                path_color = QColor(55, 65, 81)     # Dark text for path
            else:
                tags_color = QColor(174, 182, 191)  # Light gray for tags
                wiki_color = QColor(100, 200, 255)  # Blue for clickable wiki
                wiki_disabled_color = QColor(100, 100, 100)  # Dark gray for non-clickable
                path_color = QColor(236, 240, 241)  # Light text for path
            
            # Style tags column (normal text, not clickable)
            item.setForeground(6, tags_color)
            item.setToolTip(6, f"Game Tags: {tags_value}")
            
            # Style wiki column (only clickable for main games) - now column 8
            if not is_dlc:
                item.setForeground(8, wiki_color)
                item.setToolTip(8, f"📚 Click to open PCGamingWiki page for: {name}")
                # Make wiki column look clickable
                font = item.font(8)
                font.setUnderline(True)
                item.setFont(8, font)
            else:
                item.setForeground(8, wiki_disabled_color)
                item.setToolTip(8, "Wiki not available for DLC/Expansions")
            
            # Install path as plain text (no longer clickable) - now column 7
            item.setForeground(7, path_color)
            item.setToolTip(7, f"Install Path: {game.get('install_path', 'Unknown')}")
            
            # Add visual distinction for duplicates - BRIGHT background colors only
            if is_duplicate:
                # Set tooltip to explain the duplicate
                item.setToolTip(0, f"DUPLICATE GAME #{occurrence_num} of {game_name_counts[name]}\nPath: {game.get('install_path', 'Unknown')}")
                # Use very bright, obvious background colors for duplicates
                if occurrence_num % 2 == 1:
                    # Bright purple background for odd occurrences
                    duplicate_color = QColor(150, 50, 200, 120)  # Purple
                else:
                    # Bright orange background for even occurrences  
                    duplicate_color = QColor(255, 140, 0, 120)   # Orange
                
                # Apply the bright background to ALL columns
                for i in range(9):
                    item.setBackground(i, duplicate_color)
            
            # Color code by status and make status clickable (only for updates)
            # Only apply status colors if NOT a duplicate (duplicates get their own colors)
            if not is_duplicate:
                # Get theme-appropriate status colors
                if self.current_theme == "light":
                    update_text_color = QColor(185, 28, 28)      # Dark red for light theme
                    update_bg_color = QColor(254, 242, 242, 200) # Light red background
                    success_text_color = QColor(22, 101, 52)     # Dark green for light theme
                    success_bg_color = QColor(240, 253, 244, 200) # Light green background
                    warning_bg_color = QColor(254, 249, 195, 200) # Light yellow background
                else:
                    update_text_color = QColor(231, 76, 60)      # Original red
                    update_bg_color = QColor(231, 76, 60, 30)    # Original light red
                    success_text_color = QColor(46, 204, 113)    # Original green
                    success_bg_color = QColor(46, 204, 113, 30)  # Original light green
                    warning_bg_color = QColor(241, 196, 15, 30)  # Original yellow
                
                if status == 'Update Available':
                    # Set red color for status text and make it look like a link
                    item.setForeground(4, update_text_color)
                    item.setToolTip(4, "🌐 Click to open this game on gog-games.to")
                    # Make status text bold and underlined to look like a link
                    font = item.font(4)
                    font.setBold(True)
                    font.setUnderline(True)
                    item.setFont(4, font)
                    # Light red background for the entire row
                    for i in range(9):
                        item.setBackground(i, update_bg_color)
                elif status == 'Up to Date':
                    # Set green color for status text (not clickable)
                    item.setForeground(4, success_text_color)
                    # Light green background for the entire row
                    for i in range(9):
                        item.setBackground(i, success_bg_color)
                elif status.startswith('Cannot Check'):
                    # Yellow background
                    for i in range(9):
                        item.setBackground(i, warning_bg_color)
            else:
                # For duplicates, still make the status text clickable but keep duplicate background
                if status == 'Update Available':
                    item.setForeground(4, QColor(255, 255, 255))  # White text for visibility on colored background
                    item.setToolTip(4, "🌐 Click to open this game on gog-games.to")
                    font = item.font(4)
                    font.setBold(True)
                    font.setUnderline(True)
                    item.setFont(4, font)
            

            
            self.games_tree.addTopLevelItem(item)
            
            # Check if this is the previously selected item (use original name for matching)
            if preserve_selection and selected_game_name and name == selected_game_name:
                selected_item_to_restore = item
        
        # Reconnect the selection change signal
        self.games_tree.itemSelectionChanged.connect(self.on_game_selected)
        
        # Restore selection if we found the previously selected item
        if selected_item_to_restore:
            selected_item_to_restore.setSelected(True)
            self.games_tree.setCurrentItem(selected_item_to_restore)
    
    def convert_links_to_html(self, text):
        """Convert URLs in text to clickable HTML links"""
        import re
        
        if not text:
            return ""
        
        # Escape HTML characters first
        html_text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # Convert line breaks to HTML
        html_text = html_text.replace('\n', '<br>')
        
        # URL pattern - matches http, https, and www URLs
        url_pattern = r'(https?://[^\s<>"{}|\\^`\[\]]+)'
        
        def replace_url(match):
            url = match.group(1)
            # Clean up any trailing punctuation that shouldn't be part of the URL
            url = re.sub(r'[.,;:!?]+$', '', url)
            return f'<a href="{url}" style="color: #3498DB; text-decoration: underline;">{url}</a>'
        
        # Replace URLs with HTML links
        html_text = re.sub(url_pattern, replace_url, html_text)
        
        # Also handle www. links (add http://)
        www_pattern = r'\b(www\.[^\s<>"{}|\\^`\[\]]+)'
        
        def replace_www(match):
            url = match.group(1)
            url = re.sub(r'[.,;:!?]+$', '', url)
            return f'<a href="http://{url}" style="color: #3498DB; text-decoration: underline;">{url}</a>'
        
        html_text = re.sub(www_pattern, replace_www, html_text)
        
        return html_text
    
    def format_game_name_for_url(self, game_name):
        """Format game name for gog-games.to URL format"""
        import re
        # Convert to lowercase
        formatted_name = game_name.lower()
        # Replace spaces and special characters with underscores
        formatted_name = re.sub(r'[^a-z0-9]+', '_', formatted_name)
        # Remove leading/trailing underscores
        formatted_name = formatted_name.strip('_')
        return formatted_name
    
    def format_game_name_for_wiki(self, game_name):
        """Format game name for PCGamingWiki URL"""
        import re
        
        # Clean up common suffixes and prefixes
        formatted = game_name.strip()
        
        # Remove common GOG suffixes
        suffixes_to_remove = [
            " - Enhanced Edition",
            " Enhanced Edition", 
            " - Director's Cut",
            " Director's Cut",
            " - Definitive Edition",
            " Definitive Edition",
            " - Game of the Year Edition",
            " Game of the Year Edition",
            " - Complete Edition",
            " Complete Edition",
            " - Digital Deluxe Edition",
            " Digital Deluxe Edition"
        ]
        
        for suffix in suffixes_to_remove:
            if formatted.endswith(suffix):
                formatted = formatted[:-len(suffix)].strip()
                break
        
        # Replace special characters and spaces
        formatted = re.sub(r'[^\w\s]', '', formatted)  # Remove special chars except spaces
        formatted = re.sub(r'\s+', '_', formatted)     # Replace spaces with underscores
        
        return formatted
    
    def on_item_clicked(self, item, column):
        """Handle item clicks - open specific game page on gog-games.to if status column is clicked, or PCGamingWiki if wiki column is clicked"""
        if column == 4:  # Status column (moved from 3 to 4)
            status = item.text(4)
            if status == 'Update Available':  # Only for updates, not "Up to Date"
                import webbrowser
                
                # Get the game name and format it for the URL
                game_name = item.text(0)
                
                formatted_name = self.format_game_name_for_url(game_name)
                
                # Construct game-specific URL using the /game/ pattern
                url_to_open = f"https://www.gog-games.to/game/{formatted_name}"
                
                try:
                    webbrowser.open(url_to_open)
                    self.log_message(f"🌐 Opened gog-games.to game page for '{game_name}': {url_to_open}")
                except Exception as e:
                    self.log_message(f"❌ Failed to open gog-games.to: {str(e)}")
        
        elif column == 8:  # Wiki column (moved from 7 to 8)
            game_name = item.text(0)
            wiki_text = item.text(8)
            
            # Only allow wiki opening for main games (has 📚 icon)
            if wiki_text == "📚":
                try:
                    # Format game name for PCGamingWiki URL
                    wiki_game_name = self.format_game_name_for_wiki(game_name)
                    wiki_url = f"https://www.pcgamingwiki.com/wiki/{wiki_game_name}"
                    
                    import webbrowser
                    webbrowser.open(wiki_url)
                    self.log_message(f"📚 Opened PCGamingWiki: {game_name}")
                except Exception as e:
                    self.log_message(f"❌ Failed to open PCGamingWiki: {str(e)}")
            else:
                self.log_message(f"📚 PCGamingWiki is only available for main games, not DLCs")
    
    def on_mouse_enter_item(self, index):
        """Change cursor when hovering over clickable columns"""
        if index.column() == 4:  # Status column (moved from 3 to 4)
            item = self.games_tree.itemFromIndex(index)
            if item and item.text(4) == 'Update Available':  # Only for updates, not "Up to Date"
                self.games_tree.setCursor(Qt.PointingHandCursor)
            else:
                self.games_tree.setCursor(Qt.ArrowCursor)
        elif index.column() == 8:  # Wiki column (moved from 7 to 8)
            item = self.games_tree.itemFromIndex(index)
            if item and item.text(8) == "📚":  # Only for main games with wiki icon
                self.games_tree.setCursor(Qt.PointingHandCursor)
            else:
                self.games_tree.setCursor(Qt.ArrowCursor)
        else:
            self.games_tree.setCursor(Qt.ArrowCursor)
    
    def on_game_selected(self):
        """Handle game selection in the tree"""
        selected_items = self.games_tree.selectedItems()
        if not selected_items:
            self.changelog_text.setHtml("Select a game to view changelog information")
            return
        
        selected_item = selected_items[0]
        display_name = selected_item.text(0)
        
        # Use the display name directly (no modifications needed)
        game_name = display_name
        
        # Find the game in our list
        selected_game = None
        for game in self.installed_games:
            if game.get('name') == game_name:
                selected_game = game
                break
        
        if selected_game:
            changelog = selected_game.get('changelog', 'No changelog available')
            install_path = selected_game.get('install_path', 'Unknown')
            gog_id = selected_game.get('gog_id', 'Unknown')
            
            # Format changelog display
            # Convert URLs to clickable links in HTML format
            changelog_html = self.convert_links_to_html(changelog)
            
            changelog_display = f"<h3 style='color: #3498DB;'>📋 {game_name}</h3>"
            changelog_display += f"<p><b>Install Path:</b> {install_path}</p>"
            if gog_id != 'Unknown':
                changelog_display += f"<p><b>GOG ID:</b> {gog_id}</p>"
            changelog_display += f"<hr style='border: 1px solid #5D6D7E;'>"
            changelog_display += f"<div style='margin-top: 15px;'>{changelog_html}</div>"
            
            self.changelog_text.setHtml(changelog_display)
        else:
            self.changelog_text.setHtml("Game information not available")


def main():
    """Main function to run the Qt6 application"""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("GOG Games Build ID Checker")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("GOG Tools")
    
    # Apply global dark palette
    app.setStyle('Fusion')
    
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(44, 62, 80))
    dark_palette.setColor(QPalette.WindowText, QColor(236, 240, 241))
    dark_palette.setColor(QPalette.Base, QColor(52, 73, 94))
    dark_palette.setColor(QPalette.AlternateBase, QColor(74, 95, 122))
    dark_palette.setColor(QPalette.ToolTipBase, QColor(0, 0, 0))
    dark_palette.setColor(QPalette.ToolTipText, QColor(236, 240, 241))
    dark_palette.setColor(QPalette.Text, QColor(236, 240, 241))
    dark_palette.setColor(QPalette.Button, QColor(52, 73, 94))
    dark_palette.setColor(QPalette.ButtonText, QColor(236, 240, 241))
    dark_palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
    dark_palette.setColor(QPalette.Link, QColor(52, 152, 219))
    dark_palette.setColor(QPalette.Highlight, QColor(52, 152, 219))
    dark_palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
    
    app.setPalette(dark_palette)
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main()) 