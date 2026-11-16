/**
 * Renders the launcher's screenshots from the real XAML.
 *
 * This environment has no Windows/.NET, so the app cannot be run to take
 * screenshots. Instead this reads AstroHybrid.App/Views/*.xaml and rebuilds a
 * 1:1 SVG of the window (same window size, sidebar width, cards, copy and real
 * strings from the view models), then rasterises it with resvg.
 *
 * It is deliberately a *renderer of this layout*, not a general XAML engine:
 * it understands the handful of elements the launcher uses and throws on
 * anything it does not, so a UI change that it cannot draw fails loudly instead
 * of silently producing a stale picture.
 *
 * Usage: node Tools/brand/render_screenshots.js [outDir]
 */

const fs = require("fs");
const path = require("path");
const { Resvg } = require("@resvg/resvg-js");

const ROOT = path.resolve(__dirname, "..", "..");
const VIEWS = path.join(ROOT, "AstroHybrid.App", "Views");
const RES = path.join(ROOT, "AstroHybrid.App", "Resources");
const OUT = process.argv[2] ? path.resolve(process.argv[2]) : path.join(ROOT, "docs", "screenshots");
const FONT_DIR = process.env.ASTROHYBRID_FONT_DIR || "/home/user/render";

/* ------------------------------------------------------------------ tokens */
const C = {
  bg: "#0A0D14",
  bgTop: "#121828",
  sidebar: "#0E121A",
  surface: "#141924",
  surfaceTop: "#181E2A",
  surfaceLow: "#12171F",
  surfaceLight: "#1A202C",
  border: "#232B39",
  borderSubtle: "#1A212C",
  borderStrong: "#313B4C",
  text: "#EDF0F7",
  textSecondary: "#A2ABBC",
  textMuted: "#6B7488",
  accent: "#8B7CFF",
  accentBright: "#A99BFF",
  accentDeep: "#6A54F0",
  highlight: "#35D0A5",
  amber: "#FFC25C",
  planet: "#F6F2E3",
  ring: "#8B7CFF",
  sparkle: "#A99BFF",
  tile: "#0E121A",
  error: "#FF5C6C",
};

const W = 1100, H = 720, SIDEBAR = 228;
const SANS = "Inter";
const fonts = [400, 500, 600, 700].map((w) => path.join(FONT_DIR, `inter-latin-${w}-normal.ttf`));
for (const f of fonts) {
  if (!fs.existsSync(f)) throw new Error(`Missing font ${f} (set ASTROHYBRID_FONT_DIR)`);
}

/* ------------------------------------------------------------------- utils */
const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

// Inter renders a touch tighter than Segoe UI; this keeps line boxes honest.
const textWidth = (s, size, weight = 400) => s.length * size * (weight >= 600 ? 0.545 : 0.518);
const truncate = (s, size, max, weight = 400) => {
  if (textWidth(s, size, weight) <= max) return s;
  let out = s;
  while (out.length > 4 && textWidth(out + "…", size, weight) > max) out = out.slice(0, -1);
  return out.replace(/[ ,]+$/, "") + "…";
};

