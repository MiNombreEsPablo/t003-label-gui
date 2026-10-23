#!/bin/sh
# Link the launcher, icons and CLI wrapper into ~/.local. Run after creating .venv.
set -e
repo=$(cd "$(dirname "$0")/.." && pwd)
mkdir -p ~/.local/share/applications ~/.local/bin
sed "s|^Exec=.*|Exec=$repo/.venv/bin/t003-gui|" "$repo/packaging/t003-label-gui.desktop" \
    > ~/.local/share/applications/t003-label-gui.desktop
for size in 16 24 32 48 64 128 256 512; do
    dir=~/.local/share/icons/hicolor/${size}x${size}/apps
    mkdir -p "$dir"
    cp "$repo/packaging/icons/t003-label-gui-$size.png" "$dir/t003-label-gui.png"
done
printf '#!/bin/sh\nexec "%s/.venv/bin/t003-print" "$@"\n' "$repo" > ~/.local/bin/print-label
chmod +x ~/.local/bin/print-label
command -v update-desktop-database >/dev/null && update-desktop-database ~/.local/share/applications || true
command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q -t ~/.local/share/icons/hicolor || true
echo "installed launcher, icons and ~/.local/bin/print-label"
