---
title: "Rails in 2026: The Framework They Keep Burying"
author: Fernando Ruiz
pubDatetime: 2026-02-16T00:00:00Z
slug: "rails-in-2026-the-framework-they-keep-burying"
featured: false
draft: false
tags:
  - ruby
  - rails
description: "Every year a fresh batch of 'languages that will be obsolete' articles puts Ruby on the list. Here's what the numbers actually say."
---

Every year, a fresh batch of "X languages that will be obsolete by 2027" articles rolls off the content mill. Ruby is always on the list. It's been on the list since I started my career. At this point it feels like a genre, like true crime podcasts or Marvel sequels: formulaic, endlessly produced, and weirdly popular despite saying the same thing every time.

I don't want to write a rebuttal. Rebuttals are boring and defensive and nobody's mind was ever changed by a bullet-point list titled "Actually, You're Wrong." Instead, I just want to share some numbers I ran into while researching the state of Rails, because they genuinely surprised me, and I think they might surprise you too.

## The number that made me do a double take

During Black Friday/Cyber Monday 2024, Shopify processed **$11.5 billion in gross merchandise value**. Peak traffic hit **284 million requests per minute** pushing **12 TB of traffic per minute**.

All on Rails.

Shopify CEO Tobi Lütke's tweet about it remains iconic: _"Total GMV was $4.1b... But Rails doesn't scale so what are we even doing"_. That was the 2023 number. They almost tripled it.

## Meanwhile, the "dead" ecosystem is having a growth spurt

Here's where it gets fun. RubyGems is serving **4 billion gem downloads per month** as of April 2025. That's a **51% increase** from the year before. The total download count sits at **238.25 billion**. Rails 8.0.2 alone pulled **4.1 million downloads** in its first four months.

The Rails repo has **58,000+ GitHub stars** and **5,000+ all-time contributors**. Rails 8.1 shipped in October 2025 with contributions from **500+ developers across 2,500 commits**. Ruby itself hit version 4.0 in December 2025, introducing the experimental ZJIT compiler. Languages on their deathbed don't usually ship a new major version with a JIT compiler, but what do I know.

The **Rails Foundation** now has 10 core members: Shopify, GitHub, 1Password, Cookpad, Doximity, Fleetio, Intercom, Procore, 37signals, and Judge.me, each paying **$75,000 per year**. Seven of those joined in 2025 alone.

## Companies migrating _to_ Rails is my favorite plot twist

The "dead language" articles always mention companies that left Rails. Twitter moved to Scala! (In 2012. Obama was president.) But the reverse migration pattern is way more interesting and almost never gets coverage.

**Flexcar** took their **80 Java microservices and 30 databases** and consolidated them into a single Rails monolith. In 4 months. With a team that had zero Rails experience except the CTO. Their Director of Engineering presented the results at RailsConf 2025.

**Craftwork.com** tried Next.js for 3 months, abandoned it, rebuilt in Rails, and raised $6M in seed funding. **Hardcover.app** migrated from Next.js to Rails + Inertia.js after hitting unclear caching behavior and rising Vercel bills. **Whop.com**, a Gen Z marketplace, picked Rails specifically because it let them ship features as fast as users could request them.

And the big names staying put? GitHub runs a **2-million-line Rails monolith** with 1,000+ engineers deploying 20 times daily. Along with Shopify, the list includes **1Password, Robinhood, Betterment, Affirm, Chime, Plaid, Peloton**, and more. Thoughtbot's 2025 audit counted **67+ significant companies** running Rails in production.

## YJIT is quietly a big deal

Remember when "Ruby is slow" was a legitimate complaint? YJIT, Shopify's production JIT compiler (baked into Ruby since 3.1), delivers a **~79% speedup on Railsbench** and roughly **2.8x improvement** on Liquid template rendering. Memory usage dropped to about **one-third of Ruby 3.1 levels**.

To put that in context: Intercom handles **150,000 requests per second** on Rails. Judge.me serves **500,000+ e-commerce shops** with just 10 engineers. Doximity serves **2 million+ healthcare professionals**, including 80% of US doctors.

