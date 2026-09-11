---
layout: ../layouts/AboutLayout.astro
title: "About"
---

I'm Fernando Ruiz, a software engineer in Mexico City. I build web applications in
Elixir and Ruby, I self-host more of my own infrastructure than is strictly reasonable,
and I spend a lot of time lately on the seam between ordinary software and machine
learning models.

Most of what I publish here comes out of something I actually ran into: a deployment I
migrated, a library I needed and had to write, a laptop whose speakers did not work. I
try to write the post I wanted to find when I started.

<div class="not-prose my-8 grid gap-3 sm:grid-cols-2">
  <a href="https://github.com/fruizg0302/maquina_lv" class="block rounded-lg border border-border bg-muted/30 p-4 no-underline transition hover:border-accent hover:bg-muted/60">
    <div class="font-heading text-sm font-semibold text-accent">maquina_lv</div>
    <p class="mt-1 text-sm text-subtext">LiveView function components for Phoenix, inspired by shadcn/ui.</p>
    <div class="mt-2 font-heading text-xs text-overlay">Elixir</div>
  </a>
  <a href="https://github.com/fruizg0302/liminal-cdmx" class="block rounded-lg border border-border bg-muted/30 p-4 no-underline transition hover:border-accent hover:bg-muted/60">
    <div class="font-heading text-sm font-semibold text-accent">liminal-cdmx</div>
    <p class="mt-1 text-sm text-subtext">An interactive pixel-art map of Mexico City's ghosts, UFOs and time slips, rendered inside a CRT monitor.</p>
    <div class="mt-2 font-heading text-xs text-overlay">HTML, Canvas</div>
  </a>
  <a href="https://github.com/fruizg0302/ex_wxf" class="block rounded-lg border border-border bg-muted/30 p-4 no-underline transition hover:border-accent hover:bg-muted/60">
    <div class="font-heading text-sm font-semibold text-accent">ex_wxf</div>
    <p class="mt-1 text-sm text-subtext">Encoder and decoder for the Wolfram eXchange Format, so Elixir and Mathematica can talk.</p>
    <div class="mt-2 font-heading text-xs text-overlay">Elixir</div>
  </a>
  <a href="https://github.com/fruizg0302/claude-office" class="block rounded-lg border border-border bg-muted/30 p-4 no-underline transition hover:border-accent hover:bg-muted/60">
    <div class="font-heading text-sm font-semibold text-accent">claude-office</div>
    <p class="mt-1 text-sm text-subtext">A TUI companion for Claude Code: animated kaomoji agents working in a virtual office.</p>
    <div class="mt-2 font-heading text-xs text-overlay">Ruby</div>
  </a>
  <a href="https://github.com/fruizg0302/hanko-ruby" class="block rounded-lg border border-border bg-muted/30 p-4 no-underline transition hover:border-accent hover:bg-muted/60">
    <div class="font-heading text-sm font-semibold text-accent">hanko-ruby</div>
    <p class="mt-1 text-sm text-subtext">Ruby SDK for the Hanko passwordless authentication platform.</p>
    <div class="mt-2 font-heading text-xs text-overlay">Ruby</div>
  </a>
  <a href="https://github.com/fruizg0302/fa401ea-rt721-audio-fix" class="block rounded-lg border border-border bg-muted/30 p-4 no-underline transition hover:border-accent hover:bg-muted/60">
    <div class="font-heading text-sm font-semibold text-accent">fa401ea-rt721-audio-fix</div>
    <p class="mt-1 text-sm text-subtext">A kernel driver fix for silent speakers on the ASUS TUF A14, found by tracing vendor power registers the mainline driver never writes.</p>
    <div class="mt-2 font-heading text-xs text-overlay">C</div>
  </a>
</div>

## What I tend to write about

**Elixir and Phoenix.** LiveView components, OTP, and running models in-process instead
of behind a Python sidecar.

**Ruby and Rails.** Including the periodic ritual of explaining that it is not dead.

**Deployment without a platform.** Kamal, self-hosting, and keeping secrets out of git.

**Local inference.** What a Strix Halo laptop with 64 GB of unified memory can and cannot
actually do, measured rather than assumed.

**Things that are not strictly useful.** Pixel-art maps, CRT shaders, a VS Code theme
built from the colors of Mexico City at night.

## Elsewhere

Code lives on [GitHub](https://github.com/fruizg0302). Mail reaches me at
[fernando.ruiz@hey.com](mailto:fernando.ruiz@hey.com). There is an
[RSS feed](/rss.xml) if you prefer to read on your own terms, and everything here is
also in the [archives](/archives).
