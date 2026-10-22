#!/bin/sh
# Link the launcher and CLI wrapper into ~/.local. Run after creating .venv.
set -e
repo=$(cd "$(dirname "$0")/.." && pwd)
mkdir -p ~/.local/share/applications ~/.local/bin
sed "s|^Exec=.*|Exec=$repo/.venv/bin/t003-gui|" "$repo/packaging/t003-label-gui.desktop" \
    > ~/.local/share/applications/t003-label-gui.desktop
printf '#!/bin/sh\nexec "%s/.venv/bin/t003-print" "$@"\n' "$repo" > ~/.local/bin/print-label
chmod +x ~/.local/bin/print-label
command -v update-desktop-database >/dev/null && update-desktop-database ~/.local/share/applications || true
echo "installed launcher and ~/.local/bin/print-label"
