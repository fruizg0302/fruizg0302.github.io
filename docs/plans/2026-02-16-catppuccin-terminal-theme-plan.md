# Catppuccin Terminal Theme Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reskin the AstroPaper blog with Catppuccin Mocha/Latte colors, JetBrains Mono + Inter typography, and subtle terminal aesthetic touches.

**Architecture:** Swap CSS custom properties, replace the font provider with Fontsource packages, update Shiki themes to Catppuccin, and make targeted component tweaks (breadcrumbs, code blocks, cards, hero cursor). All changes are visual — no routing, logic, or structural changes.

**Tech Stack:** Astro 5, Tailwind CSS 4, Fontsource (@fontsource/jetbrains-mono, @fontsource/inter), Shiki (catppuccin-mocha/latte themes), Satori (OG images)

---

### Task 1: Install Font Packages

**Files:**
- Modify: `package.json`

**Step 1: Install Fontsource packages**

Run: `npm install @fontsource/jetbrains-mono @fontsource/inter`
Expected: Packages added to dependencies in package.json

**Step 2: Commit**

```bash
git add package.json package-lock.json
git commit -m "chore: add @fontsource/jetbrains-mono and @fontsource/inter"
```

---

### Task 2: Replace Font Provider and Update CSS Design Tokens

**Files:**
- Modify: `astro.config.ts` (lines 66-75 — remove experimental fonts block)
- Modify: `src/styles/global.css` (lines 1-30 — replace color tokens and font theme)
- Modify: `src/layouts/Layout.astro` (lines 64-68 — remove `<Font>` component, add Fontsource imports)

**Step 1: Update `astro.config.ts` — remove experimental fonts, update Shiki themes**

Remove the entire `experimental.fonts` array (lines 66-75). Keep `experimental.preserveScriptOrder`. Update Shiki themes from `{ light: "min-light", dark: "night-owl" }` to `{ light: "catppuccin-latte", dark: "catppuccin-mocha" }` (line 30).

```ts
// astro.config.ts — shikiConfig.themes (line 30)
themes: { light: "catppuccin-latte", dark: "catppuccin-mocha" },
```

```ts
// astro.config.ts — experimental block (lines 64-76)
experimental: {
  preserveScriptOrder: true,
},
```

**Step 2: Update `src/layouts/Layout.astro` — remove Font component, add Fontsource imports**

Remove the `import { Font } from "astro:assets";` (line 2) and the `<Font>` element (lines 65-68). Add Fontsource CSS imports in the frontmatter:

```astro
---
import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/jetbrains-mono/400.css";
import "@fontsource/jetbrains-mono/600.css";
// ... rest of imports
```

**Step 3: Update `src/styles/global.css` — replace all color tokens and font references**

Replace the full file content with Catppuccin tokens and dual-font theme:

```css
@import "tailwindcss";
@import "./typography.css";

@custom-variant dark (&:where([data-theme=dark], [data-theme=dark] *));

:root,
html[data-theme="light"] {
  --background: #eff1f5;
  --foreground: #4c4f69;
  --accent: #8839ef;
  --muted: #ccd0da;
  --border: #9ca0b0;
  --surface-1: #bcc0cc;
  --subtext: #6c6f85;
  --overlay: #7c7f93;
}

html[data-theme="dark"] {
  --background: #1e1e2e;
  --foreground: #cdd6f4;
  --accent: #cba6f7;
  --muted: #313244;
  --border: #45475a;
  --surface-1: #45475a;
  --subtext: #a6adc8;
  --overlay: #6c7086;
}

@theme inline {
  --font-heading: "JetBrains Mono", monospace;
  --font-body: "Inter", sans-serif;
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-accent: var(--accent);
  --color-muted: var(--muted);
  --color-border: var(--border);
  --color-surface-1: var(--surface-1);
  --color-subtext: var(--subtext);
  --color-overlay: var(--overlay);
}

@layer base {
  * {
    @apply border-border outline-accent/75;
    scrollbar-width: auto;
    scrollbar-color: var(--color-muted) transparent;
  }
  html {
    @apply overflow-y-scroll scroll-smooth;
  }
  body {
    @apply flex min-h-svh flex-col bg-background font-body text-foreground selection:bg-accent/75 selection:text-background;
  }
  h1, h2, h3, h4, h5, h6 {
    font-family: var(--font-heading);
  }
  a,
  button {
    @apply outline-offset-1 outline-accent focus-visible:no-underline focus-visible:outline-2 focus-visible:outline-dashed;
  }
  button:not(:disabled),
  [role="button"]:not(:disabled) {
    cursor: pointer;
  }
}

@utility max-w-app {
  @apply max-w-3xl;
}

@utility app-layout {
  @apply mx-auto w-full max-w-app px-4;
}

.active-nav {
  @apply underline decoration-wavy decoration-2 underline-offset-8;
}

/* Source: https://piccalil.li/blog/a-more-modern-css-reset/ */
/* Anything that has been anchored to should have extra scroll margin */
:target {
  scroll-margin-block: 1rem;
}
```

