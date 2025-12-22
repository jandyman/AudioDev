# Max External Build System Guide

Complete guide to building Max/MSP externals outside the SDK tree with universal binary support.

## Quick Reference

**Key Requirements:**
- ✅ Location independent (projects can exist anywhere)
- ✅ Universal binary (x86_64 + arm64) for Apple Silicon compatibility
- ✅ Self-contained builds (all output in project folder)
- ✅ Single SDK path to configure

## CMakeLists.txt Template

```cmake
cmake_minimum_required(VERSION 3.19)

# ONLY REQUIRED PATH: Absolute path to Max SDK
set(C74_MAX_SDK_PATH "/Users/andy/Dropbox/Developer/AudioDev/max-sdk")

# Override SDK defaults to make build location-independent
set(C74_SUPPORT_DIR "${C74_MAX_SDK_PATH}/source/max-sdk-base/c74support")
set(C74_LIBRARY_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/build/externals")

# Build universal binary (Intel + Apple Silicon) - CRITICAL!
set(CMAKE_OSX_ARCHITECTURES "x86_64;arm64")

# Include Max's pre-target setup
include("${C74_MAX_SDK_PATH}/source/max-sdk-base/script/max-pretarget.cmake")

# Include directories for Max and MSP headers
include_directories(
    "${MAX_SDK_INCLUDES}"
    "${MAX_SDK_MSP_INCLUDES}")

# Add the external as a MODULE
add_library(${PROJECT_NAME} MODULE your_source.cpp)

# Include Max's post-target setup
include("${C74_MAX_SDK_PATH}/source/max-sdk-base/script/max-posttarget.cmake")
```

## SDK Default Behavior (Problems We Solve)

The Max SDK's CMake scripts assume:

1. **Project Location**: `max-sdk/source/<category>/<project>/`
2. **Output Directory**: `../../../externals` (3 levels up)
3. **Headers**: Relative path `../c74support`
4. **Architecture**: Intel only (x86_64) ⚠️ **Breaks on Apple Silicon!**

## Our Overrides

### 1. C74_SUPPORT_DIR
```cmake
set(C74_SUPPORT_DIR "${C74_MAX_SDK_PATH}/source/max-sdk-base/c74support")
```
- **Why**: Prevents relative path issues
- **Default**: `${CMAKE_CURRENT_LIST_DIR}/../c74support`
- **Used for**: Finding headers, Info.plist.in, PkgInfo

### 2. C74_LIBRARY_OUTPUT_DIRECTORY
```cmake
set(C74_LIBRARY_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/build/externals")
```
- **Why**: Keeps builds self-contained
- **Default**: `${CMAKE_CURRENT_SOURCE_DIR}/../../../externals`
- **Result**: `.mxo` files go in project's `build/externals/`

### 3. CMAKE_OSX_ARCHITECTURES ⚠️ CRITICAL
```cmake
set(CMAKE_OSX_ARCHITECTURES "x86_64;arm64")
```
- **Why**: Enables loading on Apple Silicon Macs
- **Default**: `x86_64` only
- **Symptom if missing**: "could not load due to incorrect architecture"
- **Must be set BEFORE**: `include(max-pretarget.cmake)`

## Folder Naming Convention

Max uses `~` in object names, but filesystems don't allow it.

**SDK Convention:**
```
Folder: foo_tilde
Output: foo~.mxo
```

The SDK's `max-pretarget.cmake` auto-converts `_tilde` → `~`:
```cmake
string(REGEX REPLACE "_tilde" "~" EXTERN_OUTPUT_NAME ...)
```

**Example:**
```
Folder: andy.gain_tilde
Output: andy.gain~.mxo
Class:  "andy.gain~" (in code)
Max:    andy.gain~ (what you type)
```

## Build Process

### Initial Setup
```bash
cd your_external_tilde
rm -rf build
mkdir build
cd build
cmake -G Xcode ..
```

