#!/bin/bash
# Builds CQHold.app from CQHold.swift. Run from the folder containing both files:
#   bash build-cqhold.sh
set -euo pipefail

APP="CQHold.app"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS"

swiftc -O CQHold.swift -o "$APP/Contents/MacOS/CQHold"

cat > "$APP/Contents/Info.plist" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>            <string>CQ Hold</string>
    <key>CFBundleDisplayName</key>     <string>CQ Hold</string>
    <key>CFBundleIdentifier</key>      <string>local.cqhold</string>
    <key>CFBundleExecutable</key>      <string>CQHold</string>
    <key>CFBundlePackageType</key>     <string>APPL</string>
    <key>CFBundleVersion</key>         <string>1</string>
    <key>CFBundleShortVersionString</key> <string>1.0</string>
    <key>LSMinimumSystemVersion</key>  <string>12.0</string>
    <key>LSUIElement</key>             <true/>
</dict>
</plist>
EOF

# Strip extended attributes (Finder info, quarantine, iCloud metadata) —
# codesign refuses to sign a bundle that has them.
xattr -cr "$APP"

# Ad-hoc sign the bundle so macOS treats it as a consistent app.
codesign --force --sign - "$APP"

echo "Built $APP — drag it to /Applications, then open it."