**Step 4: Verify the dev server starts without errors**

Run: `npm run dev`
Expected: Server starts, site loads with new Catppuccin colors and fonts. No build errors.

**Step 5: Commit**

```bash
git add astro.config.ts src/styles/global.css src/layouts/Layout.astro
git commit -m "feat: replace color tokens with Catppuccin palette and switch to JetBrains Mono + Inter fonts"
```

---

### Task 3: Update Typography Styles

**Files:**
- Modify: `src/styles/typography.css` (lines 5-92 — update prose overrides for new font tokens)

**Step 1: Update typography.css**

Add heading font-family rule and ensure the prose styles reference the new tokens. Key changes:
- Add `font-family: var(--font-heading)` to h1-h4 selectors
- Code blocks use `font-family: var(--font-heading)` (JetBrains Mono)

```css
@plugin "@tailwindcss/typography";

@layer base {
  .app-prose {
    @apply prose;

    h1,
    h2,
    h3,
    h4,
    th {
      @apply mb-3 text-foreground;
      font-family: var(--font-heading);
    }

    h3 {
      @apply italic;
    }

    p,
    strong,
    ol,
    ul,
    figcaption,
    table,
    code {
      @apply text-foreground;
    }

    a {
      @apply wrap-break-word text-foreground decoration-dashed underline-offset-4 hover:text-accent focus-visible:no-underline;
    }

    ul {
      @apply overflow-x-clip;
    }

    li {
      @apply marker:text-accent;
    }

    hr {
      @apply border-border;
    }

    img {
      @apply mx-auto border border-border;
    }

    figcaption {
      @apply opacity-75;
    }

    table {
      th,
      td {
        @apply border border-border p-2;
      }

      th {
        @apply py-1.5;
      }

      code {
        @apply break-all sm:break-normal;
      }
    }

    code {
      @apply rounded bg-muted/75 p-1 wrap-break-word text-foreground before:content-none after:content-none;
      font-family: var(--font-heading);
    }

    .astro-code code {
      @apply flex-[1_0_100%] bg-inherit p-0;
    }

    blockquote {
      @apply border-s-accent/80 wrap-break-word opacity-80;
    }

    details {
      @apply inline-block cursor-pointer text-foreground select-none [&_p]:hidden [&_ul]:my-0!;
    }

    summary {
      @apply focus-visible:no-underline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-accent focus-visible:outline-dashed;
    }

    pre {
      @apply focus-visible:border-transparent focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-dashed;
    }
  }

  /* ===== Code Blocks & Syntax Highlighting ===== */
  .astro-code {
    @apply flex border bg-(--shiki-light-bg) text-(--shiki-light) outline-border [&_span]:text-(--shiki-light);
  }

  html[data-theme="dark"] .astro-code {
    @apply bg-(--shiki-dark-bg) text-(--shiki-dark) [&_span]:text-(--shiki-dark);
  }

  /* Styles for Shiki transformers */
  .astro-code {
    .line.diff.add {
      @apply relative inline-block w-full bg-green-400/20 before:absolute before:-left-3 before:text-green-500 before:content-['+'];
    }
    .line.diff.remove {
      @apply relative inline-block w-full bg-red-500/20 before:absolute before:-left-3 before:text-red-500 before:content-['-'];
    }
    .line.highlighted {
      @apply inline-block w-full bg-slate-400/20;
    }
    .highlighted-word {
      @apply rounded-sm border border-border px-0.5 py-px;
    }
  }
}
```

**Step 2: Verify typography renders correctly**

Run: `npm run dev`
Expected: Headings render in JetBrains Mono, body text in Inter. Code blocks use JetBrains Mono. Catppuccin syntax highlighting colors visible.

**Step 3: Commit**

```bash
git add src/styles/typography.css
git commit -m "feat: update typography styles for JetBrains Mono headings and code"
```

---

