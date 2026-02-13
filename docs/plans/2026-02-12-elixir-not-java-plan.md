# "In a World With AI, You Should Be Doing Elixir, Not Java" — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Write and publish a blog post arguing that AI/LLMs shifted the language calculus in Elixir's favor over Java.

**Architecture:** Single Jekyll markdown post following the existing blog conventions (layout: post, categories, AI disclosure footer). Content follows the approved design doc at `docs/plans/2026-02-12-elixir-not-java-design.md`.

**Tech Stack:** Jekyll blog (jekyll-theme-primer), GitHub Pages, Markdown

---

### Task 1: Create Post File with Frontmatter and Opening Hook

**Files:**
- Create: `_posts/2026-02-12-in-a-world-with-ai-you-should-be-doing-elixir-not-java.markdown`

**Reference files for style/conventions:**
- `_posts/2026-02-12-encode-your-rules-as-tools-a-quality-stack-for-elixir.markdown` (most recent post, tone/format reference)

**Step 1: Create the post file**

Create `_posts/2026-02-12-in-a-world-with-ai-you-should-be-doing-elixir-not-java.markdown` with:

- Jekyll frontmatter: `layout: post`, `title: "In a World With AI, You Should Be Doing Elixir, Not Java"`, `date: 2026-02-12`, `categories: elixir ai`
- The Opening Hook section (3-4 paragraphs):
  - First line IS the hot take, stated plainly: "You should be learning Elixir, not Java."
  - Credibility paragraph: not an evangelist, built production systems in both ecosystems
  - Setup: "learn Java" was correct advice for 20 years. The world changed.
  - Pivot: AI changed which language properties matter. Verbosity went from self-documenting to surface area for review. Compile-time correctness went from nice-to-have to primary quality gate.

**Step 2: Verify Jekyll builds**

Run: `cd /Users/fernandoruizguzman/workspace/PERSONAL/fruizg0302.github.io && bundle exec jekyll build 2>&1 | tail -5`
Expected: Build succeeds with no errors

**Step 3: Commit**

```bash
git add _posts/2026-02-12-in-a-world-with-ai-you-should-be-doing-elixir-not-java.markdown
git commit -m "Add blog post scaffold: Elixir not Java hot take"
```

---

### Task 2: Write Act 1 — Expressiveness Wins When Boilerplate Is Free

**Files:**
- Modify: `_posts/2026-02-12-in-a-world-with-ai-you-should-be-doing-elixir-not-java.markdown`

**Step 1: Write the three Act 1 sections**

Append after the opening hook:

`## When Boilerplate Is Free, Expressiveness Wins` (or similar heading)

**Section 1a: The Verbosity Inversion**
- Pre-AI vs. post-AI value of verbosity
- The bottleneck moved from writing to reviewing
- Concrete code comparison: JSON webhook payload parsing — Java (DTO class, Jackson annotations, validation annotations, service method, try/catch) vs. Elixir (pattern matching function heads, tagged tuples)
- Use fenced code blocks for both examples
- The point: fewer lines = fewer places for AI to introduce subtle bugs you miss during review

**Section 1b: Pattern Matching vs. Inheritance Hierarchies**
- LLMs handle declarative, self-contained pattern matching well
- LLMs struggle with deep inheritance (AbstractFactoryBeanProcessor)
- Elixir's "data + functions + pattern matching" is more LLM-legible than Java's OOP graph
- When your AI understands your code better, it generates better code

**Section 1c: Less Ceremony = Less Drift**
- More ceremony = more places for AI to be technically correct but conventionally wrong
- Java/Spring: 4 ways to inject a dependency, 3 ways to handle transactions
- Elixir: usually one idiomatic way
- AI struggles with conventions precisely because too many valid options exist

**Step 2: Verify Jekyll builds**

Run: `cd /Users/fernandoruizguzman/workspace/PERSONAL/fruizg0302.github.io && bundle exec jekyll build 2>&1 | tail -5`
Expected: Build succeeds. Watch for Liquid syntax issues in code blocks — use `{% raw %}` / `{% endraw %}` around any code containing `{{ }}` or `{% %}`.

**Step 3: Commit**

```bash
git add _posts/2026-02-12-in-a-world-with-ai-you-should-be-doing-elixir-not-java.markdown
git commit -m "Add Act 1: expressiveness wins when boilerplate is free"
```

---

### Task 3: Write Act 2 — Elixir's Guardrails Were Built for This Moment

**Files:**
- Modify: `_posts/2026-02-12-in-a-world-with-ai-you-should-be-doing-elixir-not-java.markdown`

**Step 1: Write the four Act 2 sections**

Append after Act 1:

`## Elixir's Guardrails Were Built for This Moment` (or similar heading)