### Building
```bash
# Option A: Xcode GUI
open your_external_tilde.xcodeproj
# Press Cmd+B

# Option B: Command line
xcodebuild -configuration Debug
```

### Verify Universal Binary
```bash
lipo -info build/externals/your.external~.mxo/Contents/MacOS/your.external~
# Should show: Architectures in the fat file: ... are: x86_64 arm64
```

## Build Artifacts

```
your_external_tilde/
  build/
    externals/                    ← Add to Max search path
      your.external~.mxo/
        Contents/
          MacOS/
            your.external~        ← Universal binary
          Info.plist
          PkgInfo
    build/                        ← Xcode intermediates (normal)
      your_external_tilde.build/
      XCBuildData/
    your_external_tilde.xcodeproj/
    CMakeFiles/
```

**Note:** The nested `build/build/` is normal - Xcode creates it for intermediate files.

## Troubleshooting

### "incorrect architecture"
**Symptom:** External won't load in Max on Apple Silicon

**Cause:** Built for Intel only (x86_64)

**Fix:**
1. Add `CMAKE_OSX_ARCHITECTURES` to CMakeLists.txt (see template above)
2. Clean rebuild: `rm -rf build && mkdir build && cd build && cmake -G Xcode ..`
3. Build: `xcodebuild -configuration Debug`
4. Verify: `lipo -info path/to/binary` shows both architectures

**Prevention:** Always include `CMAKE_OSX_ARCHITECTURES "x86_64;arm64"` in CMakeLists.txt

### "no such object" in Max
**Cause:** Max can't find the .mxo file

**Fix:**
1. Add to Max search path: Options → File Preferences
2. Add folder: `/path/to/your_external_tilde/build/externals`
3. Restart Max

### Build succeeds but old version loads
**Cause:** Max caches externals in memory

**Fix:**
1. Always **restart Max** after rebuilding
2. Don't just delete/recreate object - restart completely

### Build succeeds but .mxo not updated
**Cause:** Xcode using stale cache

**Fix:**
1. Product → Clean Build Folder (Shift+Cmd+K)
2. Rebuild (Cmd+B)

### Files created outside project folder
**Cause:** Didn't override `C74_LIBRARY_OUTPUT_DIRECTORY`

**Fix:**
1. Add override to CMakeLists.txt (see template)
2. Delete stray files (commonly in `~/Developer/externals/`)
3. Regenerate and rebuild

## Portability

Projects configured this way are fully portable:

✅ Copy folder anywhere on your system
✅ Only edit SDK path in CMakeLists.txt if SDK moved
✅ All build artifacts stay in project folder
✅ No dependencies on project location

**Tested:** Copying to `/tmp/` and building works identically.

## SDK Files Referenced

Via absolute paths using `${C74_MAX_SDK_PATH}`:

1. `source/max-sdk-base/script/max-pretarget.cmake`
2. `source/max-sdk-base/script/max-posttarget.cmake`
3. `source/max-sdk-base/c74support/max-includes/`
4. `source/max-sdk-base/c74support/msp-includes/`
5. `source/max-sdk-base/script/Info.plist.in`
6. `source/max-sdk-base/script/PkgInfo`

## Key Takeaways

1. **Universal binary is required** for Apple Silicon compatibility
2. **Set CMAKE_OSX_ARCHITECTURES before including max-pretarget.cmake**
3. **Folder naming:** Use `_tilde` suffix, SDK converts to `~`
4. **Always restart Max** after rebuilding (it caches externals)
5. **One SDK path** to configure, everything else is automatic

## Reference

- **Template Project:** `andy.gain_tilde/`
- **Max SDK:** `/Users/andy/Dropbox/Developer/AudioDev/max-sdk/`
- **Max SDK Docs:** `max-sdk/MaxAPI.pdf`
- **SDK Examples:** `max-sdk/source/audio/`
