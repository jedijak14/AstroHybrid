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

## Icons

All glyphs are stroked `Path` geometry on a 20x20 grid with a 1.4-1.5 px stroke,
round caps and joins, and `Fill="Transparent"` -- the stroke is what carries the
colour, so a glyph inherits the active brush.

| Where | Source |
| --- | --- |
| Sidebar | `IconHome`, `IconGraphics`, `IconController`, `IconAdvanced`, `IconInstallation` in `MainWindow.xaml` |
| Connected controllers | `IconPadPs`, `IconPadXbox`, `IconPadSwitch`, `IconPadGeneric` in `MainWindow.xaml`, selected by `ControllerTypeToIconConverter` |
| Installation buttons | `ButtonGlyphStyle` + inline geometry in `InstallationView.xaml` |

`ControllerTypeToIconConverter` returns the **key** of a geometry, and the view
binds that key to a `Path.Data`. It used to return Segoe MDL2 private-use
characters, which render as empty boxes in any other font -- that is why the
controller list used to look broken.

Nav glyphs are drawn at 18 px and the pad glyphs at 22 px; both were checked at
that size, because a glyph that reads well at 120 px can collapse to a smear.
The 20x20 grid gives 1.5 px of margin all round so nothing clips.

## Scrollbars and tooltips

`ScrollBar` and `ToolTip` have app-wide styles in `Styles.xaml`. WPF's defaults
draw a light grey trough with arrow buttons and a white drop-shadowed tooltip on
top of a near-black window, which looks broken rather than stock.

## Key caps

`KeyCapStyle` + `KeyCapTextStyle` (mono) render an in-game key. They are used on
Home for F2, Ctrl+F2, Shift+F2 and F11. Only bindings that exist in the game
patches belong here -- an earlier draft listed F12 for screenshots, which the
port does not implement.

## AMD Radeon features card

The Graphics page has a second feature card, `AMD Radeon features`, directly
under `NVIDIA RTX features` and built the same way (section header, muted
detected-hardware line, rows, note).

**These are driver features, not game features.** Fluid Motion Frames (AFMF)
and Radeon Super Resolution (RSR) live in AMD Software: Adrenalin and are turned
on there, per game. Nothing in the port can enable them, so the card does the
two things it can:

1. it says which Radeon card was found and whether AMD's support list covers it
   (`HardwareDetector`: `RadeonSeries`, parsed from the four-digit model in the
   adapter name - `RX 7900 XTX` -> 7900, `RX 6600M` -> 6600; `RX 580` and Vega
   are deliberately not matched, so they read as unsupported);
2. it puts the game in the state the driver needs, and says so in the note.

| Control | Effect on the settings | Why |
| --- | --- | --- |
| `AMD Fluid Motion Frames` | `Fullscreen = true`, `VSync = false`, `Fps = 6` (No limit); turns NVIDIA frame generation off | AFMF needs fullscreen with VSync off; the driver interpolates from whatever the game presents, so a cap is counter-productive. Two frame generators cannot both be right. |
| `Radeon Super Resolution` | `Fullscreen = false`, `AmdRenderSize` applied, turns DLSS off | RSR scales from the game's render resolution up to the screen, which needs a window, not an exclusive display. Stacking two upscalers is what AMD warns against. |
| `Render resolution` | 720p / 900p / 1080p, or the screen's own resolution (RSR then does nothing) | RSR only has work to do below the screen's resolution. Disabled unless RSR is on. |

Both settings are stored separately (`amdfmf`, `amdrsr`, `amdsize`) so turning
one off does not disturb the other, and both are skipped at launch on a card
`HardwareDetector` does not rate for them. `ApplyBestSettings` leaves them off -
at 30 FPS the port is far below the rate AFMF is meant for, so it stays the
user's choice - but pre-picks a render resolution for RSR.

The section is enabled only on a supported Radeon card (`SupportsAmd`) and
`AmdFeaturesNote` explains which of the three states applies: supported card,
unsupported AMD card, or no AMD card in the machine.

`Tools/brand/render_screenshots.js` shows the card greyed out on the NVIDIA
machine the screenshots are taken on, and `app-graphics.png` is rendered
scrolled down so the card is visible.
