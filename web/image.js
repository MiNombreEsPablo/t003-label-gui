// The picture chooser (the schema's "image" field): shows which picture is chosen and lets the user browse, paste or
// remove it. Turning a file into something the engine can use is the page's job: it passes `useFile(file)`.
//   createImageWidget(useFile, say) -> { make(field, notify) -> control, current() }

const ACCEPT = "image/png,image/jpeg,image/bmp,image/gif,image/webp,.png,.jpg,.jpeg,.bmp,.gif,.webp";

const el = (tag, props = {}, ...children) => {
  const node = Object.assign(document.createElement(tag), props);
  node.append(...children);
  return node;
};

export function createImageWidget(useFile, say) {
  let widget = null;

  function make(field, notify) {
    let path = "";
    const nameLabel = el("span", { className: "picture-name" }, "No picture");
    const picker = el("input", { type: "file", accept: ACCEPT, hidden: true });
    const browse = el("button", { type: "button", className: "gel", title: field.tip || "" }, "Browse…");
    const paste = el("button", { type: "button", className: "gel", title: "Paste a picture from the clipboard (Ctrl+V)" }, "Paste");
    const clear = el("button", { type: "button", className: "gel clear", hidden: true }, "×");
    clear.setAttribute("aria-label", "Remove the picture");
    browse.setAttribute("aria-label", "Choose a picture");
    const root = el("div", { className: "picture" }, nameLabel, browse, paste, clear, picker);

    function set(newPath, shownName) {
      path = newPath || "";
      nameLabel.textContent = path ? shownName || path.split("/").pop() : "No picture";
      nameLabel.title = path ? nameLabel.textContent : "";
      clear.hidden = !path;
    }
    browse.addEventListener("click", () => picker.click());
    picker.addEventListener("change", () => {
      const [file] = picker.files;
      picker.value = ""; // choosing the same file again must still fire
      if (file) useFile(file);
    });
    paste.addEventListener("click", async () => {
      try {
        for (const item of await navigator.clipboard.read()) {
          const type = item.types.find((t) => t.startsWith("image/"));
          if (type) return useFile(new File([await item.getType(type)], "pasted picture", { type }));
        }
        say("There is no picture on the clipboard.");
      } catch (_) {
        say("The browser didn't allow reading the clipboard: click on the page and press Ctrl+V instead.");
      }
    });
    clear.addEventListener("click", () => {
      set("");
      notify();
    });

    widget = { root, get: () => path, set, disable: (off) => { browse.disabled = paste.disabled = clear.disabled = off; } };
    return widget;
  }
  return { make, current: () => widget };
}
