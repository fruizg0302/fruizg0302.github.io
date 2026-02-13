---
layout: post
title: "In a World With AI, You Should Be Doing Elixir, Not Java"
date: 2026-02-12
categories: elixir ai
---

You should be learning Elixir, not Java.

I'm not an Elixir evangelist who's never touched a JVM. I've built production systems in both ecosystems. I've written Spring Boot services, wrestled with Maven dependency trees, debugged classloader issues at 2 AM, and shipped enough Java to know what the language does well. I've also built Elixir/Phoenix applications from scratch, including the tooling stack I wrote about in my last post. This isn't tribal loyalty. It's a conclusion I arrived at by writing real code in both worlds while leaning heavily on AI assistants to do it.

For twenty years, "learn Java" was the correct default advice for a working programmer. The ecosystem was massive, the job market was deep, and the language's verbosity was a feature: all that ceremony made code self-documenting. An `AbstractFactoryProviderImpl` was ugly, but you could read it cold and know what it did. Type signatures were long, but they told you exactly what crossed every boundary. That tradeoff made sense when humans wrote every line and humans reviewed every line.

Then AI changed which language properties matter. The verbosity that once made Java self-documenting now creates surface area, more lines for an AI to generate, more lines for you to review, more places for subtle bugs to hide in a 200-line class that could be 30 lines of Elixir. Meanwhile, compile-time correctness went from a nice-to-have to the primary quality gate. When your code is written by an AI assistant that doesn't internalize your conventions across sessions, the question stops being "can a human read this?" and starts being "does the compiler reject this before it ships?" That shift changes the calculus entirely, and it doesn't favor Java.