The "can't scale" argument made sense in 2014. In 2026 it's trivia.

## The one-person framework

Rails 8 leaned hard into what DHH calls "the one-person framework," and the pitch is compelling: a single developer can build, deploy, and operate a production application on a **$5 VPS**. No Heroku. No Render. No monthly infrastructure bill that makes you question your life choices.

The pieces:

- **Solid Queue** replaces Redis-backed Sidekiq for background jobs (HEY runs 20 million jobs/day on it)
- **Solid Cache** replaces Redis/Memcached (Basecamp runs a 10TB cache with 96% hit rate)
- **Solid Cable** handles WebSockets without Redis
- **Kamal 2** deploys to any server in under 2 minutes
- **Built-in authentication generator** extracted from production 37signals apps

One framework. One database. One server. One developer. That's a real superpower when you're bootstrapping.

## A wild stat for the AI era

This one is niche but I find it fascinating. Martin Alderson's January 2026 analysis of token efficiency across 19 languages found that **Ruby ranks second among mainstream languages**, behind only Clojure. Dynamic languages averaged **30% fewer tokens** than statically-typed counterparts.

Why does this matter? When you're working with an AI coding assistant, every token eats context window space and API cost. `has_many :posts` packs the same meaning as 10+ lines of explicit association code. `validates :name, presence: true` replaces manual validation logic. Rails conventions mean the AI can infer where code lives (`app/models/`, `app/controllers/`) without you explaining the project structure.

As developer Sean Goedecke put it: _"A LLM can't skim boilerplate... a token takes up space in its context window whether it's boilerplate or not. The ideal language for LLMs is a language that uses as few tokens as possible per feature while still being readable. That's Ruby."_

Fair caveat: LLMs still produce better code in Python due to training data volume. But that's a data problem, not a language problem, and it's closing.

## The honest part

I like Rails. I'm not going to pretend it's perfect.

Ruby fell out of the TIOBE top 20 in 2025. Fewer new developers enter the ecosystem compared to Python or JavaScript. Ruby is the wrong choice for ML/AI model training. Concurrency, while improving through Ractors and Fibers, still lags behind Go and Elixir. If you're building something like Linear or Figma, React/Next.js is the better pick.

But "declining in mindshare" is a completely different sentence than "obsolete." PHP powers 79% of websites and nobody mistakes it for cutting-edge. Maturity and mortality aren't the same thing.

## So why do these articles keep getting written?

Honestly? SEO. "Top 6 languages that will DIE in 2027" is a great headline. It gets clicks, gets shared, generates angry engagement in comment sections. The authors are overwhelmingly content creators and SEO bloggers, not practicing engineers.

The developers writing "Ruby is dead" articles are not building products. The developers building products are not writing those articles.

Meanwhile, Rails keeps processing billions in commerce, shipping features for small teams that compete with engineering armies, and attracting companies migrating _to_ it from architectures that looked good on a whiteboard but didn't survive contact with reality.

Every metric that matters for a production framework — **download velocity** (4B/month, 51% YoY growth), **corporate investment** (10 foundation members), **release cadence** (Rails 8.0, 8.1, Ruby 4.0 in 14 months), **production scale** ($11.5B in one weekend), **developer salaries** ($115K-$155K average) — points the same direction.

Rails isn't dying. It just stopped being trendy. And for the kind of work I do, that's fine by me.

---

### Sources