### Task 4: Update Breadcrumb with Terminal-Style Separators

**Files:**
- Modify: `src/components/Breadcrumb.astro` (lines 26-57)

**Step 1: Update Breadcrumb.astro**

Change the "Home" text to `~` and replace `&raquo;` separators with `/`. Update the nav to use monospace font for the terminal path feel:

```astro
<nav class="app-layout mt-8 mb-1" aria-label="breadcrumb">
  <ul
    class="font-light [&>li]:inline [&>li:not(:last-child)>a]:hover:opacity-100"
    style="font-family: var(--font-heading);"
  >
    <li>
      <a href="/" class="opacity-80">~</a>
      <span aria-hidden="true" class="opacity-80">/</span>
    </li>
    {
      breadcrumbList.map((breadcrumb, index) =>
        index + 1 === breadcrumbList.length ? (
          <li>
            <span
              class:list={["capitalize opacity-75", { lowercase: index > 0 }]}
              aria-current="page"
            >
              {decodeURIComponent(breadcrumb)}
            </span>
          </li>
        ) : (
          <li>
            <a href={`/${breadcrumb}/`} class="capitalize opacity-70">
              {breadcrumb}
            </a>
            <span aria-hidden="true">/</span>
          </li>
        )
      )
    }
  </ul>
</nav>
```

**Step 2: Verify breadcrumbs**

Run: `npm run dev`, navigate to a post page.
Expected: Breadcrumb shows `~ / posts / post-name` style with monospace font.

**Step 3: Commit**

```bash
git add src/components/Breadcrumb.astro
git commit -m "feat: update breadcrumbs to terminal-style path separators"
```

---

### Task 5: Add Blinking Cursor to Homepage Hero

**Files:**
- Modify: `src/pages/index.astro` (lines 25-28 — hero name heading)

**Step 1: Add blinking cursor after the name**

Update the `<h1>` in the hero section to include a blinking cursor span:

```astro
<h1 class="my-4 inline-block text-4xl font-bold sm:my-8 sm:text-5xl">
  Fernando Ruiz<span class="animate-pulse text-accent">_</span>
</h1>
```

**Step 2: Verify cursor blinks**

Run: `npm run dev`
Expected: Homepage shows "Fernando Ruiz" with a pulsing mauve underscore cursor.

**Step 3: Commit**

```bash
git add src/pages/index.astro
git commit -m "feat: add blinking terminal cursor to homepage hero"
```

---

### Task 6: Update Card Component with Hover Accent Border

**Files:**
- Modify: `src/components/Card.astro` (lines 16-33)

**Step 1: Add left border accent on hover**

Update the `<li>` element to include a left border that highlights on hover:

```astro
<li class="my-6 border-l-2 border-transparent pl-4 transition-colors hover:border-accent">
  <a
    href={getPath(id, filePath)}
    class:list={[
      "inline-block text-lg font-medium text-accent",
      "decoration-dashed underline-offset-4 hover:underline",
      "focus-visible:no-underline focus-visible:underline-offset-0",
    ]}
  >
    <Heading
      style={{ viewTransitionName: slugifyStr(title.replaceAll(".", "-")) }}
    >
      {title}
    </Heading>
  </a>
  <Datetime {...props} />
  <p>{description}</p>
</li>
```

**Step 2: Verify card hover effect**

Run: `npm run dev`
Expected: Post cards show a mauve left border on hover.

**Step 3: Commit**

```bash
git add src/components/Card.astro
git commit -m "feat: add accent left border on card hover"
```

---

### Task 7: Update Tag Component Styling

**Files:**
- Modify: `src/components/Tag.astro` (lines 13-35)

**Step 1: Style tags as monospace pills**

Update the tag link styling to use monospace font and a surface-1 background:

```astro
<li>
  <a
    href={`/tags/${tag}/`}
    transition:name={tag}
    class:list={[
      "flex items-center gap-0.5 rounded-md px-2 py-0.5",
      "bg-surface-1/50 hover:bg-accent/20",
      "hover:text-accent",
      "focus-visible:text-accent focus-visible:outline-none",
      { "text-sm": size === "sm" },
      { "text-lg": size === "lg" },
    ]}
    style="font-family: var(--font-heading);"
  >
    <IconHash
      class:list={[
        "opacity-80",
        { "size-5": size === "lg" },
        { "size-4": size === "sm" },
      ]}
    />
    {tagName}
  </a>
</li>
```

**Step 2: Verify tags render as pills**

