# Jekyll to AstroPaper Migration — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate the Jekyll blog at fruizg0302.github.io to Astro using the AstroPaper theme, preserving existing URLs and gaining dark mode, search, tags, and SEO features.

**Architecture:** Scaffold AstroPaper into the repo root, replacing all Jekyll files. Migrate 3 blog posts with converted front matter. Deploy via GitHub Actions instead of Jekyll auto-build.

**Tech Stack:** Astro 5, AstroPaper theme, TailwindCSS, TypeScript, Pagefind (search), GitHub Actions

---

### Task 1: Scaffold AstroPaper project

**Context:** We need to scaffold AstroPaper into a temporary directory, then move files into the repo. We can't scaffold directly into the repo because it's not empty.

**Step 1: Create AstroPaper project in a temp directory**

```bash
cd /tmp
npm create astro@latest -- --template satnaing/astro-paper astro-paper-scaffold --yes
```

**Step 2: Verify the scaffold succeeded**

```bash
ls /tmp/astro-paper-scaffold/src/
```

Expected: `assets/ components/ config.ts constants.ts content.config.ts data/ env.d.ts layouts/ pages/ scripts/ styles/ utils/`

**Step 3: Commit current state before making destructive changes**

```bash
cd /Users/fernandoruizguzman/workspace/PERSONAL/fruizg0302.github.io
git add -A && git commit -m "chore: snapshot before Astro migration"
```

(Only if there are uncommitted changes.)

**Step 4: Remove Jekyll files**

```bash
cd /Users/fernandoruizguzman/workspace/PERSONAL/fruizg0302.github.io
rm -f _config.yml Gemfile Gemfile.lock index.markdown 404.html heroku_to_kamal.md
rm -rf _posts/
```

Keep: `docs/`, `.git/`, `.gitignore`

**Step 5: Copy AstroPaper files into the repo**

```bash
cp -r /tmp/astro-paper-scaffold/* /Users/fernandoruizguzman/workspace/PERSONAL/fruizg0302.github.io/
cp /tmp/astro-paper-scaffold/.prettierrc /Users/fernandoruizguzman/workspace/PERSONAL/fruizg0302.github.io/
cp /tmp/astro-paper-scaffold/.prettierignore /Users/fernandoruizguzman/workspace/PERSONAL/fruizg0302.github.io/ 2>/dev/null || true
cp /tmp/astro-paper-scaffold/tsconfig.json /Users/fernandoruizguzman/workspace/PERSONAL/fruizg0302.github.io/
cp /tmp/astro-paper-scaffold/.vscode /Users/fernandoruizguzman/workspace/PERSONAL/fruizg0302.github.io/ -r 2>/dev/null || true
```

**Step 6: Update .gitignore for Astro**

Replace contents of `.gitignore` with:

```
# Astro
dist/
node_modules/
.astro/

# Pagefind
public/pagefind/

# Environment
.env
.env.*

# Editor
.vscode/
.idea/

# OS
.DS_Store
```

**Step 7: Install dependencies**

```bash
cd /Users/fernandoruizguzman/workspace/PERSONAL/fruizg0302.github.io
npm install
```

**Step 8: Verify the dev server starts**

```bash
cd /Users/fernandoruizguzman/workspace/PERSONAL/fruizg0302.github.io
npx astro dev &
sleep 5
curl -s http://localhost:4321 | head -20
kill %1
```

Expected: HTML output from the AstroPaper default site.

**Step 9: Commit**

```bash
git add -A && git commit -m "feat: scaffold AstroPaper project replacing Jekyll"
```

---

### Task 2: Configure site settings

**Files:**
- Modify: `src/config.ts`

**Step 1: Update site configuration**

Edit `src/config.ts` and replace the default values:

```typescript
const SITE = {
  website: "https://fruizg0302.github.io/",
  author: "Fernando Ruiz",
  profile: "https://github.com/fruizg0302",
  desc: "Personal blog by Fernando Ruiz. Software engineering, Ruby, AI, and more.",
  title: "Fernando Ruiz",
  ogImage: "astropaper-og.jpg",
  lightAndDarkMode: true,
  postPerIndex: 4,
  postPerPage: 4,
  scheduledPostMargin: 15 * 60 * 1000, // 15 minutes
  showArchives: true,
  showBackButton: true,
  editPost: {
    enabled: false,
  },
  dynamicOgImage: true,
  lang: "en",
  timezone: "America/Chicago",
} as const;
```

