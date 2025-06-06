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
    QSizePolicy, QSpacerItem, QMenuBar, QMenu
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSettings
from PySide6.QtGui import QFont, QIcon, QPalette, QColor, QAction, QKeySequence

# Import the game scanner from the original file
import winreg
import subprocess


class GOGGameScanner:
    """Scanner class for detecting installed GOG games - reused from original implementation"""
    
    def __init__(self):
        """Initialize the GOG game scanner"""
        self.found_games = []
        
    def find_gog_galaxy(self):
        """Find GOG Galaxy installation"""
        print("DEBUG: Searching for GOG Galaxy...")
        
        # Common GOG Galaxy installation paths
        possible_paths = [
            "C:\\Program Files (x86)\\GOG Galaxy\\GalaxyClient.exe",
            "C:\\Program Files\\GOG Galaxy\\GalaxyClient.exe",
            "C:\\Users\\{}\\AppData\\Local\\GOG.com\\Galaxy\\GalaxyClient.exe".format(os.getenv('USERNAME', 'User')),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                print(f"DEBUG: Found GOG Galaxy at: {path}")
                return path
        
        # Try registry
        if winreg:
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\GOG.com\GalaxyClient\paths")
                client_path = winreg.QueryValueEx(key, "client")[0]
                if os.path.exists(client_path):
                    print(f"DEBUG: Found GOG Galaxy via registry: {client_path}")
                    return client_path
            except:
                pass
        
        print("DEBUG: GOG Galaxy not found")
        return None
        
    def find_gog_games(self):
        """Find all installed GOG games"""
        print("DEBUG: Starting game scan...")
        self.found_games = []
        
        # Scan registry
        registry_games = self._scan_registry()
        
        # Scan directories
        directory_games = self._scan_directories()
        
        # Combine and deduplicate
        all_games = registry_games + directory_games
        unique_games = {}
        
        for game in all_games:
            game_name = game.get('name', '').lower()
            if game_name and game_name not in unique_games:
                unique_games[game_name] = game
        
        self.found_games = list(unique_games.values())
        
        print(f"DEBUG: Total games found: {len(self.found_games)}")
        for game in self.found_games:
            print(f"DEBUG: Game: {game.get('name')} at {game.get('install_path')}")
        
        return self.found_games
    
    def _scan_registry(self):
        """Scan Windows registry for GOG games"""
        print("DEBUG: Scanning registry...")
        games = []
        
        if not winreg:
            print("DEBUG: winreg not available, skipping registry scan")
            return games
        
        registry_paths = [
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
        ]
        
        for registry_path in registry_paths:
            try:
                print(f"DEBUG: Checking registry path: {registry_path}")
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
                    
                    print(f"DEBUG: Found {len(gog_keys)} GOG keys in {registry_path}")
                    
                    for gog_key in gog_keys:
                        game_info = self._extract_game_info_from_registry(key, gog_key)
                        if game_info:
                            games.append(game_info)
                            
            except Exception as e:
                print(f"DEBUG: Error scanning registry path {registry_path}: {e}")
                continue
        
        print(f"DEBUG: Registry scan found {len(games)} games")
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
        """Clean and validate version string from registry"""
        if not version_str:
            return None
        
        version_str = str(version_str).strip()
        prefixes = ['v', 'ver', 'version', 'rel', 'release']
        for prefix in prefixes:
            if version_str.lower().startswith(prefix):
                version_str = version_str[len(prefix):].strip('.: ')
                break
        
        return self._extract_version_from_text(version_str)
    
    def _scan_directories(self):
        """Scan common directories for GOG games"""
        print("DEBUG: Scanning directories...")
        games = []
        
        # Common GOG installation directories
        search_paths = [
            "C:\\Program Files (x86)\\GOG Games",
            "C:\\Program Files\\GOG Games",
            "C:\\GOG Games",
            "D:\\GOG Games",
            "E:\\GOG Games",
            "F:\\GOG Games",
            "G:\\GOG Games",
            "C:\\Games\\GOG",
            "D:\\Games\\GOG",
            "E:\\Games\\GOG",
            "C:\\Program Files\\GOG Games",
            "C:\\Program Files (x86)\\GOG Games",
            "D:\\Program Files\\GOG Games",
            "D:\\Program Files (x86)\\GOG Games",
            "C:\\Games",
            "D:\\Games",
            "E:\\Games",
            f"C:\\Users\\{os.getenv('USERNAME', 'User')}\\Games\\GOG",
            f"C:\\Users\\{os.getenv('USERNAME', 'User')}\\Documents\\GOG Games",
            "D:",
            "E:",
            "F:"
        ]
        
        for path in search_paths:
            print(f"DEBUG: Checking directory: {path}")
            if os.path.exists(path):
                print(f"DEBUG: Directory exists: {path}")
                try:
                    items = os.listdir(path)
                    print(f"DEBUG: Found {len(items)} items in {path}")
                    
                    for item in items:
                        item_path = os.path.join(path, item)
                        if os.path.isdir(item_path):
                            if self._is_gog_game_directory(item_path):
                                print(f"DEBUG: Found GOG metadata file: {self._find_gog_metadata(item_path)}")
                                print(f"DEBUG: Analyzing potential GOG game: {item_path}")
                                game_info = self._analyze_game_directory(item_path, item)
                                if game_info:
                                    print(f"DEBUG: Successfully identified GOG game: {game_info['name']}")
                                    games.append(game_info)
                            else:
                                # Check for access errors
                                try:
                                    os.listdir(item_path)
                                except Exception as e:
                                    print(f"DEBUG: Error checking directory {item_path}: {e}")
                                    
                except Exception as e:
                    print(f"DEBUG: Error scanning directory {path}: {e}")
            else:
                print(f"DEBUG: Directory does not exist: {path}")
        
        print(f"DEBUG: Directory scan found {len(games)} games")
        return games
    
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
            
        patterns = [
            r'version\s*[:=]\s*([0-9]+(?:\.[0-9]+)+)',
            r'v\.?\s*([0-9]+(?:\.[0-9]+)+)',
            r'([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)',
            r'([0-9]+\.[0-9]+\.[0-9]+)',
            r'([0-9]+\.[0-9]+)',
            r'build\s*[:=]\s*([0-9]+)',
            r'release\s*[:=]\s*([0-9]+(?:\.[0-9]+)*)',
        ]
        
        text_lower = text.lower()
        
        for pattern in patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                version = match.group(1)
                if self._is_valid_version(version):
                    return version
        
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
    
    def __init__(self):
        super().__init__()
        self.scanner = GOGGameScanner()
    
    def run(self):
        """Run the game scanning in a separate thread"""
        try:
            self.log_message.emit("🔄 Starting game scan...")
            games = self.scanner.find_gog_games()
            self.games_found.emit(games)
            self.log_message.emit(f"✅ Scan completed! Found {len(games)} games")
        except Exception as e:
            self.log_message.emit(f"❌ Error during scan: {str(e)}")


class UpdateCheckThread(QThread):
    """Thread for checking game updates without blocking the UI"""
    update_progress = Signal(dict)
    log_message = Signal(str)
    finished = Signal()
    
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
                
                self.log_message.emit(f"🎮 Checking: {game_name}")
                
                # Detect version from GOG files
                detected_version = self.detect_version_from_gog_files(install_path)
                
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
                    
                    if detected_version.isdigit() and len(detected_version) >= 8:
                        self.log_message.emit(f"   🎯 Found Build ID: {detected_version}")
                    else:
                        self.log_message.emit(f"   🎯 Found GOG ID: {detected_version}")
                else:
                    self.log_message.emit(f"   ❌ Could not detect version/build ID")
                
                # Get latest version info from APIs
                self.log_message.emit(f"   🌐 Fetching from GOG Database API...")
                api_id = actual_gog_id if actual_gog_id else detected_version
                self.log_message.emit(f"   🔧 Using API ID: {api_id} (actual_gog_id: {actual_gog_id}, detected_version: {detected_version})")
                version_info = self.get_latest_version_info(game_name, api_id)
                
                time.sleep(1)  # Rate limiting
                
                if version_info and 'error' not in version_info:
                    game['latest_version'] = version_info.get('latest_version', 'Unknown')
                    game['changelog'] = version_info.get('changelog', 'No changelog available')
                    game['tags'] = version_info.get('tags', '🎮')
                    source = version_info.get('source', 'unknown')
                    
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
                
                # Emit progress update
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
            
            for file in os.listdir(install_path):
                if file.lower().startswith('goggame-') and file.lower().endswith('.info'):
                    match = re.search(r'goggame-(\d+)\.info', file.lower())
                    if match:
                        gog_id = match.group(1)
                        info_path = os.path.join(install_path, file)
                        
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
        except:
            return None
    
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
                        latest_build = builds[-1]
                        version = latest_build.get('version', 'Unknown')
                        build_id = latest_build.get('id', '')
                        
                        # Extract tags information from product data
                        tags_info = self.extract_tags_from_data(data, gog_id)
                        
                        self.log_message.emit(f"   📋 Found {len(builds)} builds, latest: {build_id}")
                        
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
                            
                            # For DLCs, mention they share the base game's build ID
                            if is_dlc:
                                changelog += f"\n\nNote: This DLC/Expansion shares the build ID with the base game '{base_game_name}'"
                        
                        return {
                            'latest_version': latest_version,
                            'changelog': changelog,
                            'build_id': build_id,
                            'tags': tags_info,
                            'source': 'gogdb.org',
                            'base_game': base_game_name if is_dlc else game_name
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
        except Exception as e:
            self.log_message.emit(f"   ❌ GOGDB API Unexpected Error: {str(e)}")
        
        return None
    
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
        
        controls_layout = QHBoxLayout(controls_frame)
        controls_layout.setSpacing(10)
        
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
        
        # Add buttons to layout
        controls_layout.addWidget(self.scan_button)
        controls_layout.addWidget(self.update_button)
        controls_layout.addWidget(self.refresh_button)
        controls_layout.addWidget(self.galaxy_button)
        controls_layout.addWidget(self.help_button)
        controls_layout.addStretch()
        
        # Statistics labels
        self.stats_label = QLabel("Ready to scan")
        self.stats_label.setStyleSheet("color: #ECF0F1; font-size: 12px; font-weight: bold;")
        controls_layout.addWidget(self.stats_label)
        
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
<li><b>Check Updates:</b> Click "Check Updates" to compare with latest versions</li>
<li><b>View Details:</b> Click on any game to see changelog information</li>
<li><b>Open Folders:</b> Click on install paths to open game folders</li>
</ol>

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
        
        about_text = """
<h3>🎮 GOG Games Build ID Checker</h3>

<p><b>Version:</b> 2.0</p>
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
        
        # Update statistics label
        if hasattr(self, 'stats_label'):
            self.stats_label.setStyleSheet(f"color: {text_primary}; font-size: 12px; font-weight: bold;")
        
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
    
    def auto_scan(self):
        """Automatically start scanning on startup"""
        QTimer.singleShot(1000, self.scan_games)  # Delay to allow UI to fully load
    
    def scan_games(self):
        """Start scanning for installed games"""
        if self.scan_thread and self.scan_thread.isRunning():
            return
        
        self.scan_button.setEnabled(False)
        self.update_button.setEnabled(False)
        self.status_bar.showMessage("Scanning for games...")
        
        self.scan_thread = GameScanThread()
        self.scan_thread.games_found.connect(self.on_games_found)
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
        
        self.update_thread = UpdateCheckThread(self.installed_games)
        self.update_thread.update_progress.connect(self.on_update_progress)
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
                subprocess.Popen([galaxy_path])
                self.log_message("🎮 GOG Galaxy launched successfully")
                self.status_bar.showMessage("GOG Galaxy opened")
            except Exception as e:
                self.log_message(f"❌ Failed to open GOG Galaxy: {str(e)}")
                QMessageBox.warning(self, "Error", f"Failed to open GOG Galaxy:\n{str(e)}")
        else:
            self.log_message("❌ GOG Galaxy not found")
            QMessageBox.information(self, "GOG Galaxy Not Found", 
                                  "GOG Galaxy is not installed or could not be found.")
    
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
        self.status_bar.showMessage("Scan completed")
        
        # Auto-start update checking
        if self.installed_games:
            QTimer.singleShot(2000, self.check_updates)
    
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
            item = QTreeWidgetItem(["No GOG games found", "", "", "Not scanned", "", "", "", ""])
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
            
            item = QTreeWidgetItem([name, installed_version, latest_version, status, size, tags_value, path, wiki_value])
            
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
            item.setForeground(5, tags_color)
            item.setToolTip(5, f"Game Tags: {tags_value}")
            
            # Style wiki column (only clickable for main games) - now column 7
            if not is_dlc:
                item.setForeground(7, wiki_color)
                item.setToolTip(7, f"📚 Click to open PCGamingWiki page for: {name}")
                # Make wiki column look clickable
                font = item.font(7)
                font.setUnderline(True)
                item.setFont(7, font)
            else:
                item.setForeground(7, wiki_disabled_color)
                item.setToolTip(7, "Wiki not available for DLC/Expansions")
            
            # Install path as plain text (no longer clickable) - now column 6
            item.setForeground(6, path_color)
            item.setToolTip(6, f"Install Path: {game.get('install_path', 'Unknown')}")
            
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
                for i in range(8):
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
                    item.setForeground(3, update_text_color)
                    item.setToolTip(3, "🌐 Click to open this game on gog-games.to")
                    # Make status text bold and underlined to look like a link
                    font = item.font(3)
                    font.setBold(True)
                    font.setUnderline(True)
                    item.setFont(3, font)
                    # Light red background for the entire row
                    for i in range(8):
                        item.setBackground(i, update_bg_color)
                elif status == 'Up to Date':
                    # Set green color for status text (not clickable)
                    item.setForeground(3, success_text_color)
                    # Light green background for the entire row
                    for i in range(8):
                        item.setBackground(i, success_bg_color)
                elif status.startswith('Cannot Check'):
                    # Yellow background
                    for i in range(8):
                        item.setBackground(i, warning_bg_color)
            else:
                # For duplicates, still make the status text clickable but keep duplicate background
                if status == 'Update Available':
                    item.setForeground(3, QColor(255, 255, 255))  # White text for visibility on colored background
                    item.setToolTip(3, "🌐 Click to open this game on gog-games.to")
                    font = item.font(3)
                    font.setBold(True)
                    font.setUnderline(True)
                    item.setFont(3, font)
            

            
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
        """Handle item clicks - open specific game page on gog-games.to if status column is clicked, or PCGamingWiki if tags column is clicked"""
        if column == 3:  # Status column
            status = item.text(3)
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
        
        elif column == 7:  # Wiki column (now last column)
            game_name = item.text(0)
            wiki_text = item.text(7)
            
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
        if index.column() == 3:  # Status column
            item = self.games_tree.itemFromIndex(index)
            if item and item.text(3) == 'Update Available':  # Only for updates, not "Up to Date"
                self.games_tree.setCursor(Qt.PointingHandCursor)
            else:
                self.games_tree.setCursor(Qt.ArrowCursor)
        elif index.column() == 7:  # Wiki column (now last column)
            item = self.games_tree.itemFromIndex(index)
            if item and item.text(7) == "📚":  # Only for main games with wiki icon
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