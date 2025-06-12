@echo off
echo Building GOG Checker v1.2.0 with Deep Scan...
echo.

echo Cleaning previous builds...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

echo.
echo Starting PyInstaller build...
python -m PyInstaller --clean GOGChecker-v1.2.0-DeepScan.spec

echo.
if exist "dist\GOGChecker-v1.2.0-DeepScan.exe" (
    echo ✅ Build successful!
    echo.
    echo Executable created: dist\GOGChecker-v1.2.0-DeepScan.exe
    echo.
    echo Testing executable...
    echo Starting application to verify build...
    start "" "dist\GOGChecker-v1.2.0-DeepScan.exe"
) else (
    echo ❌ Build failed!
    echo Check the output above for errors.
)

pause 