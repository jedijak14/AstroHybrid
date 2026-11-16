# Launcher UI

The launcher is a WPF app (`AstroHybrid.App`). Everything on this page is
presentation only - no game, setup, update or service code is involved.

## Brand

| File | Use |
| --- | --- |
| `AstroHybrid.App/Resources/astrohybrid.ico` | Window title bar, taskbar, `AstroHybrid.exe` |
| `AstroHybrid.App/Resources/astrohybrid.png` | The tiled icon (exe, docs, packaging) |
| `AstroHybrid.App/Resources/astrohybrid-mark.png` | Transparent mark, used in the sidebar and on the Home plate |
| `Docs/images/astrohybrid-logo.png` | Preview sheet |

The mark is deliberately **flat**: a warm off-white planet with a violet ring
and one small sparkle on a near-black tile. Solid fills only - no gradients,
glow, bevel or shadow - because that is what keeps it crisp at 16 px and stops
it looking like generated artwork. Inspiration came from flat planetary logo
marks and the restrained two-colour style used by good app icons.

Two variants exist for a reason: the tile is the same near-black as the
sidebar, so a tiled image would disappear there. The UI uses the transparent
`astrohybrid-mark.png`; the tiled PNG and the ICO are for the shell.

The 16 and 24 px ICO frames are drawn separately (`small_simplified`) with a
thicker ring, no sparkle and tighter margins, because the full mark turns to
noise at that size.

Regenerate:

```bash
python3 Tools/brand/make_logo.py               # PNGs, ICO, preview sheet
powershell -File Tools\release\make_icon.ps1   # same mark, no Python needed
```

## Design tokens

All colours, type sizes and control templates live in
`AstroHybrid.App/Resources/Styles.xaml`. Anything visual should reference a key
from there rather than hard-coding a value:

| Token | Value | Notes |
| --- | --- | --- |
| `AccentBrush` | `#8B7CFF` | the single accent; buttons, active nav, focus rings |
| `AccentGradientBrush` | `#A99BFF` → `#6A54F0` | primary buttons only |
| `AccentDeepColor` | `#6A54F0` | pressed/hover ramps |
| `HighlightBrush` | `#56E0C0` | positive state (installed, up to date) |
| `AmberBrush` | `#FFC25C` | "update available", destructive-adjacent advice |
| `ErrorBrush` | `#FF5C6C` | errors and the remove card |
| `AppBackgroundBrush` | radial `#141A2C` → `#090C12` | window background |
| `SurfaceGradientBrush` | `#181E2A` → `#12171F` | cards |
| `SidebarBrush` | `#0E121A` | navigation rail |

Type: `FontFamilyDisplay` (Segoe UI Variable Display → Segoe UI) for page
titles, body at 13.5 px, mono (`FontFamilyMono`) for paths and the config
readout. Sentence case everywhere; the only uppercase text is the small
`EyebrowTextStyle` kicker above a heading.

Spacing follows an 8 px rhythm: card padding 18/16, gaps 14, control heights 38
(44 for the action bar), corner radii 8 (controls), 12 (cards), 16 (hero).

## Icons

Navigation uses stroked `Path` glyphs defined in `MainWindow.xaml`, not emoji -
emoji ignore the foreground brush, render in colour, and differ between Windows
builds. A glyph inherits the active colour through
`{Binding Foreground, RelativeSource={RelativeSource AncestorType=RadioButton}}`.

## Rules worth keeping

- Never set `TextTransform` or `LetterSpacing` on a `TextBlock`: WPF has no such
  properties and throws when the style is applied.
- Give a `ComboBox` an explicit `Width`; the template has a `MinWidth` but no
  stretch behaviour.
- Put future "tags" in a `WrapPanel`, not a `StackPanel`, so they reflow at the
  900 px minimum window width.
- Cards carry a hairline border and a subtle gradient instead of a drop shadow.

## Screenshots

`docs/screenshots/*.png` are rendered from the XAML with
`Tools/brand/render_screenshots.js`, because the app cannot be run in the
environment the docs are maintained in. The renderer reads
`AstroHybrid.App/Views/*.xaml`, rebuilds the window at its real 1100x720 size
with the same cards, spacing and copy (plus representative strings from the view
models), and rasterises the result.

```bash
npm i @resvg/resvg-js                      # once, plus the Inter woff files
python3 - <<'PY'                           # woff -> ttf, resvg needs ttf
from fontTools.ttLib import TTFont
TTFont("inter-latin-600-normal.woff").save("inter-latin-600-normal.ttf")
PY
ASTROHYBRID_FONT_DIR=<dir with inter-latin-{400,500,600,700}-normal.ttf> \
  node Tools/brand/render_screenshots.js
```

It covers the five pages (`app-home`, `app-graphics`, `app-controller`,
`app-advanced`, `app-installation`). If a page is added or renamed, update the
`SCENES` list - the renderer throws on a missing view rather than quietly
producing a stale picture.

Colours in the XAML are WPF's `#AARRGGBB`; the renderer converts them to
`rgba()` because an eight-digit hex in SVG means `#RRGGBBAA`, which silently
turns a translucent surface into a solid block.

**These are renderings of the layout, not screenshots of a running app.** When
the launcher can be built on Windows, replace them with real captures
(1100x720, dark desktop) - the filenames and the README gallery can stay as they
are.