**Ecosystem & Statistics**
- [RubyGems.org Stats](https://rubygems.org/stats) — gem counts, download metrics, user statistics
- [GitHub Ruby Repository Rankings](https://github.com/EvanLi/Github-Ranking/blob/master/Top100/Ruby.md) — stars, contributors, activity metrics

**Companies Using Rails**
- [Monterail — Companies That Use Ruby on Rails in 2025](https://www.monterail.com/blog/companies-that-use-ruby-on-rails)
- [MobiDev — Why Ruby is Still Great for Web App Development](https://mobidev.biz/blog/ruby-on-rails-not-dead-still-good-for-your-product-development)
- [SaaSTrail — Is Ruby on Rails Still Relevant in 2025?](https://saastrail.com/is-ruby-on-rails-still-relevant-in-2025/)

**Performance & Scaling**
- [Shopify Engineering — YJIT Benchmarking](https://shopify.engineering/yjit-benchmarking-harness) — YJIT performance metrics
- [ByteByteGo — Shopify Tech Stack](https://blog.bytebytego.com/p/shopify-tech-stack) — architecture analysis, Black Friday metrics
- [Shopify News — Performance Updates](https://www.shopify.com/news/performance%F0%9F%91%86-complexity%F0%9F%91%87-killer-updates-from-shopify-engineering)

**Community & Events**
- [TokyoDev — RubyKaigi 2025 Recap](https://www.tokyodev.com/articles/rubykaigi-2025-recap)
- [Ruby Events — RubyKaigi 2025](https://www.rubyevents.org/events/rubykaigi-2025)

**Rails 8 Features**
- [Bacancy Technology — Rails 8.0 Release](https://www.bacancytechnology.com/blog/rails-8) — new features, latest updates

**Migration Case Studies**
- [Ruby Central — RailsConf 2025 Keynote: Flexcar](https://rubycentral.org/news/railsconf-2025-keynote-john-dewsnap-on-what-happened-after-flexcar-switched-from-java-to-ruby-on-rails/) — John Dewsnap on migrating from Java to Rails
- [Class Central — Flexcar Migration Video](https://www.classcentral.com/course/youtube-railsconf-2025-365-days-later-moving-from-java-to-ror-and-how-it-changed-everything-by-john-dewsnap-470472) — "365 Days Later"
- [Evil Martians — Startups on Rails (RailsConf 2024)](https://evilmartians.com/events/startups-on-rails-railsconf-2024)
- [Hotwire Weekly — Next.js to Rails Migration](https://www.hotwireweekly.com/archive/week-19-from-nextjs-to-rails-building-a-password-manager/)
- [Daily.dev — Falling Out of Love with Next.js](https://app.daily.dev/posts/part-1-how-we-fell-out-of-love-with-next-js-and-back-in-love-with-ruby-on-rails-inertia-js-uwwz87c2k) — Hardcover.app's migration story

**Developer Productivity**
- [Netguru — Build MVP with Ruby on Rails](https://www.netguru.com/blog/build-mvp-with-ruby-on-rails)
- [RailsCarma — Rails Accelerates MVP Development](https://www.railscarma.com/blog/how-ruby-on-rails-accelerates-mvp-development-for-startups/)
- [Medium — Why I Moved from Java Spring Boot to Rails](https://medium.com/@danilo.alves9325/why-i-moved-from-java-spring-boot-to-ruby-on-rails-567ff5f02213)

**AI/LLM Token Efficiency**
- [Ivan Turkovic — Ruby Token Efficiency](https://www.ivanturkovic.com/2026/01/17/ruby-token-efficiency-llm-ai-friendly-language/) — "Why Ruby Might Be the Most AI-Friendly Language Nobody's Talking About"
- [Sean Goedecke — The Future of AI is Ruby on Rails](https://www.seangoedecke.com/ai-and-ruby/)

**Industry Rankings**
- [InfoWorld — TIOBE Programming Language Rankings 2025](https://www.infoworld.com/article/4112993/c-wins-tiobe-programming-language-of-the-year-honors-for-2025.html)

**Counter-Arguments & Community Response**
- [Goji Labs — Why Ruby on Rails Development is Still Smart](https://gojilabs.com/blog/why-ruby-on-rails-development-is-still-a-smart-choice-in-2025/)
- [Genbeta (Spanish) — Programming Languages Obsolete by 2026](https://www.genbeta.com/desarrollo/estos-seis-lenguajes-programacion-estaran-obsoletos-2026-desarrollador-da-consejos-para-reaccionar-usas) — the original article making obsolescence claims

### AI usage disclosure

_Most of the research for this post was compiled and fact-checked with Claude Code Opus 4.6_

_Grammar has been reviewed and corrected by Claude Sonnet 4.5 as Spanish is my native language_