**Step 2: Update Astro config for GitHub Pages**

Edit `astro.config.ts` — ensure the `site` value uses our URL:

```typescript
site: "https://fruizg0302.github.io",
```

No `base` is needed since this is a user site (not a project site).

**Step 3: Verify dev server still works**

```bash
npx astro dev &
sleep 5
curl -s http://localhost:4321 | head -5
kill %1
```

**Step 4: Commit**

```bash
git add -A && git commit -m "feat: configure site settings for Fernando Ruiz blog"
```

---

### Task 3: Remove AstroPaper sample blog posts

**Files:**
- Delete: All files in `src/data/blog/` (sample posts from AstroPaper)

**Step 1: List existing sample posts**

```bash
ls src/data/blog/
```

**Step 2: Delete all sample posts**

```bash
rm src/data/blog/*.md src/data/blog/*.mdx 2>/dev/null
```

**Step 3: Commit**

```bash
git add -A && git commit -m "chore: remove AstroPaper sample blog posts"
```

---

### Task 4: Migrate Post 1 — "From Heroku to Kamal"

**Files:**
- Create: `src/data/blog/from-heroku-to-kamal.md`
- Source: `_posts/2026-02-06-from-heroku-to-kamal-deploying-rails-on-your-own-terms.markdown` (already deleted from repo, read from git history)

**Step 1: Retrieve the original post content from git history**

```bash
git show HEAD~2:_posts/2026-02-06-from-heroku-to-kamal-deploying-rails-on-your-own-terms.markdown > /tmp/heroku-to-kamal-original.md
```

(Adjust `HEAD~N` as needed — find it with `git log --oneline --all -- '_posts/2026-02-06*'`)

**Step 2: Create the migrated post**

Create `src/data/blog/from-heroku-to-kamal.md` with:
- Replace the Jekyll front matter with AstroPaper front matter
- Keep all body content unchanged (no Liquid syntax in this post)

New front matter:

```yaml
---
title: "From Heroku to Kamal: A Practical Migration Guide"
author: Fernando Ruiz
pubDatetime: 2026-02-06T00:00:00Z
slug: "rails/deployment/2026/02/06/from-heroku-to-kamal-deploying-rails-on-your-own-terms"
featured: false
draft: false
tags:
  - rails
  - deployment
description: "A practical guide to migrating Rails applications from Heroku to Kamal 2, with step-by-step instructions for Docker, Hetzner Cloud, and production hardening."
---
```

**Step 3: Verify the post renders**

```bash
npx astro dev &
sleep 5
curl -s http://localhost:4321/posts/rails/deployment/2026/02/06/from-heroku-to-kamal-deploying-rails-on-your-own-terms/ | head -20
kill %1
```

**Step 4: Commit**

```bash
git add -A && git commit -m "feat: migrate post - From Heroku to Kamal"
```

---

### Task 5: Migrate Post 2 — "Securing Kamal with Bitwarden"

**Files:**
- Create: `src/data/blog/securing-kamal-with-bitwarden.md`

**Step 1: Retrieve the original post content from git history**

```bash
git show HEAD~3:_posts/2026-02-10-securing-kamal-deployments-with-bitwarden-no-more-secrets-in-git.markdown > /tmp/kamal-bitwarden-original.md
```

**Step 2: Create the migrated post**

New front matter:

```yaml
---
title: "Securing Kamal Deployments with Bitwarden: No More Secrets in Git"
author: Fernando Ruiz
pubDatetime: 2026-02-10T00:00:00Z
slug: "rails/deployment/security/2026/02/10/securing-kamal-deployments-with-bitwarden-no-more-secrets-in-git"
featured: false
draft: false
tags:
  - rails
  - deployment
  - security
description: "How to use Bitwarden CLI and Kamal 2's built-in adapter to manage deployment secrets securely, replacing fragile .env files and manual secret sharing."
---
```

Body content: copy unchanged from original.

**Step 3: Verify the post renders**

```bash
npx astro dev &
sleep 5
curl -s http://localhost:4321/posts/rails/deployment/security/2026/02/10/securing-kamal-deployments-with-bitwarden-no-more-secrets-in-git/ | head -20
kill %1
```

**Step 4: Commit**

```bash
git add -A && git commit -m "feat: migrate post - Securing Kamal with Bitwarden"
```

---

### Task 6: Migrate Post 3 — "Encode Your Rules as Tools"

**Files:**
- Create: `src/data/blog/encode-your-rules-as-tools.md`

**Step 1: Retrieve the original post content from git history**

