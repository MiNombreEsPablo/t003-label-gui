# Porting the Qt UI to the web UI

Goal: one UI (`web/`, plain HTML/JS, no build step) for the browser and the desktop shell, with the Python engine behind
it, so the Qt UI can be retired without losing a feature. Direction and rules are in [AGENTS.md](../AGENTS.md#web-ui-direction-one-ui-for-every-client-wip-on-the-web-ui-branch).
Tick items off as they land. Sizes are rough: **S** an hour or two, **M** a session, **L** several.

The engine, the file formats, the CLI and their tests do not change. Only what Qt draws is redone.

## What the Qt app has (the parity list)

**Content tab** — text (multi-line), QR text, image file (path field, Browse, Paste, clear ×).
**Text tab** — font (the 23 bundled families, grouped by category, previewed in their own face; "Show all installed
fonts" on Linux), bold, italic, size (Auto = largest that fits, or a cap), align, vertical align, effect (7).
**Image tab** — layout (only / left / right / top / bottom / behind) and the picture's share (20–80 %), dither
(Floyd–Steinberg, Bayer 4×4, Bayer 8×8, hard cutoff) with the cutoff slider, brightness, contrast, gamma, pixelate,
mirror, flip, invert, Reset; dimmed until a picture is chosen.
**Decoration tab** — border style (none + 9), background (none + 12), hazard bars.
**Doodle tab** — freehand ink drawn on the preview itself: pen, line, box, oval, eraser, brush size, 12 stickers with a
size, 30-step undo, clear.
**Output** — copies, darkness, printer (USB / Bluetooth + address).
**Preview** — the exact bitmap that prints, live; the gap between stickers is shown and captioned; a hint says when the
text is hidden by "Image only".
**Presets** — save, load, delete named presets (shared with `t003-print --preset`).
**Files** — open / save `.t003label` (the image travels inside), export PNG, drag and drop (a picture or a
`.t003label`), paste a picture, copy the label as an image.
**Menus and keys** — File (open, save, export, print, quit), Edit (paste, clear image, clear doodle, copy label), View ›
Theme, Help (about, updates, report an issue, presets folder); Ctrl+O/S/E/P/V/Shift+C/Q.
**Look** — four themes (Y2K Blue, Y2K Pink, Gunmetal, Handheld) and the system look, remembered between runs: gel
buttons, LED checkboxes, plastic tabs, a glossy banner with the icon, the preview in a chrome bezel, a two-column layout.
**Also** — keyboard focus order, accessible names on every control, remembered settings (theme, last folder, printer).

## Already in `web/` (the slice)

- [x] Live preview from the engine (Pyodide in the browser, native Python in the desktop shell), newest-wins rendering
- [x] Text, font (all 23, from `api.options()`), bold, effect, border (plain)
- [x] Print: Web Bluetooth (browser), USB and Bluetooth with auto-find (desktop shell), status and errors
- [x] Fonts fetched on demand; both clients checked against the native engine byte for byte
- [x] Phone-width layout, dark/light by the system (a placeholder look until Phase 1.5)

## Phase 0 — decisions before more controls (S)

- [x] **Form schema** (`src/t003gui/form.py`): `api.options()["form"]` describes the simple fields (name, kind, label, tab,
      choices, range, tooltip) and `web/form.js` builds the controls from it. Kept: a new effect/background/border in
      `spec.py` needs no UI change, and `tests/test_form.py` fails when a `LabelSpec` field has neither a control nor an
      entry in `PENDING`. The doodle, image picker, font picker and preset bar stay hand-written.
- [x] Tabs + layout shell (ARIA tabs with arrow keys; Output and Print always visible), phone-friendly. Image and Doodle
      tabs appear when their phases land
- [x] A third seam, **store** (settings; `store/local.js`, `store/bridge.js` + `settings.py`). Still to come on it, with
      the phases that need them: presets and open/save/export (browser: localStorage, file input, downloads; desktop
      shell: the bridge, so presets stay in the JSON file the CLI and Qt app read).

## Phase 1 — Decoration and the other simple controls (M)

- [x] Decoration: border style (none + 9), background (none + 12), hazard bars *(the schema trial)*
- [x] Text: italic, size (Auto / cap), align, vertical align
- [x] Content: QR text
- [x] Output: copies, darkness (printer row is done)
- [x] The "Image only hides the text" hint: the rule is `spec.layout_hint`, shared with Qt; the page shows `hints` that
      come with every preview (it only fires once pictures exist, in phase 2)
- [x] Remember the printer choice and Bluetooth address (store seam)
- Checked: 44 label variations driven through the real controls are bit-identical to the native engine (the one
  mismatch was a real bug, `fonts_needed` missing the matrix background's mono font; now fixed and guarded by a test)

## Phase 1.5 — The vibe (M–L, before images, so every control after it is born in the right style)

The web UI is plain dark/light right now; the Qt app is an iMac-G3 candy-plastic Y2K studio with three more looks. The
look is part of the app's point (see "Scope" in AGENTS.md), so it comes before the big controls (sliders, the doodle
toolbar), not after. CSS only: no framework, no build step. The four palettes are copied by hand from `theme.py`, which
goes away with Qt (making them shared data would mean refactoring the frozen Qt UI for a file that is about to be deleted).

- [ ] **Theme tokens**: one set of CSS custom properties (colours, bevel highlight/shadow pairs, gel gradient stops,
      radii, font) that the whole stylesheet uses; no colour is written anywhere else
- [ ] **Y2K Blue first, as the default**: sky-blue gradient window; gel buttons (bright top half, seam, glowing lower
      half) and the orange gel Print button; bevelled inset fields; plastic tabs that join their pane; LED checkboxes
      (green on, hollow off); round-cornered Output group with its caption sitting on the frame
- [ ] **The banner**: the app icon mark (`assets/icon-mark.png`) and "T003 LABEL STUDIO" in the title font, on a glossy plate
- [ ] **The preview as a screen**: chrome bezel around the canvas, the captioned "gap between stickers, not printed"
      strip (preview only), crisp dots
- [ ] **Layout**: two columns on a wide window (controls left, the bezelled preview right, as in the Qt screenshots),
      one column on a phone; the preview stays visible while editing
- [ ] **The other three looks**: Y2K Pink (colour changes only), Gunmetal (black LCD fields, lime text) and Handheld (four
      olive shades, flat, Pixelify Sans, tinted preview), plus "System" (no custom look; dark/light by the OS)
- [ ] **A theme switcher** (View › Theme, or a small picker on a phone) remembered through the store seam; first run
      gets Y2K Blue
- [ ] Fonts for the look (title font, Pixelify Sans) served with the page like the label fonts; they are bundled and
      open-licensed already
- [ ] Check every theme at phone and desktop widths, in the desktop shell's web engine and in a browser, and for
      readable text and visible focus (the select styling already needed a fix in Qt's engine once)
- Cheap first cut if wanted: Y2K Blue + layout + banner + bezel, then the other looks and the switcher

## Phase 2 — Images (L)

- [ ] Picture in: file picker, drag and drop, paste from the clipboard, clear ×. Browser: bytes into Pyodide's file
      system (downscale huge photos in JS first, to keep wasm memory sane); desktop: the bridge writes a temp file
- [ ] Layout (6) and the picture's share
- [ ] Dither (4 modes) with the cutoff slider; brightness, contrast, gamma (log mapping), pixelate; mirror, flip,
      invert; Reset; dimmed until a picture is chosen
- [ ] Load time and memory of Pillow on a phone with a 12-megapixel photo (measure; set a limit if needed)

## Phase 3 — Doodle (L)

- [ ] Drawing surface over the preview, one dot per pixel, hard-edged, pointer events so touch and pen work
- [ ] Tools: pen, line, box, oval, eraser; brush size; undo (30 steps); clear
- [ ] Stickers: the 12 masks come from the engine (`api` returns them), with a size; place on click
- [ ] The doodle crosses as the spec's base64 PNG mask (exactly W×SH, 1-bit), so presets, files and the CLI carry it
- [ ] Faint underlay of the rest of the label while the tab is open

## Phase 4 — Presets, files, themes, shortcuts (L)

- [ ] Presets: save, load, delete (browser: localStorage; desktop: `presets.py` through the bridge)
- [ ] `.t003label`: open and save with the image embedded (engine functions behind `api`, so the format has one
      implementation); drag and drop of either kind of file
- [ ] Export PNG (scale 1–6) and copy the label as an image (Clipboard API; desktop through the bridge if needed)
- (themes moved to Phase 1.5)
- [ ] A menu bar or toolbar for File / Edit / View / Help, and the shortcuts (Ctrl+O/S/E/P/V/Shift+C)
- [ ] Accessible names on every control and a tested keyboard order (Qt had both; so should the web UI)
- [ ] Decide: "Show all installed fonts" (desktop shell only, through the bridge, or drop it), update check (drop on
      the web; keep or drop on desktop), "Open presets folder" (desktop shell only)

## Phase 5 — Publish on GitHub Pages (M)

- [ ] A build step that copies exactly the dev server's layout (`web/`, the engine modules, fonts) into the site
- [ ] Host the `qrcode` wheel (and decide: Pyodide from the CDN, or self-hosted for offline use)
- [ ] A GitHub Actions deploy workflow; project-path base URL works (`/t003-label-gui/`); fonts' licence texts shipped
- [ ] One small CI job: Node + Pyodide renders a fixed set of labels and compares their hashes with the native
      engine (the harness already exists), so the web and desktop engines can't drift apart unnoticed
- [ ] A phone check of the deployed page (print over Web Bluetooth)

## Phase 6 — Desktop packaging and retiring Qt (L, the riskiest, so last)

- [ ] pywebview as a dependency; which web engine each OS uses (WebKitGTK, WebView2, WKWebView, or Qt's) and what
      each needs installed; the page must look right in all of them (the select styling already needed a fix in Qt's)
- [ ] Rework the PyInstaller / AppImage / Windows / macOS builds and the `--selftest` for the shell; keep the CLI
- [ ] Parity gate: every item above ticked, the Qt tests that still mean something re-expressed against `api`/`bridge`
- [ ] Remove `app.py`, `panels.py`, `widgets.py`, `theme.py` and their tests; update the README, screenshots and AGENTS.md
- [ ] Release; the `web-ui` branch merges long before this, as soon as the web UI is usable on its own

## Cross-cutting

- Engine features (a new effect, font, background) are added once in Python and show up in both clients; don't add UI
  features to Qt meanwhile (bug fixes only).
- Tests: Python tests for `api`/`bridge` as now; the parity job in Phase 5; manual phone and desktop-shell checks per
  phase, since Web Bluetooth needs a real phone and Chromium on Linux can't use it with this printer.
- Keep CI small (AGENTS.md): one extra job, not a matrix.
- Windows and macOS shells can't be tested from the Linux dev machine; Bluetooth printing is Linux-tested only.