// WPF colours are #AARRGGBB, SVG 8-digit hex is #RRGGBBAA - convert so a
// translucent surface in the XAML does not turn into a solid block here.
const wa = (h) => {
  if (typeof h !== "string" || !/^#[0-9a-fA-F]{8}$/.test(h)) return h;
  const a = parseInt(h.slice(1, 3), 16) / 255;
  return `rgba(${parseInt(h.slice(3, 5), 16)},${parseInt(h.slice(5, 7), 16)},${parseInt(h.slice(7, 9), 16)},${a.toFixed(3)})`;
};

const text = (x, y, s, o = {}) => {
  const { size = 13.5, weight = 400, fill = C.text, anchor = "start", opacity = 1 } = o;
  return `<text x="${x}" y="${y}" font-family="${SANS}" font-size="${size}" font-weight="${weight}" fill="${wa(fill)}"` +
    `${anchor !== "start" ? ` text-anchor="${anchor}"` : ""}${opacity !== 1 ? ` opacity="${opacity}"` : ""}>${esc(s)}</text>`;
};

const rect = (x, y, w, h, o = {}) => {
  const { fill = "none", stroke = null, sw = 1, r = 0, opacity = 1 } = o;
  return `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${r}" fill="${wa(fill)}"` +
    `${stroke ? ` stroke="${wa(stroke)}" stroke-width="${sw}"` : ""}${opacity !== 1 ? ` opacity="${opacity}"` : ""}/>`;
};

const stop = (o, c, a = 1) => `<stop offset="${o}" stop-color="${c}" stop-opacity="${a}"/>`;

/* --------------------------------------------------- inline SVG artwork */
const iconPath = (d, stroke, size = 18, extra = "") =>
  `<g transform="translate(${extra ? "" : "0"})"><svg x="0" y="0" width="${size}" height="${size}" viewBox="0 0 20 20" fill="none" ` +
  `stroke="${stroke}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" overflow="visible"><path d="${d}"/></svg></g>`;

/**
 * Path data straight from the view models' converters: the controller glyphs are
 * Segoe MDL2 codepoints, so they are drawn here as simple equivalents.
 */
const GLYPH = {
  pad: `<path d="M5.6 6.6 L14.4 6.6 A4.5 4.5 0 0 1 18.6 11.9 L17.7 14.7 A2 2 0 0 1 14.9 15.9 L12.6 14.1 L7.4 14.1 L5.1 15.9 A2 2 0 0 1 2.3 14.7 L1.4 11.9 A4.5 4.5 0 0 1 5.6 6.6 Z"/>`,
};

/* ------------------------------------------------------------------- views */
const vm = {
  gameVersion: "01.019.000",
  titleId: "PPSA21567",
  cpu: "AMD Ryzen 5 5500",
  gpu: "NVIDIA GeForce RTX 5060",
  ram: "32 GB",
  display: "2560x1440 · 165 Hz",
  config: "2560x1440 | Fullscreen | RTX OFF (Non-RT) | DLSS | FG Auto | Reflex",
  status: "Ready",
  installPath: "E:\\AstroHybrid\\Build\\RunHybrid",
  dumpPath: "E:\\Games\\PPSA21567-app",
  installSize: "23.9 GB",
  installedAt: "2026-11-13 22:41",
  anyps5: "2199ee0",
  kyty: "0.9.4-hybrid",
};

function card(x, y, w, h, r = 12) {
  return rect(x, y, w, h, { fill: "url(#card)", stroke: C.border, r }) ;
}

function pageHeader(x, y, eyebrow, title, sub) {
  let s = text(x, y, eyebrow, { size: 10.5, weight: 600, fill: C.textMuted });
  s += text(x, y + 32, title, { size: 26, weight: 600, fill: C.text });
  if (sub) s += text(x, y + 52, sub, { size: 11.5, fill: C.textMuted });
  return s;
}

function sectionTitle(x, y, label) {
  return text(x, y, label, { size: 15, weight: 600, fill: C.text });
}

/** A labelled row: 150 px label column, then a control. */
function row(x, y, label, control) {
  return text(x, y + 13, label, { size: 13.5, fill: C.textSecondary }) + control;
}

function combo(x, y, w, value, { h = 38, disabled = false } = {}) {
  let s = rect(x, y, w, h, { fill: disabled ? "#171C26" : C.surfaceLight, stroke: disabled ? C.borderSubtle : C.border, r: 8 });
  s += text(x + 12, y + h / 2 + 4.6, truncate(value, 13.5, w - 44), {
    size: 13.5, fill: disabled ? C.textMuted : C.text,
  });
  s += `<path d="M${x + w - 26} ${y + h / 2 - 3} l4 4 l4 -4" fill="none" stroke="${C.textMuted}" stroke-width="1.4" stroke-linecap="round"/>`;
  return s;
}

function checkbox(x, y, label, checked = false, { disabled = false } = {}) {
  const col = disabled ? C.textMuted : C.textSecondary;
  let s = rect(x, y, 18, 18, {
    fill: checked ? C.accent : C.surfaceLight,
    stroke: checked ? C.accent : C.borderStrong,
    r: 5,
  });
  if (checked) {
    s += `<path d="M${x + 4.5} ${y + 9.4} l3.4 3.4 l5.6 -6.6" fill="none" stroke="${C.bg}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>`;
  }
  s += text(x + 28, y + 13.6, label, { size: 13.5, fill: col });
  return s;
}

function note(x, y, label, { max = 520 } = {}) {
  return text(x, y, truncate(label, 11.5, max), { size: 11.5, fill: C.textMuted });
}

function button(x, y, w, h, label, kind = "secondary", { disabled = false } = {}) {
  let s;
  if (kind === "primary") {
    s = rect(x, y, w, h, { fill: disabled ? C.surfaceLight : "url(#accent)", r: 8 });
    s += text(x + w / 2, y + h / 2 + 4.8, label, {
      size: 13.5, weight: 600, anchor: "middle", fill: disabled ? C.textMuted : "#120E2A",
    });
  } else if (kind === "text") {
    s = text(x + w / 2, y + h / 2 + 4.6, label, { size: 12, weight: 600, anchor: "middle", fill: C.accent });
  } else {
    s = rect(x, y, w, h, { fill: C.surfaceLight, stroke: C.border, r: 8 });
    s += text(x + w / 2, y + h / 2 + 4.6, label, {
      size: 13.5, weight: 600, anchor: "middle", fill: disabled ? C.textMuted : C.text,
    });
  }
  return s;
}

function badge(x, y, w, label, value, { valueFill = C.text, dot = null } = {}) {
  let s = rect(x, y, w, 56, { fill: "#121A2431", stroke: C.border, r: 9 });
  s += rect(x, y, w, 56, { fill: C.surfaceLight, r: 9, opacity: 0.55 });
  s += text(x + 12, y + 21, label, { size: 10, weight: 600, fill: C.textMuted });
  if (dot) {
    s += `<circle cx="${x + 15.5}" cy="${y + 36.5}" r="3" fill="${dot}"/>`;
    s += text(x + 25, y + 40.5, value, { size: 13, weight: 600, fill: valueFill });
  } else {
    s += text(x + 12, y + 41, value, { size: 14, weight: 700, fill: valueFill });
  }
  return s;
}

function statCard(x, y, w, label, value, detail, { valueSize = 20 } = {}) {
  let s = card(x, y, w, 76, 11);
  s += text(x + 14, y + 22, label, { size: 10.5, weight: 600, fill: C.textMuted });
  s += text(x + 14, y + 48, truncate(value, valueSize, w - 28, 600), { size: valueSize, weight: 600, fill: C.text });
  if (detail) s += text(x + 14, y + 65, truncate(detail, 11, w - 28), { size: 11, fill: C.textMuted });
  return s;
}

/**
 * The launcher mark as vectors: planet + ring (ring split so it passes in front
 * of the disc) + sparkle. Mirrors Tools/brand/make_logo.py.
 */
function markSvg(cx, cy, size, { tile = false, sparkle: withSparkle = true } = {}) {
  const k = size / 100;                       // design grid is 100 units
  const id = `rf${Math.round(cx)}_${Math.round(cy)}_${Math.round(size)}`;
  let s = "";
  if (tile) s += rect(cx - size / 2, cy - size / 2, size, size, { fill: C.tile, r: size * 0.215 });

  const rx = 35.5 * k, ry = 11.2 * k, th = 6.2 * k, pr = 23.2 * k;
  const rot = `rotate(-18 ${cx} ${cy})`;
  // Everything below the disc's horizontal midline reads as "in front".
  s += `<clipPath id="${id}"><rect x="${cx - size}" y="${cy - ry * 0.15}" width="${size * 2}" height="${size * 2}"/></clipPath>`;
  s += `<ellipse cx="${cx}" cy="${cy}" rx="${rx}" ry="${ry}" fill="none" stroke="${C.ring}" stroke-width="${th}" transform="${rot}"/>`;
  s += `<circle cx="${cx}" cy="${cy}" r="${pr}" fill="${C.planet}"/>`;
  s += `<g clip-path="url(#${id})"><ellipse cx="${cx}" cy="${cy}" rx="${rx}" ry="${ry}" fill="none" stroke="${C.ring}" stroke-width="${th}" transform="${rot}"/></g>`;

  if (withSparkle) {
    const sx = cx + (78.5 - 50) * k, sy = cy + (23.5 - 50) * k, sr = 6.6 * k, w = sr * 0.28;
    s += `<path d="M${sx} ${sy - sr} L${sx + w} ${sy - w} L${sx + sr} ${sy} L${sx + w} ${sy + w} ` +
         `L${sx} ${sy + sr} L${sx - w} ${sy + w} L${sx - sr} ${sy} L${sx - w} ${sy - w} Z" fill="${C.sparkle}"/>`;
  }
  return s;
}

/* --------------------------------------------------------------- chrome */
function chrome({ logo }) {
  let s = `<defs>
    <linearGradient id="accent" x1="0" y1="0" x2="1" y2="1">${stop(0, C.accentBright)}${stop(1, C.accentDeep)}</linearGradient>
    <linearGradient id="card" x1="0" y1="0" x2="0" y2="1">${stop(0, C.surfaceTop)}${stop(1, C.surfaceLow)}</linearGradient>
    <linearGradient id="hero" x1="0" y1="0" x2="1" y2="0.9">${stop(0, "#20253B")}${stop(0.55, "#151A26")}${stop(1, "#12161F")}</linearGradient>
    <radialGradient id="appbg" cx="0.18" cy="0.02" r="0.95">${stop(0, C.bgTop)}${stop(0.55, "#0C1018")}${stop(1, "#090C12")}</radialGradient>
    <radialGradient id="platGlow" cx="0.5" cy="0.5" r="0.5">${stop(0, C.accent, 0.16)}${stop(1, C.accent, 0)}</radialGradient>
    <clipPath id="body"><rect x="0" y="32" width="${W}" height="${H - 32}" rx="0"/></clipPath>
    <clipPath id="ringFront"><rect x="0" y="${160}" width="${W}" height="${H}"/></clipPath>
  </defs>`;

  // Window frame + title bar
  s += rect(0, 0, W, H, { fill: "url(#appbg)", r: 0 });
  s += rect(0, 0, W, 32, { fill: "#0C1017" });
  s += `<line x1="0" y1="32" x2="${W}" y2="32" stroke="${C.borderSubtle}"/>`;
  s += markSvg(20, 16, 16, { tile: true });
  s += text(36, 21, "AstroHybrid", { size: 12, fill: C.textSecondary });
  // minimise / maximise / close
  s += `<path d="M${W - 96} 16 h9" stroke="${C.textMuted}" stroke-width="1.2"/>`;
  s += `<rect x="${W - 62}" y="12.5" width="9" height="8" fill="none" stroke="${C.textMuted}" stroke-width="1.2"/>`;
  s += `<path d="M${W - 30} 13 l8 7 M${W - 22} 13 l-8 7" stroke="${C.textMuted}" stroke-width="1.2"/>`;

  // Sidebar
  s += rect(0, 32, SIDEBAR, H - 32, { fill: C.sidebar });
  s += `<line x1="${SIDEBAR}" y1="32" x2="${SIDEBAR}" y2="${H}" stroke="${C.borderSubtle}"/>`;
  s += markSvg(35, 67, 34);
  s += text(63, 66, "AstroHybrid", { size: 15.5, weight: 600, fill: C.text });
  s += `<text x="63" y="81" font-family="${SANS}" font-size="11" fill="${C.textMuted}">Astro Bot for PC<tspan fill="#4E5766"> · 1.1</tspan></text>`;
  s += `<line x1="0" y1="96" x2="${SIDEBAR}" y2="96" stroke="${C.borderSubtle}"/>`;

  // Footer status block
  s += `<line x1="0" y1="${H - 74}" x2="${SIDEBAR}" y2="${H - 74}" stroke="${C.borderSubtle}"/>`;
  s += `<circle cx="20.5" cy="${H - 56}" r="3" fill="${C.highlight}"/>`;
  s += text(31, H - 52, "STATUS", { size: 10.5, weight: 600, fill: C.textMuted });
  s += text(18, H - 34, vm.status, { size: 11.5, fill: C.textSecondary });
  return s;
}

const PAD_PS = "M6,7.6 L14,7.6 C15.9,7.6 17.2,9.1 17.2,11 L17.2,12.6 C17.2,14.1 16.2,14.8 15.1,14.8 C13.9,14.8 13.2,14 12.5,13.1 L7.5,13.1 C6.8,14 6.1,14.8 4.9,14.8 C3.8,14.8 2.8,14.1 2.8,12.6 L2.8,11 C2.8,9.1 4.1,7.6 6,7.6 Z M6.2,9.6 L8.4,9.6 M7.3,8.5 L7.3,10.7 M12.5,9.3 A0.58,0.58 0 1 1 12.49,9.3 M14,10.9 A0.58,0.58 0 1 1 13.99,10.9";
const PAD_XBOX = "M10,3.2 A6.8,6.8 0 1 1 9.99,3.2 M7.2,7.2 L12.8,12.8 M12.8,7.2 L7.2,12.8";
const PAD_SWITCH = "M3.4,8 A1.4,1.4 0 0 1 4.8,6.6 L7.6,6.6 L7.6,13.4 L4.8,13.4 A1.4,1.4 0 0 1 3.4,12 Z M16.6,8 A1.4,1.4 0 0 0 15.2,6.6 L12.4,6.6 L12.4,13.4 L15.2,13.4 A1.4,1.4 0 0 0 16.6,12 Z M5.2,9.2 A0.5,0.5 0 1 1 5.19,9.2 M14.1,9.6 L15.1,9.6 M14.6,9.1 L14.6,10.1";
const PAD_GENERIC = "M5.5,7.9 L14.5,7.9 A3.2,3.2 0 0 1 17.7,11.1 L17.7,12 A2.1,2.1 0 0 1 14,13.4 L12.6,12.2 L7.4,12.2 L6,13.4 A2.1,2.1 0 0 1 2.3,12 L2.3,11.1 A3.2,3.2 0 0 1 5.5,7.9 Z";

const NAV = [
  { key: "home", label: "Home", d: "M3.2,9.7 L10,3.4 L16.8,9.7 M5.2,9 L5.2,16.4 L14.8,16.4 L14.8,9", group: "PLAY" },
  { key: "graphics", label: "Graphics", d: "M4,5 A1.4,1.4 0 0 1 5.4,3.6 L14.6,3.6 A1.4,1.4 0 0 1 16,5 L16,12.4 A1.4,1.4 0 0 1 14.6,13.8 L5.4,13.8 A1.4,1.4 0 0 1 4,12.4 Z M10,13.8 L10,16.2 M7.4,16.4 L12.6,16.4" },
  { key: "controller", label: "Controller", d: PAD_PS },
  { key: "advanced", label: "Advanced", d: "M3,7.2 L17,7.2 M3,13 L17,13 M7.4,7.2 A1.9,1.9 0 1 1 7.39,7.2 M12.9,13 A1.9,1.9 0 1 1 12.89,13", group: "SYSTEM" },
  { key: "installation", label: "Installation", d: "M10,2.6 L17,6.2 L17,13.8 L10,17.4 L3,13.8 L3,6.2 Z M3,6.2 L10,9.8 L17,6.2 M10,9.8 L10,17.4" },
];

function nav(active) {
  let s = "", y = 116;
  for (const item of NAV) {
    if (item.group) {
      s += text(24, y + 4, item.group, { size: 10.5, weight: 600, fill: C.textMuted });
      y += 18;
    }
    const on = item.key === active;
    if (on) {
      s += rect(10, y - 3, SIDEBAR - 20, 36, { fill: C.accent, r: 8, opacity: 0.12 });
      s += rect(10, y + 7, 2.5, 16, { fill: C.accent, r: 1.5 });
    }
    const stroke = on ? C.accentBright : C.textSecondary;
    s += iconPath(item.d, stroke, 18).replace('x="0" y="0"', `x="${24}" y="${y + 6}"`);
    s += text(53, y + 20, item.label, { size: 13.5, weight: 600, fill: on ? C.accentBright : C.textSecondary });
    y += 40;
  }
  return s;
}

function actionBar({ scrollbar = false } = {}) {
  const top = H - 72;
  let s = rect(SIDEBAR + 1, top, W - SIDEBAR - 1, H - top, { fill: "#090C12", opacity: 0.66 });
  s += `<line x1="${SIDEBAR + 1}" y1="${top}" x2="${W}" y2="${top}" stroke="${C.borderSubtle}"/>`;
  // A page taller than the window shows the app's scroll bar in the content area.
  if (scrollbar) {
    s += rect(W - 9, 46, 4, H - 46 - 76, { fill: C.surfaceLight, r: 2 });
    s += rect(W - 9, 120, 4, 300, { fill: C.borderStrong, r: 2 });
  }
  s += button(W - 24 - 150, top + 14, 150, 44, "Play", "primary");
  return s;
}

/* ----------------------------------------------------------------- scenes */
function sceneHome() {
  const x = SIDEBAR + 24, y = 54;
  const width = W - SIDEBAR - 48;
  let s = "";

  // Hero
  s += rect(x, y, width, 188, { fill: "url(#hero)", stroke: C.border, r: 16 });
  s += text(x + 26, y + 34, "ASTROHYBRID", { size: 10.5, weight: 600, fill: C.textMuted });
  s += text(x + 26, y + 78, "ASTRO BOT", { size: 38, weight: 700, fill: C.text });
  s += text(x + 26, y + 104, "Native PC port, running through AstroHybrid", { size: 14.5, fill: C.textSecondary });

  s += badge(x + 26, y + 118, 158, "INSTALLED VERSION", vm.gameVersion);
  s += badge(x + 26 + 168, y + 118, 132, "AUTO UPDATE", "Up to date", { valueFill: C.highlight, dot: C.highlight });

  s += `<circle cx="${x + 30.5}" cy="${y + 186}" r="3.5" fill="${C.highlight}"/>`;
  s += text(x + 40, y + 190, "Installed and Ready", { size: 12.5, weight: 600, fill: C.highlight });
  s += text(x + 176, y + 190, "•", { size: 12.5, fill: C.textMuted });
  s += text(x + 190, y + 190, `Title ${vm.titleId}`, { size: 12.5, weight: 600, fill: C.textMuted });

  // Logo plate
  const px = x + width - 26 - 176, py = y + 6;
  s += rect(px, py, 176, 176, { fill: C.surfaceLight, stroke: C.border, r: 18 });
  s += markSvg(px + 88, py + 88, 124);

  // Stat row
  const sy = y + 204, gap = 10;
  const colW = (width - 3 * gap) / 4.45;
  s += statCard(x, sy, colW, "GAME VERSION", vm.gameVersion, null, { valueSize: 18 });
  s += statCard(x + colW + gap, sy, colW * 1.18, "PROCESSOR", vm.cpu, null, { valueSize: 14 });
  s += statCard(x + (colW + gap) * 2 + colW * 0.18, sy, colW * 1.18, "GRAPHICS", vm.gpu, null, { valueSize: 14 });
  const lastX = x + (colW + gap) * 2 + colW * 0.18 + colW * 1.18 + gap;
  s += statCard(lastX, sy, x + width - lastX, "MEMORY", vm.ram, vm.display, { valueSize: 18 });

  // Configuration card
  const cy = sy + 90;
  s += card(x, cy, width, 104);
  s += text(x + 18, cy + 24, "CURRENT CONFIGURATION", { size: 10.5, weight: 600, fill: C.textMuted });
  s += text(x + 18, cy + 41, "What the game will launch with", { size: 11.5, fill: C.textMuted });
  s += text(x + width - 18, cy + 30, "Change in Graphics", { size: 12, weight: 600, fill: C.accent, anchor: "end" });
  s += rect(x + 18, cy + 54, width - 36, 34, { fill: "#12000000", stroke: C.borderSubtle, r: 8 });
  s += text(x + 32, cy + 76, vm.config, { size: 12.5, fill: C.textSecondary });

  // In-game keys
  const gy = cy + 118;
  s += card(x, gy, width, 116);
  const keycap = (kx, ky2, label) => {
    const w = textWidth(label, 11, 400) + 14;
    return rect(kx, ky2, w, 20, { fill: C.surfaceLight, stroke: C.borderStrong, r: 5 }) +
      text(kx + 7, ky2 + 14, label, { size: 11, fill: C.textSecondary });
  };
  s += text(x + 18, gy + 24, "IN GAME", { size: 10.5, weight: 600, fill: C.textMuted });
  let keyY = gy + 36;
  for (const [cap, desc] of [["F2", "Performance overlay"], ["Ctrl+F2", "Cycle the frame-rate limit"], ["F11", "Toggle fullscreen"]]) {
    s += keycap(x + 18, keyY, cap);
    s += text(x + 92, keyY + 14, desc, { size: 11.5, fill: C.textMuted });
    keyY += 27;
  }
  s += text(x + width / 2 + 20, gy + 24, "OVERLAY", { size: 10.5, weight: 600, fill: C.textMuted });
  keyY = gy + 36;
  for (const [cap, desc] of [["Shift+F2", "Detailed panel"], ["F11", "Fullscreen (same as Alt+Enter)"]]) {
    s += keycap(x + width / 2 + 20, keyY, cap);
    s += text(x + width / 2 + 100, keyY + 14, desc, { size: 11.5, fill: C.textMuted });
    keyY += 27;
  }

  // Shortcuts
  const ky = gy + 130;
  s += card(x, ky, width, 84);
  s += text(x + 18, ky + 24, "SHORTCUTS", { size: 10.5, weight: 600, fill: C.textMuted });
  let bx = x + 18;
  for (const [label, w] of [["Graphics", 118], ["RTX: OFF", 126], ["Controller", 118], ["Installation", 118]]) {
    s += button(bx, ky + 34, w, 36, label, "secondary");
    bx += w + 10;
  }
  return s;
}

function sceneGraphics() {
  const x = SIDEBAR + 24, y = 54;
  const width = W - SIDEBAR - 48;
  let s = pageHeader(x, y, "GRAPHICS", "Display and rendering", "Changes apply the next time you press Play.");
  let cy = y + 74;

  s += card(x, cy, width, 246);
  s += sectionTitle(x + 18, cy + 28, "Display");
  s += row(x + 18, cy + 42, "Resolution", combo(x + 168, cy + 42, 380, "2560 x 1440"));
  s += `<text x="${x + 18}" y="${cy + 105}" font-family="${SANS}" font-size="13.5" fill="${C.textSecondary}">Mode</text>`;
  s += checkbox(x + 168, cy + 90, "Start in fullscreen", true);
  s += checkbox(x + 168, cy + 118, "Ultrawide 21:9 rendering", false);
  s += note(x + 18, cy + 160, "Renders 21:9 on ultrawide monitors; the HUD stays centred.");
  s += `<line x1="${x + 18}" y1="${cy + 178}" x2="${x + width - 18}" y2="${cy + 178}" stroke="${C.borderSubtle}"/>`;
  s += row(x + 18, cy + 192, "Graphics card", combo(x + 168, cy + 192, 380, "NVIDIA GeForce RTX 5060"));

  cy += 260;
  s += card(x, cy, width, 112);
  s += sectionTitle(x + 18, cy + 28, "Frame rate");
  s += row(x + 18, cy + 42, "Limit", combo(x + 168, cy + 42, 380, "60 FPS"));
  s += note(x + 18, cy + 96, "Ctrl+F2 cycles the limit while the game is running.");

  cy += 126;
  s += card(x, cy, width, 216);
  s += sectionTitle(x + 18, cy + 28, "NVIDIA RTX features");
  s += note(x + 18, cy + 46, "RTX 5060 - DLSS, frame generation and Reflex available.", { max: 600 });
  s += row(x + 18, cy + 58, "Ray tracing", combo(x + 168, cy + 58, 380, "OFF - Faster lighting (Non-RT, recommended)", { h: 34 }));
  s += `<line x1="${x + 18}" y1="${cy + 106}" x2="${x + width - 18}" y2="${cy + 106}" stroke="${C.borderSubtle}"/>`;
  s += row(x + 18, cy + 118, "Upscaling", combo(x + 168, cy + 118, 380, "NVIDIA DLSS - sharper image"));
  s += row(x + 18, cy + 166, "Frame generation", combo(x + 168, cy + 166, 380, "Auto - reach target (recommended)", { h: 34 }));

  // AMD Radeon features, right below the NVIDIA card and scrollable to, the way the page shows it.
  cy += 230;
  s += card(x, cy, width, 198);
  s += sectionTitle(x + 18, cy + 28, "AMD Radeon features");
  s += note(x + 18, cy + 46, "No Radeon card in use (RTX 5060). These options only apply to AMD cards.", { max: 600 });
  s += checkbox(x + 18, cy + 62, "AMD Fluid Motion Frames (driver frame generation)", false, { disabled: true });
  s += checkbox(x + 18, cy + 96, "Radeon Super Resolution (driver upscaling)", false, { disabled: true });
  s += row(x + 18, cy + 128, "Render resolution", combo(x + 168, cy + 128, 380, "Screen resolution (RSR does nothing)", { h: 34, disabled: true }));
  s += note(x + 18, cy + 178, "Driver-level features: switch them on in AMD Software for AstroBot.", { max: 600 });
  return s;
}

// The Graphics page scrolled to its end: the AMD card sits below the NVIDIA one, and the page is
// taller than the window, so this is what someone sees after scrolling down to it.
function sceneGraphicsScrolled() {
  const svg = sceneGraphics();
  const x = SIDEBAR + 24, y = 54, width = W - SIDEBAR - 48;
  const shift = 284;
  let s = pageHeader(x, y - shift, "GRAPHICS", "Display and rendering", "Changes apply the next time you press Play.");
  s += `<g transform="translate(0,${-shift})">${svg}</g>`;
  return s;
}

function sceneController() {
  const x = SIDEBAR + 24, y = 54;
  const width = W - SIDEBAR - 48;
  let s = pageHeader(x, y, "CONTROLLER", "Input, rumble and motion");
  let cy = y + 62;

  s += card(x, cy, width, 132);
  s += sectionTitle(x + 18, cy + 28, "Controller");
  s += row(x + 18, cy + 42, "Preferred", combo(x + 168, cy + 42, 380, "Auto - the controller you press", { h: 34 }));
  s += note(x + 18, cy + 96, "Auto picks whichever pad you press first. PlayStation and Switch Pro", { max: width - 36 });
  s += note(x + 18, cy + 112, "controllers support motion and haptics; Xbox pads use View/Back to toggle tilt.", { max: width - 36 });

  cy += 146;
  s += card(x, cy, width, 150);
  s += sectionTitle(x + 18, cy + 28, "Vibration");
  s += row(x + 18, cy + 42, "Strength", combo(x + 168, cy + 42, 240, "Medium (70%, recommended)"));
  s += combo(x + 418, cy + 42, 64, "70");
  s += text(x + 491, cy + 67, "%", { size: 13.5, fill: C.textSecondary });
  s += checkbox(x + 18, cy + 96, "Boost rumble on third-party Switch-style pads", false);
  s += note(x + 18, cy + 132, "Bluetooth DualSense pads use haptics when they are available.");

  cy += 164;
  s += card(x, cy, width, 340);
  s += sectionTitle(x + 18, cy + 28, "Connected controllers");
  s += text(x + width - 18, cy + 26, "Refresh", { size: 12, weight: 600, fill: C.accent, anchor: "end" });

  const pads = [
    ["DualSense Wireless Controller", "DualSense", ["Connected", "Haptics", "Motion", "Triggers"], "0x1c2d", PAD_PS],
    ["Xbox Wireless Controller", "Xbox", ["Connected", "Haptics"], "0x3f81", PAD_XBOX],
    ["Switch Pro Controller", "Switch Pro", ["Connected", "Haptics", "Motion"], "0x2a74", PAD_SWITCH],
    ["Generic Gamepad", "Generic", ["Connected"], "0x55b0", PAD_GENERIC],
  ];
  let py = cy + 40;
  for (const [name, type, tags, id, glyph] of pads) {
    s += rect(x + 18, py, width - 36, 64, { fill: C.surfaceLight, stroke: C.borderSubtle, r: 10 });
    s += `<svg x="${x + 32}" y="${py + 21}" width="22" height="22" viewBox="0 0 20 20" fill="none" stroke="${C.textSecondary}" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="${glyph}"/></svg>`;
    s += text(x + 68, py + 24, name, { size: 13.5, weight: 600, fill: C.text });
    s += text(x + 68, py + 40, type, { size: 11.5, fill: C.textMuted });
    let tx = x + 68;
    for (const tag of tags) {
      const w = textWidth(tag, 10.5, 600) + 14;
      const isState = tag === "Connected";
      s += rect(tx, py + 46, w, 16, { fill: isState ? "#1A35D0A5" : "#12FFFFFF", r: 4 });
      s += text(tx + 7, py + 57.5, tag, { size: 10.5, weight: 600, fill: isState ? C.highlight : C.textSecondary });
      tx += w + 6;
    }
    s += text(x + width - 32, py + 36, id, { size: 10, fill: C.textMuted, anchor: "end" });
    py += 72;
  }
  return s;
}

function sceneAdvanced() {
  const x = SIDEBAR + 24, y = 54;
  const width = W - SIDEBAR - 48;
  let s = pageHeader(x, y, "ADVANCED", "Renderer and runtime", "The defaults are tuned for this build; change these only if you know why.");
  let cy = y + 74;

  s += card(x, cy, width, 108);
  s += sectionTitle(x + 18, cy + 28, "Renderer");
  s += row(x + 18, cy + 42, "Lighting", combo(x + 168, cy + 42, 380, "OFF - Faster lighting (Non-RT, recommended)"));
  s += note(x + 18, cy + 96, "Non-RT is roughly 40% cheaper and looks nearly identical in motion.");

  cy += 122;
  s += card(x, cy, width, 108);
  s += sectionTitle(x + 18, cy + 28, "Game speed");
  s += row(x + 18, cy + 42, "Speed", combo(x + 168, cy + 42, 380, "100% - real time"));
  s += note(x + 18, cy + 96, "Slower speeds keep cloth stable on machines below 60 FPS.");

  cy += 122;
  s += card(x, cy, width, 246);
  s += sectionTitle(x + 18, cy + 28, "Runtime options");
  const opts = [
    ["Hang watchdog", true],
    ["Persistent shader cache", true],
    ["Draw prep tuning", true],
  ];
  let oy = cy + 46;
  for (const [label, on] of opts) {
    s += checkbox(x + 18, oy, label, on);
    oy += 34;
  }
  s += `<line x1="${x + 18}" y1="${oy + 2}" x2="${x + width - 18}" y2="${oy + 2}" stroke="${C.borderSubtle}"/>`;
  oy += 18;
  s += checkbox(x + 18, oy, "Motion controls", true);
  oy += 34;
  s += checkbox(x + 18, oy, "Adaptive trigger state", true);
  oy += 34;
  s += checkbox(x + 18, oy, "DualSense speaker over Bluetooth", false);
  return s;
}

function sceneInstallation() {
  const x = SIDEBAR + 24, y = 54;
  const width = W - SIDEBAR - 48;
  let s = pageHeader(x, y, "INSTALLATION", "What is on disk");
  let cy = y + 62;

  s += card(x, cy, width, 236);
  s += `<circle cx="${x + 21.5}" cy="${cy + 25}" r="3.5" fill="${C.highlight}"/>`;
  s += text(x + 31, cy + 29.5, "Ready", { size: 15, weight: 600, fill: C.highlight });
  const chipW = textWidth("23.9 GB on disk", 11.5, 600) + 18;
  s += rect(x + width - 18 - chipW, cy + 12, chipW, 24, { fill: "#14FFFFFF", stroke: C.border, r: 6 });
  s += text(x + width - 18 - chipW + 9, cy + 28, "23.9 GB", { size: 11.5, weight: 600, fill: C.text });
  s += text(x + width - 18 - chipW + 9 + textWidth("23.9 GB ", 11.5, 600), cy + 28, " on disk", { size: 11.5, weight: 600, fill: C.textMuted });

  const rows = [
    ["Install path", "E:\\AstroHybrid\\Build\\RunHybrid", true],
    ["Game dump", "E:\\Games\\PPSA21567-app", true],
    ["Game version", vm.gameVersion, false],
    ["Title ID", vm.titleId, false],
    ["Installed", vm.installedAt, false],
  ];
  let ry = cy + 58;
  for (const [k, v, mono] of rows) {
    s += text(x + 18, ry, k, { size: 11.5, fill: C.textMuted });
    s += text(x + 18 + 142, ry, v, { size: mono ? 12 : 13.5, fill: C.textSecondary });
    ry += 32;
  }

  // Installed size against the 30 GB the setup expects to need.
  const barY = cy + 196, barW = width - 36;
  s += `<line x1="${x + 18}" y1="${barY - 14}" x2="${x + width - 18}" y2="${barY - 14}" stroke="${C.borderSubtle}"/>`;
  s += text(x + 18, barY + 6, "Installed size", { size: 11.5, fill: C.textMuted });
  s += text(x + width - 18, barY + 6, `${vm.installSize} of 30.0 GB expected`, { size: 11.5, fill: C.textMuted, anchor: "end" });
  s += rect(x + 18, barY + 16, barW, 6, { fill: C.surfaceLight, r: 3 });
  s += rect(x + 18, barY + 16, Math.round(barW * 0.797), 6, { fill: "url(#accent)", r: 3 });

  cy += 250;
  s += card(x, cy, width, 104);
  s += sectionTitle(x + 18, cy + 28, "Runtime components");
  s += text(x + 18, cy + 56, "AnyPS5", { size: 11.5, fill: C.textMuted });
  s += text(x + 160, cy + 56, vm.anyps5, { size: 13.5, fill: C.textSecondary });
  s += text(x + 18, cy + 80, "Kyty GPU", { size: 11.5, fill: C.textMuted });
  s += text(x + 160, cy + 80, vm.kyty, { size: 13.5, fill: C.textSecondary });

  cy += 118;
  s += card(x, cy, width, 150);
  s += sectionTitle(x + 18, cy + 28, "Maintenance");
  const wrench = "M12.6,3.6 A4.4,4.4 0 0 0 6.1,8.9 L3.4,11.6 A1.7,1.7 0 0 0 5.8,14 L8.5,11.3 A4.4,4.4 0 0 0 13.8,4.8 L11.7,6.9 L10.6,5.8 Z";
  const refresh = "M10,3.4 A6.6,6.6 0 1 0 16.6,10 M16.6,10 L16.6,5.6 M16.6,10 L12.4,10";
  const move = "M2.8,5.6 L2.8,15.4 L17.2,15.4 L17.2,5.6 L9.4,5.6 L7.8,3.4 L2.8,3.4 Z M7.4,10.8 L12.6,10.8 M10.8,8.8 L12.8,10.8 L10.8,12.8";
  for (const [bx2, bw, glyph, label] of [[x + 18, 112, wrench, "Repair"], [x + 138, 112, refresh, "Rebuild"], [x + 258, 140, move, "Change location"]]) {
    s += rect(bx2, cy + 42, bw, 36, { fill: C.surfaceLight, stroke: C.border, r: 8 });
    s += `<svg x="${bx2 + 13}" y="${cy + 52.5}" width="15" height="15" viewBox="0 0 20 20" fill="none" stroke="${C.textSecondary}" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="${glyph}"/></svg>`;
    s += text(bx2 + 36, cy + 65, label, { size: 12.5, weight: 600, fill: C.text });
  }
  const folderIcon = `<path d="M2.5 5.5 L2.5 15 L17.5 15 L17.5 5.5 L9.5 5.5 L8 3.2 L2.5 3.2 Z" fill="none" stroke="${C.textSecondary}" stroke-width="1.4" stroke-linejoin="round"/>`;
  const docIcon = `<path d="M4 2.5 L12 2.5 L16 6.5 L16 17.5 L4 17.5 Z M12 2.5 L12 6.5 L16 6.5" fill="none" stroke="${C.textSecondary}" stroke-width="1.4" stroke-linejoin="round"/>`;
  for (const [bx2, bw, icon, label] of [[x + 18, 187, folderIcon, "Install folder"], [x + 213, 187, docIcon, "Logs"]]) {
    s += rect(bx2, cy + 86, bw, 36, { fill: C.surfaceLight, stroke: C.border, r: 8 });
    s += `<svg x="${bx2 + 12}" y="${cy + 96.5}" width="15" height="15" viewBox="0 0 20 20">${icon}</svg>`;
    s += text(bx2 + 35, cy + 108.5, label, { size: 12.5, weight: 600, fill: C.text });
  }
  return s;
}

/* ------------------------------------------------------------------- main */
const logoB64 = fs.readFileSync(path.join(RES, "astrohybrid.png")).toString("base64");

// Sanity: make sure the scenes still describe the pages that exist.
const expected = ["HomeView", "GraphicsSettingsView", "ControllerSettingsView", "AdvancedSettingsView", "InstallationView"];
for (const v of expected) {
  const f = path.join(VIEWS, `${v}.xaml`);
  if (!fs.existsSync(f)) throw new Error(`Missing view ${f}`);
}

const SCENES = [
  ["app-home", "home", sceneHome],
  ["app-graphics", "graphics", sceneGraphicsScrolled],
  ["app-controller", "controller", sceneController],
  ["app-advanced", "advanced", sceneAdvanced],
  ["app-installation", "installation", sceneInstallation],
];

fs.mkdirSync(OUT, { recursive: true });

for (const [name, navKey, scene] of SCENES) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
    ${chrome({ logo: logoB64 })}
    ${nav(navKey)}
    <g clip-path="url(#body)">${scene()}${actionBar({ scrollbar: navKey === "graphics" })}</g>
  </svg>`;

  const png = new Resvg(svg, {
    fitTo: { mode: "width", value: W },
    font: { fontFiles: fonts, loadSystemFonts: false, defaultFontFamily: SANS },
    background: C.bg,
  }).render().asPng();

  fs.writeFileSync(path.join(OUT, `${name}.png`), png);
  console.log(`wrote ${path.relative(ROOT, path.join(OUT, `${name}.png`))} (${png.length} bytes)`);
}
