#!/bin/sh
# Wrap the PyInstaller Linux build (dist/t003-label-studio/) into an AppImage.
# Needs `appimagetool` on PATH (CI downloads it); run packaging/build.py first.
set -e
repo=$(cd "$(dirname "$0")/.." && pwd)
version=${1:-dev}
app="$repo/build/AppDir"
rm -rf "$app" && mkdir -p "$app/usr/lib"
cp -r "$repo/dist/t003-label-studio" "$app/usr/lib/t003-label-studio"
cp "$repo/packaging/icons/t003-label-gui-256.png" "$app/t003-label-gui.png"
cp "$repo/packaging/t003-label-gui.desktop" "$app/t003-label-gui.desktop"
sed -i 's|^Exec=.*|Exec=t003-label-studio|' "$app/t003-label-gui.desktop"
cat > "$app/AppRun" <<'RUN'
#!/bin/sh
here=$(dirname "$(readlink -f "$0")")
exec "$here/usr/lib/t003-label-studio/t003-label-studio" "$@"
RUN
chmod +x "$app/AppRun"
mkdir -p "$repo/dist"
ARCH=${ARCH:-x86_64} appimagetool --appimage-extract-and-run "$app" "$repo/dist/T003-Label-Studio-$version-x86_64.AppImage" 2>/dev/null \
  || ARCH=${ARCH:-x86_64} appimagetool "$app" "$repo/dist/T003-Label-Studio-$version-x86_64.AppImage"