**Section 2a: Supervision Trees vs. Try/Catch Pyramids**
- AI in Java generates defensive try/catch (correctly — unhandled exceptions kill threads)
- Result: silent error swallowing, bad state propagation
- Elixir: supervision tree IS the error handling. AI doesn't generate defensive code because runtime handles failure
- Reference previous post's `NoRescueInCallbacks` Credo check as a concrete example

**Section 2b: The Compiler as AI Code Reviewer**
- Elixir's layered pipeline: compiler warnings-as-errors, Boundary, custom Credo checks, Dialyzer
- Catches AI mistakes before human review
- Link to previous post: "I wrote about building this pipeline in [Encode Your Rules as Tools](/elixir/quality/2026/02/12/encode-your-rules-as-tools-a-quality-stack-for-elixir.html)"
- Note: Verify the actual URL path by checking Jekyll's permalink structure in `_config.yml` or by looking at existing posts

**Section 2c: Concurrency for Small Teams**
- AI enables small teams → those systems need concurrency
- Java: threading libraries + reactive frameworks + message queues + ops burden
- Elixir: GenServer, PubSub, Task.Supervisor, Phoenix Channels — built into runtime, zero external deps
- AI + Elixir: solo dev builds what a Java team of 5 + DevOps engineer would

**Section 2d: LiveView vs. The Full-Stack Tax**
- Java: Spring Boot + React/Vue + API layer + state management + two build systems
- AI generates both sides, but you review two languages across two paradigms
- LiveView: one language, one paradigm, one codebase, real-time out of the box
- Fewer seams, fewer integration points to review

**Step 2: Verify Jekyll builds**

Run: `cd /Users/fernandoruizguzman/workspace/PERSONAL/fruizg0302.github.io && bundle exec jekyll build 2>&1 | tail -5`
Expected: Build succeeds

**Step 3: Commit**

```bash
git add _posts/2026-02-12-in-a-world-with-ai-you-should-be-doing-elixir-not-java.markdown
git commit -m "Add Act 2: Elixir's guardrails built for this moment"
```

---

### Task 4: Write Concessions and Close

**Files:**
- Modify: `_posts/2026-02-12-in-a-world-with-ai-you-should-be-doing-elixir-not-java.markdown`

**Step 1: Write the concessions section**

Append after Act 2:

`## Where Java Still Wins`

Five concessions, stated plainly with no hedging:
- Enterprise hiring (10x candidate pool)
- Android (Kotlin/JVM home turf)
- Existing codebases (never rewrite 2M lines of Spring Boot)
- Mature enterprise integrations (SAP, Oracle, SOAP — 25 years of plumbing)
- ML/AI model training (Python owns this; Java has better ML libs than Elixir)

The reframe paragraph: these are reasons to stay, not reasons to choose. The thesis isn't "Java is dead" — it's "the default choice changed."

**Step 2: Write the close**

`## Closing` (or similar)

2-3 paragraphs:
- Old advice vs. new advice
- What "most effective team with your AI" means concretely
- You're asking them to update their priors, not abandon Java

**Step 3: Write the footer**

After a `---` horizontal rule:
- Italicized AI usage disclosure (matching format from previous posts)
- Grammar review note

**Step 4: Verify Jekyll builds**

Run: `cd /Users/fernandoruizguzman/workspace/PERSONAL/fruizg0302.github.io && bundle exec jekyll build 2>&1 | tail -5`
Expected: Build succeeds

**Step 5: Commit**

```bash
git add _posts/2026-02-12-in-a-world-with-ai-you-should-be-doing-elixir-not-java.markdown
git commit -m "Add concessions and close: complete blog post"
```

---

### Task 5: Final Review and Polish

**Files:**
- Modify: `_posts/2026-02-12-in-a-world-with-ai-you-should-be-doing-elixir-not-java.markdown`

**Step 1: Read the complete post end-to-end**

Read the entire file and check for:
- Consistent tone (provocative but earned throughout)
- Logical flow from opening → Act 1 → Act 2 → concessions → close
- All code examples are properly fenced and syntax-highlighted
- No Liquid syntax conflicts (all `{{ }}` in code blocks wrapped with `{% raw %}` / `{% endraw %}`)
- Link to previous post is correct
- AI disclosure footer present

**Step 2: Full Jekyll build and verify**

Run: `cd /Users/fernandoruizguzman/workspace/PERSONAL/fruizg0302.github.io && bundle exec jekyll build 2>&1`
Expected: Clean build with no warnings or errors

**Step 3: Commit any polish changes**

```bash
git add _posts/2026-02-12-in-a-world-with-ai-you-should-be-doing-elixir-not-java.markdown
git commit -m "Polish: final review of Elixir vs Java post"
```