```bash
git show HEAD~4:_posts/2026-02-12-encode-your-rules-as-tools-a-quality-stack-for-elixir.markdown > /tmp/encode-rules-original.md
```

**Step 2: Create the migrated post**

New front matter:

```yaml
---
title: "Encode Your Rules as Tools: A Compile-to-Test Quality Stack for Elixir"
author: Fernando Ruiz
pubDatetime: 2026-02-12T00:00:00Z
slug: "elixir/quality/2026/02/12/encode-your-rules-as-tools-a-quality-stack-for-elixir"
featured: false
draft: false
tags:
  - elixir
  - quality
description: "How to replace a 450-line AI style guide with automated Elixir build checks using Credo, Dialyzer, Boundary, and custom compile-time rules."
---
```

**IMPORTANT:** This post contains Liquid template syntax that must be removed:
- Remove `{% raw %}` on line 106
- Remove `{% endraw %}` on line 113
- The content between these tags stays unchanged

Body content: copy from original, stripping `{% raw %}` and `{% endraw %}` tags.

**Step 3: Verify the post renders**

```bash
npx astro dev &
sleep 5
curl -s http://localhost:4321/posts/elixir/quality/2026/02/12/encode-your-rules-as-tools-a-quality-stack-for-elixir/ | head -20
kill %1
```

**Step 4: Commit**

```bash
git add -A && git commit -m "feat: migrate post - Encode Your Rules as Tools"
```

---

### Task 7: Add About page

**Files:**
- Create: `src/pages/about.md`

**Step 1: Create the About page**

Create `src/pages/about.md`:

```markdown
---
layout: ../layouts/AboutLayout.astro
title: "About"
---

## Fernando Ruiz

Software engineer. I write about Ruby, Rails, Elixir, deployment, and building things with AI.

Find me on [GitHub](https://github.com/fruizg0302) or reach me at [fernando.ruiz@hey.com](mailto:fernando.ruiz@hey.com).
```

Note: Check if `AboutLayout.astro` exists in `src/layouts/`. If not, use `../layouts/Layout.astro` instead.

**Step 2: Verify the page renders**

```bash
npx astro dev &
sleep 5
curl -s http://localhost:4321/about/ | head -20
kill %1
```

**Step 3: Commit**

```bash
git add -A && git commit -m "feat: add About page"
```

---

### Task 8: Add GitHub Actions deployment workflow

**Files:**
- Create: `.github/workflows/deploy.yml`

**Step 1: Create the workflow file**

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to GitHub Pages

on:
  push:
    branches: [master]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Install, build, and upload
        uses: withastro/action@v3

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

Note: Branch is `master` (not `main`) to match this repo's default branch.

**Step 2: Commit**

```bash
git add -A && git commit -m "feat: add GitHub Actions workflow for Astro deployment"
```

---

### Task 9: Build verification and final cleanup

**Step 1: Run a full production build**

```bash
cd /Users/fernandoruizguzman/workspace/PERSONAL/fruizg0302.github.io
npm run build
```

Expected: Build succeeds with no errors.

**Step 2: Preview the production build**

```bash
npm run preview &
sleep 3
curl -s http://localhost:4321/ | head -30
curl -s http://localhost:4321/posts/rails/deployment/2026/02/06/from-heroku-to-kamal-deploying-rails-on-your-own-terms/ | head -10
curl -s http://localhost:4321/about/ | head -10
kill %1
```

Expected: All pages render correctly.

**Step 3: Verify search index was generated**

```bash
ls dist/pagefind/
```

Expected: Pagefind index files exist.

**Step 4: Commit any remaining changes**

```bash
git add -A && git commit -m "chore: final migration cleanup"
```

(Only if there are uncommitted changes.)

---

### Task 10: Push and verify deployment

**Step 1: Push to GitHub**

```bash
git push origin master
```

**Step 2: Monitor the GitHub Actions workflow**

```bash
gh run list --limit 1
gh run watch
```

Expected: Workflow completes successfully.

**Step 3: Verify the live site**

Visit https://fruizg0302.github.io/ and confirm:
- Homepage shows all 3 posts
- Dark/light mode toggle works
- Search works
- Individual posts render correctly
- About page is accessible
- Old URLs still work (via slug mapping)

**Step 4: Verify GitHub Pages settings**

If the workflow fails, you may need to update GitHub Pages settings:
1. Go to repo Settings > Pages
2. Change Source from "Deploy from a branch" to "GitHub Actions"