Run: `npm run dev`, navigate to a post or tags page.
Expected: Tags display as rounded monospace pills with subtle background.

**Step 3: Commit**

```bash
git add src/components/Tag.astro
git commit -m "feat: style tags as monospace pills with surface background"
```

---

### Task 8: Add Terminal Dots to Code Blocks

**Files:**
- Modify: `src/styles/typography.css` (add terminal dots CSS to the `.astro-code` section)

**Step 1: Add terminal window chrome CSS**

Add the following CSS after the existing `.astro-code` styles (after line 101, before the Shiki transformers comment):

```css
/* Terminal window chrome for code blocks */
.astro-code {
  @apply relative pt-8 rounded-lg;
}

.astro-code::before {
  content: "";
  position: absolute;
  top: 12px;
  left: 16px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #ed8796; /* Catppuccin red */
  box-shadow:
    20px 0 0 #eed49f, /* Catppuccin yellow */
    40px 0 0 #a6da95; /* Catppuccin green */
}
```

Note: Using Catppuccin Macchiato palette colors for the dots as they provide good visibility on both Mocha (dark) and Latte (light) backgrounds.

**Step 2: Verify code blocks have terminal dots**

Run: `npm run dev`, navigate to a blog post with code blocks.
Expected: Code blocks show red/yellow/green dots at the top-left, resembling a terminal window.

**Step 3: Commit**

```bash
git add src/styles/typography.css
git commit -m "feat: add terminal window dots to code blocks"
```

---

### Task 9: Update OG Image Templates

**Files:**
- Modify: `src/utils/og-templates/post.js` (update colors to Catppuccin Mocha)
- Modify: `src/utils/og-templates/site.js` (update colors to Catppuccin Mocha)
- Modify: `src/utils/loadGoogleFont.ts` (switch font from IBM Plex Mono to JetBrains Mono)

**Step 1: Update `src/utils/loadGoogleFont.ts`**

Replace IBM Plex Mono with JetBrains Mono:

```ts
const fontsConfig = [
  {
    name: "JetBrains Mono",
    font: "JetBrains+Mono",
    weight: 400,
    style: "normal",
  },
  {
    name: "JetBrains Mono",
    font: "JetBrains+Mono",
    weight: 700,
    style: "bold",
  },
];
```

**Step 2: Update `src/utils/og-templates/post.js`**

Replace all hardcoded colors with Catppuccin Mocha palette:
- Background `#fefbfb` → `#1e1e2e` (Base)
- Shadow layer `#ecebeb` → `#313244` (Surface 0)
- Border `#000` → `#45475a` (Surface 2)
- Text color: add `color: "#cdd6f4"` (Text) to all text elements
- Author/title accent: add `color: "#cba6f7"` (Mauve) to the author name

**Step 3: Update `src/utils/og-templates/site.js`**

Same color replacements as post.js:
- Background `#fefbfb` → `#1e1e2e`
- Shadow `#ecebeb` → `#313244`
- Border `#000` → `#45475a`
- Add text color `#cdd6f4` to all text elements

**Step 4: Verify OG images generate correctly**

Run: `npm run build`
Expected: Build succeeds. Check generated OG images in `dist/` — they should show Catppuccin Mocha colors with JetBrains Mono font.

**Step 5: Commit**

```bash
git add src/utils/loadGoogleFont.ts src/utils/og-templates/post.js src/utils/og-templates/site.js
git commit -m "feat: update OG image templates to Catppuccin Mocha palette and JetBrains Mono"
```

---

### Task 10: Full Build Verification

**Files:** None (verification only)

**Step 1: Run type checking**

Run: `npm run build`
Expected: `astro check` passes, build completes, pagefind indexes successfully.

**Step 2: Run format check**

Run: `npm run format:check`
Expected: All files pass formatting. If failures, run `npm run format` and commit.

**Step 3: Run lint**

Run: `npm run lint`
Expected: No lint errors.

**Step 4: Preview the site**

Run: `npm run preview`
Expected: Full site renders with Catppuccin theme. Verify:
- Light/dark toggle works
- Homepage hero has blinking cursor
- Breadcrumbs show `~/posts/...` style
- Code blocks have terminal dots
- Tags are monospace pills
- Cards have hover border accent
- Search works (Pagefind)
- OG images render with correct colors

**Step 5: Final commit (if any formatting fixes needed)**

```bash
git add -A
git commit -m "chore: formatting fixes after theme reskin"
```
