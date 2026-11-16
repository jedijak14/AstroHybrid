# Launcher UI

The launcher is a WPF app (`AstroHybrid.App`). Everything on this page is
presentation only - no game, setup, update or service code is involved.

## Brand

| File | Use |
| --- | --- |
| `AstroHybrid.App/Resources/astrohybrid.ico` | Window title bar, taskbar, `AstroHybrid.exe` |
| `AstroHybrid.App/Resources/astrohybrid.png` | Sidebar lockup and the plate on the Home page |
| `Docs/images/astrohybrid-logo.png` | Preview sheet (512 px plus the 16-64 px reductions) |

The mark is a violet badge with a white four-point sparkle and a thin amber
orbit ring. It is drawn from primitives, so it contains no game artwork.

Regenerate it with:

```bash
python3 Tools/brand/make_logo.py          # writes the PNG, ICO and preview
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
