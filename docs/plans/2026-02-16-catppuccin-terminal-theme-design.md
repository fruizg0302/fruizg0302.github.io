# Catppuccin Terminal Theme — Design Document

## Summary

Full visual redesign of the AstroPaper-based blog using the Catppuccin color palette with subtle terminal aesthetics. The approach is a **theme reskin** — keeping AstroPaper's existing structure, components, routing, and features while overhauling colors, typography, and targeted UI details.

## Goals

- Unique, dev-forward identity that feels personal rather than template-y
- Catppuccin Mocha (dark) + Latte (light) dual-theme support
- Terminal-inspired touches without sacrificing readability or UX
- Preserve all existing features: Pagefind search, OG images, RSS, pagination, accessibility

## Color System

### Dark Mode — Catppuccin Mocha

| Token          | Value     | Catppuccin Name |
|----------------|-----------|-----------------|
| `--background` | `#1e1e2e` | Base            |
| `--foreground` | `#cdd6f4` | Text            |
| `--accent`     | `#cba6f7` | Mauve           |
| `--muted`      | `#313244` | Surface 0       |
| `--border`     | `#45475a` | Surface 2       |
| `--surface-1`  | `#45475a` | Surface 1       |
| `--subtext`    | `#a6adc8` | Subtext 0       |
| `--overlay`    | `#6c7086` | Overlay 0       |

### Light Mode — Catppuccin Latte

| Token          | Value     | Catppuccin Name |
|----------------|-----------|-----------------|
| `--background` | `#eff1f5` | Base            |
| `--foreground` | `#4c4f69` | Text            |
| `--accent`     | `#8839ef` | Mauve           |
| `--muted`      | `#ccd0da` | Surface 0       |
| `--border`     | `#9ca0b0` | Surface 2       |
| `--surface-1`  | `#bcc0cc` | Surface 1       |
| `--subtext`    | `#6c6f85` | Subtext 0       |
| `--overlay`    | `#7c7f93` | Overlay 0       |

### Code Syntax Highlighting (Shiki)

- Light: `catppuccin-latte`
- Dark: `catppuccin-mocha`

## Typography

| Role        | Font            | Weight | Notes                              |
|-------------|-----------------|--------|------------------------------------|
| Headings    | JetBrains Mono  | 600    | Tighter letter-spacing, monospace identity |
| Body        | Inter           | 400    | Optimized for long-form readability |
| Code        | JetBrains Mono  | 400    | Consistent with headings           |
| Nav/UI      | Inter           | 500    | Clean and functional               |

Font loading via Fontsource (self-hosted, no external requests):
- `@fontsource/jetbrains-mono`
- `@fontsource/inter`

Body line-height: ~1.7 for comfortable reading.

## Component Changes

### Code Blocks
- Terminal-window top bar with three colored dots (Catppuccin red/yellow/green) and optional filename
- Background: `--muted` (Surface 0)
- Keep existing copy button, syntax highlighting, diffs

### Cards (Post List)
- Subtle left border accent (`--accent` / Mauve) on hover
- Metadata (date, reading time) in `--subtext`
- Tags as monospace pills with `--surface-1` background

### Navigation / Header
- Breadcrumbs with path-like separators (`~/blog/posts`)
- Active nav uses `--accent` underline
- Theme toggle retained

### Homepage Hero
- Blinking cursor (`_`) after name/tagline
- Colors update via tokens

### Progress Bar (Post Detail)
- Color: `--accent` (Mauve)

### OG Images
- Updated to Catppuccin Mocha palette and JetBrains Mono

### Footer
- Color updates only, minimal structural change
- Social icons: `--foreground` default, `--accent` on hover

## No Changes

- Page routing / URL structure
- Pagination logic
- Search (Pagefind)
- RSS feed
- Responsive breakpoints
- Accessibility (ARIA, skip-to-content, semantic HTML)
- Redirects

## Approach

Theme Reskin of existing AstroPaper v5.5.1 base — swap design tokens, fonts, and targeted component visuals without rewriting structure or logic.
