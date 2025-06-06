# Build ID Update Implementation

## Overview

The GOG Games Version Checker has been updated to use build IDs for version comparison instead of traditional version strings. This provides more accurate and precise update detection for GOG games.

## Key Changes Made

### 1. Build ID Extraction (`_parse_gog_info_file`)
- **Priority System**: Now prioritizes build IDs over version strings
- **Multiple Patterns**: Searches for `buildId`, `build_id`, and `build` fields
- **Validation**: Ensures extracted build IDs are numeric and substantial (8+ digits)
- **Fallback Logic**: Falls back to version strings if no build ID found

### 2. API Response Handling
Updated all API methods to prioritize build IDs:
- `_try_gog_games_to_api`: Extracts and prioritizes `buildId` from API responses
- `_try_gogdb_api`: Uses build IDs from GOGDB builds array
- `_search_gog_games_to`: Prioritizes build IDs in search results

### 3. Version Comparison Logic (`check_all_updates`)
- **Numeric Comparison**: For build IDs, performs intelligent numeric comparison
- **Precise Updates**: Can determine if installed build is older, newer, or same
- **Status Categories**:
  - "Update Available" - Installed build ID is lower than latest
  - "Up to Date" - Build IDs match exactly
  - "Newer Version Installed" - Installed build ID is higher than latest
  - "Different Version" - Fallback for non-numeric comparisons

### 4. User Interface Updates
- **Column Headers**: Changed to "Installed Build/Version" and "Latest Build/Version"
- **Window Title**: Updated to "GOG Games Build ID Checker"
- **Logging Messages**: More descriptive messages about build ID extraction and comparison
- **Subtitle**: Added explanation about build ID comparison

### 5. **NEW: Changelog Fetching from GOGDB**
Added comprehensive changelog fetching capabilities:

#### Changelog URLs
- **Pattern**: `https://www.gogdb.org/product/[product_id]/releasenotes`
- **Implementation**: `fetch_changelog_from_gogdb(gog_id)` method
- **Parsing**: `parse_release_notes_html(html_content)` method

#### Changelog Parsing Features
- **Multiple Patterns**: Searches for various HTML patterns containing release information
- **Pattern 1**: Release notes sections with specific CSS classes
- **Pattern 2**: Version-specific changelog entries  
- **Pattern 3**: General update-related content paragraphs
- **Fallback**: Extracts meaningful paragraphs as release information

#### Changelog Display
- **Rich Formatting**: Displays "📄 Release Notes from GOGDB:" header
- **Clean Text**: Removes HTML tags and formats text properly
- **Fallback Info**: Shows basic build/version info if detailed changelog unavailable
- **Error Handling**: Graceful degradation when changelog fetching fails

### 6. Documentation Updates
- **README.md**: Updated to explain build ID priority and comparison
- **PROJECT_OVERVIEW.md**: Revised to focus on build ID checking capabilities
- **Launcher**: Updated titles and descriptions

## Technical Details

### Build ID Detection Process
1. **File Scanning**: Looks for `goggame-*.info` files in installation directories
2. **JSON Parsing**: Extracts build ID from JSON metadata using regex patterns
3. **Validation**: Ensures build IDs are numeric and at least 8 digits long
4. **Fallback**: Uses GOG ID or version string if no valid build ID found

### API Integration
- **Multi-Source**: Queries gog-games.to, GOGDB, and official GOG APIs
- **Build ID Priority**: Prefers build IDs from API responses over other identifiers
- **Consistent Format**: Returns build IDs as primary version identifier

### Comparison Algorithm
```python
if installed_build_id.isdigit() and latest_build_id.isdigit():
    installed_build = int(installed_build_id)
    latest_build = int(latest_build_id)
    
    if installed_build < latest_build:
        status = "Update Available"
    elif installed_build > latest_build:
        status = "Newer Version Installed" 
    else:
        status = "Up to Date"
```

## Benefits of Build ID Comparison

1. **Precision**: Build IDs are unique numeric identifiers for each game build
2. **Accuracy**: More reliable than version strings which can be inconsistent
3. **Chronological**: Higher build IDs typically indicate newer versions
4. **Comprehensive**: Works with GOG's internal versioning system

## Example Build ID
```json
{
  "buildId": "58465618714994950",
  "version": "1.0.2"
}
```

In this case, the application will use `58465618714994950` for comparison instead of `1.0.2`.

## Backward Compatibility

The application maintains backward compatibility:
- Falls back to GOG IDs when build IDs unavailable
- Falls back to version strings when neither build ID nor GOG ID available
- Handles mixed scenarios where some games have build IDs and others don't

## Changelog Fetching Implementation

### Technical Flow
```
1. Query GOGDB product API for build information
2. Extract GOG product ID from response
3. Fetch release notes from https://www.gogdb.org/product/{id}/releasenotes
4. Parse HTML content using multiple regex patterns
5. Clean and format extracted text
6. Display in changelog tab with fallback info
```

### HTML Parsing Patterns
- **Release Sections**: `<div class=".*release.*">content</div>`
- **Version Info**: `Version X.X.X: changelog content`
- **Update Content**: Paragraphs containing update-related keywords
- **Fallback**: Any meaningful paragraph content

### Error Handling
- **Network Timeouts**: 15-second timeout for changelog requests
- **Parse Failures**: Fallback to basic build/version information
- **Missing Content**: Graceful degradation with informative messages
- **User Feedback**: Clear logging of changelog fetching status

## Testing

The updated system has been tested for:
- ✅ Syntax validation (no compilation errors)
- ✅ Build ID extraction from metadata files
- ✅ API response handling with build ID priority
- ✅ Numeric comparison logic
- ✅ UI updates and column headers
- ✅ Fallback mechanisms
- ✅ Qt6 Signal/Slot fixes (QSignal → Signal)
- ✅ CSS transform property removal for Qt compatibility
- ✅ Changelog fetching from GOGDB release notes
- ✅ HTML parsing and text extraction
- ✅ Both Qt6 and Tkinter versions updated

The application is now ready for use with improved build ID-based version checking and comprehensive changelog fetching from GOGDB. 