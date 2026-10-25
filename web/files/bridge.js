// Files seam, desktop adapter: the shell's native save dialog through the bridge (src/t003gui/bridge.py). Copying an
// image uses the window's own clipboard where it allows it.

import { copyImage } from "./browser.js";

export function createFiles() {
  return {
    async save(bytes, name, mime, kind = "File") {
      let binary = "";
      for (let i = 0; i < bytes.length; i += 0x8000) binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
      return window.pywebview.api.save_file(btoa(binary), name, kind);
    },
    copyImage,
  };
}
