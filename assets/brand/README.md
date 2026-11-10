# Stacksmith brand

Three slabs, stacked: compose files layered into one forged system. Together they read as an anvil. The top slab glows **Ember** because that's where the work happens.

## Files

| Folder | File | Use |
| --- | --- | --- |
| `logo/` | `stacksmith-lockup.svg` / `-on-dark.svg` / `-mono.svg` | Primary horizontal lockup |
| | `stacksmith-lockup-stacked.svg` / `-on-dark.svg` / `-mono.svg` | Narrow or square spaces |
| | `stacksmith-mark.svg` / `-on-dark.svg` / `-mono.svg` | Mark on its own |
| | `stacksmith-wordmark.svg` | Wordmark only, `currentColor` |
| `icon/` | `app-icon.svg`, `app-icon-512.png`, `app-icon-192.png` | App / PWA / avatar (Iron tile) |
| | `app-icon-ember.svg` | Alternate on an Ember tile |
| | `apple-touch-icon.png` | 180 × 180 home-screen icon |
| | `favicon.svg`, `favicon.ico`, `favicon-32.png`, `favicon-16.png` | Browser tab |
| `social/` | `social-preview.png` | GitHub social preview, 1280 × 640 |
| `tokens/` | `tokens.css`, `tokens.json` | Colors, type, spacing, radius |

The wordmark is outlined, so the SVGs render without the font installed. The `-mono` files use `currentColor` and take the color of the surrounding text.

## The mark

- Drawn on a 64-unit grid. Slabs are 10 units tall with 4-unit gaps. The horn tapers over 14 units, and the heel has the one 5-unit radius.
- **The middle slab is the axis.** On its own (icons, stacked lockup) the mark is centered on the middle slab, never on the wider face.
- **In horizontal lockups the mark sits tight to the wordmark.** The gap is 0.3 × the mark's width, measured from the heel.
- Clear space: one slab height on every side. Minimum size: mark 16 px, lockup 80 px wide.
- Below 24 px use the favicon cut (`favicon.svg`), drawn on a 16 px grid so every edge lands on a whole pixel.
- Don't recolor the slabs individually, add effects, rotate, or set the wordmark in another font.

## Color

Mostly Iron, one hot spot. Ember is the only brand accent: primary actions, focus, the mark. Status colors only show service state.

| Iron | | Ember | | Status | |
| --- | --- | --- | --- | --- | --- |
| 50 | `#F6F7F9` | 100 | `#FFE6D5` | Healthy | `#1F9D63` |
| 100 | `#ECEEF2` | 400 | `#FF8641` | Warning | `#E0A100` |
| 200 | `#D8DCE3` | **500** | **`#F2610F`** | Error | `#E5484D` |
| 300 | `#B6BCC8` | 600 | `#C9470A` | Info | `#3D8BFD` |
| 400 | `#8E96A6` | 700 | `#B23E06` | | |
| 500 | `#687183` | | | | |
| 600 | `#4A5261` | | | | |
| 700 | `#323844` | | | | |
| 800 | `#22262E` | | | | |
| 900 | `#16191F` | | | | |
| 950 | `#0E1014` | | | | |

Ember 500 is too light for text on white. Use Ember 700 for links and text on light backgrounds, and Iron 900 text on Ember fills.

## Typography

| Role | Family | Weights |
| --- | --- | --- |
| Display, headings, wordmark | Space Grotesk | 500, 700 |
| Body and UI | Inter | 400, 500, 600 |
| Code, hostnames, env vars, labels | JetBrains Mono | 400, 500 |

All three are open source (SIL OFL) and on Google Fonts. Scale: display 64/68, h1 44/48, h2 32/38, h3 24/30, body 16/26, small 14/22, code 14/22, label 12/16 uppercase +0.08em.

## Spacing and shape

- 4 px base: 4, 8, 12, 16, 24, 32, 48, 64, 96.
- Radius: `sm` 3 (inputs, tags), `md` 6 (buttons, code), `lg` 10 (cards, panels), `pill` (status only).
- Depth comes from 1 px borders and the Iron ramp, not shadows. Controls are 44 px tall.

## Using it

Logo in a Markdown file, switching with the reader's theme:

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/brand/logo/stacksmith-lockup-on-dark.svg">
  <img alt="Stacksmith" src="assets/brand/logo/stacksmith-lockup.svg" height="48">
</picture>
```

Tokens in a web UI:

```html
<link rel="stylesheet" href="assets/brand/tokens/tokens.css">
<style>
  body { background: var(--ss-ground); color: var(--ss-text); font: var(--ss-type-body); }
  .primary { background: var(--ss-accent); color: var(--ss-on-accent); border-radius: var(--ss-radius-md); }
</style>
```

Role variables (`--ss-ground`, `--ss-surface`, `--ss-border`, `--ss-text`, `--ss-text-muted`, `--ss-accent`, `--ss-accent-text`, `--ss-on-accent`) switch automatically for dark mode, or force a theme with `data-theme="light|dark"` on `<html>`.

Set `social/social-preview.png` under the repository's **Settings › General › Social preview**.
