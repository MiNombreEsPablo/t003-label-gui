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
bundle="$here/usr/lib/t003-label-studio/_internal"
# The bundle carries the (old) build base's libstdc++, which shadows the host's. The host's Mesa needs a newer one, so
# on a current distro EGL fails and the window stays blank. Preload the host's libstdc++ (and libgcc_s) when it is newer.
newest() { grep -ao 'GLIBCXX_3\.4\.[0-9]*' "$1" 2>/dev/null | sed 's/.*\.//' | sort -n | tail -1; }
host_lib() {
  for l in /sbin/ldconfig /usr/sbin/ldconfig ldconfig; do
    p=$("$l" -p 2>/dev/null | awk -v n="$1" '$1 == n && /x86-64|x86_64|aarch64|libc6$/ { print $NF; exit }')
    [ -n "$p" ] && { echo "$p"; return; }
  done
}
host_cxx=$(host_lib libstdc++.so.6)
if [ -n "$host_cxx" ] && [ -f "$bundle/libstdc++.so.6" ] \
   && [ "$(newest "$host_cxx" || echo 0)" -gt "$(newest "$bundle/libstdc++.so.6" || echo 0)" ] 2>/dev/null; then
  pre="$host_cxx"
  host_gcc=$(host_lib libgcc_s.so.1)
  [ -n "$host_gcc" ] && pre="$pre:$host_gcc"
  export LD_PRELOAD="$pre${LD_PRELOAD:+:$LD_PRELOAD}"
fi
exec "$here/usr/lib/t003-label-studio/t003-label-studio" "$@"
RUN
chmod +x "$app/AppRun"
mkdir -p "$repo/dist"
ARCH=${ARCH:-x86_64} appimagetool --appimage-extract-and-run "$app" "$repo/dist/T003-Label-Studio-$version-x86_64.AppImage" 2>/dev/null \
  || ARCH=${ARCH:-x86_64} appimagetool "$app" "$repo/dist/T003-Label-Studio-$version-x86_64.AppImage"
