// Builds the label's simple controls from the description in api.options()["form"], so a choice added in Python shows
// up here without touching this file. The picture, the doodle and the printer are not described there; they have their
// own widgets.
//   buildForm(schema, defaults, onChange) -> { tabs: Element, output: Element, read(): object, write(spec) }
// onChange(field) is called after the user changes a control.

const el = (tag, props = {}, ...children) => {
  const node = Object.assign(document.createElement(tag), props);
  node.append(...children);
  return node;
};

function makeControl(field, defaults) {
  const id = `f-${field.name}`;
  let input;
  switch (field.kind) {
    case "textarea":
      input = el("textarea", { id, rows: 3 });
      break;
    case "text":
      input = el("input", { id, type: "text", autocomplete: "off" });
      break;
    case "toggle":
      input = el("input", { id, type: "checkbox" });
      break;
    case "number":
      input = el("input", { id, type: "number", min: field.minimum, max: field.maximum, step: 1, inputMode: "numeric" });
      if (field.zero_label) input.placeholder = field.zero_label;
      break;
    case "choice": {
      input = el("select", { id });
      if (field.none_label) input.append(new Option(field.none_label, ""));
      const groups = new Map();
      for (const [value, label, group] of field.choices) {
        if (!group) input.append(new Option(label, value));
        else {
          if (!groups.has(group)) groups.set(group, input.appendChild(el("optgroup", { label: group })));
          groups.get(group).append(new Option(label, value));
        }
      }
      break;
    }
    default:
      throw new Error(`unknown field kind ${field.kind}`);
  }
  if (field.tip) input.title = field.tip;
  return input;
}

function setValue(field, input, spec) {
  const value = spec[field.name];
  if (field.kind === "toggle") input.checked = !!value;
  else if (field.kind === "choice") input.value = field.toggle && !spec[field.toggle] ? "" : value;
  else if (field.kind === "number") input.value = field.zero_label && value === 0 ? "" : value;
  else input.value = value;
}

function getValue(field, input, defaults) {
  if (field.kind === "toggle") return { [field.name]: input.checked };
  if (field.kind === "choice") {
    if (!field.toggle) return { [field.name]: input.value };
    return input.value === "" ? { [field.toggle]: false } : { [field.toggle]: true, [field.name]: input.value };
  }
  if (field.kind === "number") {
    const raw = input.value.trim();
    if (raw === "") return { [field.name]: field.zero_label ? 0 : defaults[field.name] };
    const n = Math.round(Number(raw));
    if (Number.isNaN(n)) return { [field.name]: defaults[field.name] };
    return { [field.name]: Math.min(field.maximum, Math.max(field.minimum, n)) };
  }
  return { [field.name]: input.value };
}

// One row per field; fields sharing a row title (Bold, Italic: "Style") go side by side under it.
function layoutFields(fields, controls) {
  const nodes = [];
  for (let i = 0; i < fields.length; i++) {
    const field = fields[i];
    const input = controls.get(field.name);
    if (field.kind === "toggle") {
      const group = [field];
      while (field.row && fields[i + 1] && fields[i + 1].row === field.row) group.push(fields[++i]);
      const checks = group.map((f) => el("label", { className: "check" }, controls.get(f.name), f.label));
      const title = field.row ? el("span", { className: "row-title" }, field.row) : null;
      nodes.push(el("div", { className: title ? "field toggles" : "field toggles bare" }, ...(title ? [title] : []), el("div", { className: "checks" }, ...checks)));
    } else {
      nodes.push(el("div", { className: "field" }, el("label", { htmlFor: input.id }, field.label), input));
    }
  }
  return nodes;
}

export function buildForm(schema, defaults, onChange) {
  const controls = new Map();
  const fields = schema.fields;
  for (const field of fields) {
    const input = makeControl(field, defaults);
    setValue(field, input, defaults);
    input.addEventListener("input", () => onChange(field));
    controls.set(field.name, input);
  }

  // tabs: the ARIA tab pattern, arrows move between them
  const tablist = el("div", { className: "tablist", role: "tablist" });
  const panels = [];
  const buttons = [];
  schema.tabs.forEach((tab, index) => {
    const button = el("button", { type: "button", role: "tab", id: `tab-${tab.id}`, className: "tab" }, tab.label);
    button.setAttribute("aria-controls", `panel-${tab.id}`);
    const panel = el("div", { role: "tabpanel", id: `panel-${tab.id}`, className: "panel" },
      ...layoutFields(fields.filter((f) => f.tab === tab.id), controls));
    panel.setAttribute("aria-labelledby", button.id);
    buttons.push(button);
    panels.push(panel);
    tablist.append(button);
    button.addEventListener("click", () => select(index, false));
    button.addEventListener("keydown", (event) => {
      const last = buttons.length - 1;
      const to = { ArrowRight: index === last ? 0 : index + 1, ArrowLeft: index === 0 ? last : index - 1, Home: 0, End: last }[event.key];
      if (to !== undefined) {
        event.preventDefault();
        select(to, true);
      }
    });
  });
  function select(index, focus) {
    buttons.forEach((button, i) => {
      button.setAttribute("aria-selected", String(i === index));
      button.tabIndex = i === index ? 0 : -1;
      panels[i].hidden = i !== index;
    });
    if (focus) buttons[index].focus();
  }
  select(0, false);

  const output = el("fieldset", { className: "output" }, el("legend", {}, "Output"),
    ...layoutFields(fields.filter((f) => f.tab === "output"), controls));

  return {
    tabs: el("div", { className: "tabs" }, tablist, ...panels),
    output,
    read() {
      return Object.assign({}, ...fields.map((f) => getValue(f, controls.get(f.name), defaults)));
    },
    write(spec) {
      const full = { ...defaults, ...spec };
      for (const f of fields) setValue(f, controls.get(f.name), full);
    },
  };
}
