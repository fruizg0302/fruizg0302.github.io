# Design: Jekyll to AstroPaper Migration

## Overview

Migrate the personal blog at fruizg0302.github.io from Jekyll (jekyll-theme-primer) to Astro using the AstroPaper theme. The goal is a feature-rich, modern blog with dark mode, search, tags, and SEO optimization while preserving existing URLs.

## Decisions

- **Framework:** Astro 5 with AstroPaper theme
- **Approach:** Replace Jekyll project in-place (same repo)
- **Deployment:** GitHub Actions (replaces Jekyll auto-build)
- **URL preservation:** Yes, via custom slugs matching old Jekyll category-based paths
- **Draft post:** Exclude the incomplete "Elixir vs Java" post
- **About page:** Yes, simple bio with links

## Architecture

- Replace the entire Jekyll setup with an AstroPaper-based Astro project
- The repo (fruizg0302.github.io) stays the same — contents are replaced
- Deploy via GitHub Actions instead of Jekyll's built-in GitHub Pages integration
- Astro project lives at the repo root

## Content Migration

3 posts to migrate (excluding the incomplete draft):

| Jekyll Post | Astro Location |
|-------------|----------------|
| `_posts/2026-02-06-from-heroku-to-kamal-*.markdown` | `src/content/blog/from-heroku-to-kamal.md` |
| `_posts/2026-02-10-securing-kamal-*.markdown` | `src/content/blog/securing-kamal-with-bitwarden.md` |
| `_posts/2026-02-12-encode-your-rules-*.markdown` | `src/content/blog/encode-your-rules-as-tools.md` |

### Front matter conversion (Jekyll to AstroPaper)

```yaml
# Jekyll
layout: post
title: "..."
date: 2026-02-06 00:00:00 -0600
categories: rails deployment

# AstroPaper
title: "..."
pubDatetime: 2026-02-06T00:00:00Z
tags: [rails, deployment]
description: "..."
author: "Fernando Ruiz"
slug: "rails/deployment/2026/02/06/from-heroku-to-kamal"
```

## URL Preservation

Jekyll generates URLs from categories + date + slug: `/rails/deployment/2026/02/06/from-heroku-to-kamal.html`

To preserve these, we configure custom `slug` values in each post's front matter that match the old Jekyll URL paths. AstroPaper generates post URLs at `/posts/{slug}/`.

We'll need to configure Astro routing or use redirects to map the old category-based paths to the new location, or set the slug to replicate the old path structure.

## Site Configuration

Update AstroPaper's `src/config.ts`:
- Site title: "Fernando Ruiz"
- Site description: "Personal blog by Fernando Ruiz. Software engineering, Ruby, AI, and more."
- Author: Fernando Ruiz
- Email: fernando.ruiz@hey.com
- Social links: GitHub (fruizg0302)

## About Page

Simple page at `src/pages/about.md` with bio and links to GitHub/email.

## GitHub Actions Deployment

Add `.github/workflows/deploy.yml` using the official Astro GitHub Pages deployment workflow. Configure GitHub Pages to use GitHub Actions as the source.

## Files to Remove

- `_config.yml`
- `Gemfile`, `Gemfile.lock`
- `_posts/` directory
- `index.markdown`
- `404.html`
- `heroku_to_kamal.md` (scratch file)

## Files to Keep

- `docs/plans/` (design and plan documents)
- `.git/` (repository history)

## Features Gained

- Dark/light mode toggle
- Fuzzy search (Pagefind)
- Tags system with tag pages
- Dynamic OG images for social sharing
- RSS feed + sitemap
- Perfect Lighthouse scores (100/100)
- SEO optimization
- Draft post support
- Responsive design
- Accessibility (keyboard navigation, screen reader support)

## Tech Stack

- Astro 5
- TypeScript
- TailwindCSS
- Pagefind (search)
- AstroPaper theme
