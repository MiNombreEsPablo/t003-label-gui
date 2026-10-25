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

- [x] **Theme tokens**: one set of CSS custom properties (colours, bevel highlight/shadow pairs, gel gradient stops,
      radii, font) that the whole stylesheet uses; no colour is written anywhere else
- [x] **Y2K Blue first, as the default**: sky-blue gradient window; gel buttons (bright top half, seam, glowing lower
      half) and the orange gel Print button; bevelled inset fields; plastic tabs that join their pane; LED checkboxes
      (green on, hollow off); round-cornered Output group with its caption sitting on the frame
- [x] **The banner**: the app icon mark (`assets/icon-mark.png`) and "T003 LABEL STUDIO" in the title font, on a glossy plate
- [x] **The preview as a screen**: chrome bezel around the canvas, the captioned "gap between stickers, not printed"
      strip (preview only), crisp dots
- [x] **Layout**: two columns on a wide window (controls left, the bezelled preview right, as in the Qt screenshots),
      one column on a phone; the preview stays visible while editing
- [x] **The other three looks**: Y2K Pink (colour changes only), Gunmetal (black LCD fields, lime text) and Handheld (four
      olive shades, flat, Pixelify Sans, tinted preview, the doodle ink tinted too), plus "System" (flat; dark/light by the OS)
- [x] **A theme switcher**: a "Look" picker under the Print bar for now (it moves into View › Theme with the menus in
      Phase 4), remembered through the store seam; first run gets Y2K Blue; in the browser the saved look is applied before
      the first paint, so there is no flash
- [x] Fonts for the look (Orbitron, VT323, Pixelify Sans: bundled, served on demand like the label fonts) served with the page like the label fonts; they are bundled and
      open-licensed already
- [x] Checked every look at 320, 360, 411, 520 and 960 px (nothing spills out of a panel, all five tabs fit), in the
      browser and the desktop shell's engine, and for contrast (computed for every text/background pair: the Qt palettes
      had never been checked; Gunmetal's buttons and tabs, Handheld's tabs and every look's placeholder text were below
      4.5:1 and are fixed; left as in Qt: the Y2K banner title, 2.9:1 but large type with a hard shadow, and Gunmetal's
      bold Print at 4.4:1). Y2K Blue itself is byte-identical to before (741 computed properties on 39 elements)
- [x] The other looks on the phone (Pixel 7a, Chrome): fine, the pixel font and the dark controls included
- **Phase 1.5 is done.** The preset bar and menu bar that sit in the Qt
  window's top rows arrive with Phase 4

## Phase 2 — Images (L)

- [x] Picture in: file picker, drag and drop, paste from the clipboard (Ctrl+V and a Paste button), clear ×. Both
      clients hand the bytes to `api.adopt_image`, which checks they are a picture, caps them at 40 MB and stores them under
      a content-hash name (browser: Pyodide's file system; desktop: `bridge.upload_image` and a temp file)
- [x] Layout (6) and the picture's share (enabled only for left/right/top/bottom)
- [x] Dither (4 modes) with the cutoff slider (shown only for the hard cutoff); brightness, contrast, gamma (the log
      mapping gives the same values as Qt's at every sampled slider position), pixelate; mirror, flip, invert; Reset;
      the tab dims, with its hint, until a picture is chosen
- Checked: 24 image variations through the real controls are bit-identical to the native engine, except "Behind
  text" with this picture (Pillow 13.0's resize differs from Pyodide's 12.2: same input, 12 % of the dots differ after
  dithering; the browser equals Node-Pyodide exactly). Expect it to disappear when Pyodide ships a newer Pillow
- [x] (Pixel 7a, Chrome) choosing a big photo is quick, nothing felt slow; no load-time note appeared (under 1.5 s)
- [~] Load time and memory of Pillow on a phone with a 12-megapixel photo (the page now says how long a picture took when
      it is over 1.5 s; measure on the Pixel, set a limit or downscale in JS if needed)

## Phase 3 — Doodle (L)

- [x] Drawing surface over the preview, one dot per pixel, hard-edged, pointer events so mouse, touch and pen work
      (`web/doodle.js`; the engine is `web/doodle-raster.js`, pure functions with 15 Node tests)
- [x] Tools: all ten of the Qt canvas (round, square and calligraphy brushes, spray, line, rectangle, ellipse, paint
      bucket, sticker, eraser), five dither inks, brush size, undo (30), Ctrl+Z, clear
- [x] Stickers: the 12 bitmaps come from the engine (`api.options()["stickers"]`), a picker grid, size 1–6×, ghost under
      the pointer, placed on release
- [x] The doodle crosses as the spec's base64 PNG mask (W×SH, white = ink), so presets, files and the CLI carry it. Stored
      doodles load back; a damaged one becomes empty
- [ ] (for Phase 4) Re-encode with `doodle.encode` when saving a preset or file: a browser canvas PNG is 4–8 KB of text,
      the engine's 1-bit PNG a fraction of that
- [x] The rest of the label shows through while drawing: the engine renders the label without its doodle, the overlay
      draws the ink on it, the bucket uses that picture to stop at the text
- Checked: 9 doodles built through the page (every tool kind, patterned inks, a bucket fill stopped by text) decode and
  render natively bit for bit; real mouse input in the browser; the desktop shell's engine; touch on the phone (Pixel 7a, Chrome): works

## Phase 4 — Presets, files, themes, shortcuts (L)

- [ ] Presets: save, load, delete (browser: localStorage; desktop: `presets.py` through the bridge)
- [ ] `.t003label`: open and save with the image embedded (engine functions behind `api`, so the format has one
      implementation); drag and drop of either kind of file
- [x] Export PNG and copy the label as an image (`export-image` branch): "Save image" and "Copy image" under the preview,
      with the Qt app's two sizes (as printed, 4×) and its file naming (the label's first line), both from the engine
      (`api.export_png`, `spec.file_stem`) so every client agrees; a new **files** seam (browser: a download and the
      Clipboard API; desktop shell: the native save dialog through the bridge). The saved PNGs are pixel-identical to the
      native engine's. They move into File / Edit menus with the menu bar. *Copy* was not exercised with a real click in
      the browser here (a clipboard write hung the test tab, which was not focused): try it on the phone and the desktop
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
- [ ] **Instant controls on repeat visits**: the form is built from the engine's options, so it only appears once
      Pyodide has booted (a couple of seconds on the phone). Keep the last options in the store seam, draw the form
      straight away from them, boot the engine in the background and swap the form only if the options changed

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
