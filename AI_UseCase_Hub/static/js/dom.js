// Hilfen für den Seitenaufbau. Inhalte werden immer als Text eingesetzt,
// nie als HTML (Konzept 6.4).

export function h(tag, attrs, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs || {})) {
    if (value === false || value === null || value === undefined) continue;
    if (key === "class") el.className = value;
    else if (key.startsWith("on")) el.addEventListener(key.slice(2), value);
    else if (value === true) el.setAttribute(key, "");
    else el.setAttribute(key, value);
  }
  add(el, children);
  return el;
}

export function add(el, children) {
  for (const child of [children].flat(Infinity)) {
    if (child === false || child === null || child === undefined) continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return el;
}

const ICONS = {
  check: ["M3 8.5l3.2 3.2L13 4.8"],
  alert: ["M8 2.2L14.5 13.5H1.5L8 2.2z", "M8 6.5v3.2", "M8 11.6v.1"],
  circle: ["M8 2.5a5.5 5.5 0 1 0 0 11a5.5 5.5 0 0 0 0-11z"],
  dash: ["M4 8h8"],
  lock: ["M4 7.5h8v6H4z", "M5.8 7.5V5.4a2.2 2.2 0 0 1 4.4 0v2.1"],
  folder: ["M1.8 4h4.4l1.4 1.6h6.6v7.4H1.8z"],
  file: ["M4 1.8h5.2L12 4.6v9.6H4z", "M9 1.8v3h3"],
  arrow: ["M3 8h10", "M9 4l4 4-4 4"],
  up: ["M8 13V3", "M4 7l4-4 4 4"],
  plus: ["M8 3v10", "M3 8h10"],
  power: ["M8 2v6", "M4.6 4.4a5 5 0 1 0 6.8 0"],
  x: ["M4 4l8 8", "M12 4l-8 8"],
};

export function icon(name, label) {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", "0 0 16 16");
  svg.setAttribute("class", "icon");
  if (label) {
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", label);
  } else {
    svg.setAttribute("aria-hidden", "true");
  }
  for (const d of ICONS[name] || []) {
    const path = document.createElementNS(ns, "path");
    path.setAttribute("d", d);
    svg.append(path);
  }
  return svg;
}

export function emptyState(text) {
  return h("p", { class: "empty" }, text);
}

export function pageHead(title, subtitle, action) {
  return h("div", { class: "page-head" },
    h("div", null, h("h1", null, title), subtitle ? h("p", null, subtitle) : null),
    action || null);
}

export function formatDate(iso) {
  if (!iso) return "";
  const [year, month, day] = iso.slice(0, 10).split("-");
  return `${day}.${month}.${year}`;
}
