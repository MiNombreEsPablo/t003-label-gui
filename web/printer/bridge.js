// Printer seam, desktop adapter: the native USB or Bluetooth transports through the shell's bridge
// (src/t003gui/bridge.py). Same shape as printer/ble.js.

export function createPrinter() {
  return {
    modes: ["USB", "Bluetooth"],
    // address: for Bluetooth, an address, or "" for the first T003 the system knows
    async print(spec, { mode, address }) {
      const target = mode === "Bluetooth" ? address || "" : null;
      return window.pywebview.api.print_label(JSON.stringify(spec), target);
    },
  };
}
