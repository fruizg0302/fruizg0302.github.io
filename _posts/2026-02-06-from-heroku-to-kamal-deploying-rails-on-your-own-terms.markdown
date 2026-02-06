---
layout: post
title: "From Heroku to Kamal: Deploying Rails on Your Own Terms"
date: 2026-02-06
categories: rails deployment
---

Today Salesforce announced that [Heroku Enterprise contracts are officially End of Sale for new customers](https://www.heroku.com/blog/an-update-on-heroku/). The company is "redirecting product and engineering investments toward AI initiatives," and Heroku is moving into what they diplomatically call a "sustaining engineering model", [industry shorthand for maintenance mode](https://simonwillison.net/2026/Feb/6/an-update-on-heroku/) with no new features planned.

In other words: Heroku is in maintenance mode. The end of an era.

For those of us who built our first Rails apps on Heroku, who fell in love with `git push heroku main` and watched our apps come to life in seconds, this hits differently. Heroku didn't just host apps; it defined what developer experience should feel like. It made deployment invisible so you could focus on building.

But the Rails ecosystem didn't stand still. While Heroku was being absorbed into Salesforce's orbit, DHH and the Rails team were building something that recaptures that same spirit of simplicity, except this time, you own the server.

## Enter Kamal

Kamal 2 is a deployment tool from 37signals that ships with Rails 8 by default. It orchestrates Docker containers on any server you can SSH into, gives you zero-downtime deploys, automatic SSL via Let's Encrypt, and rollbacks, all from a single YAML file.

Think of it as "Heroku on your own infrastructure." Same developer experience, a fraction of the cost, and you're never at the mercy of someone else's roadmap.

## What You'll Need

Here's the stack I use for a production Rails SaaS application:

- **A Hetzner Cloud server**, CX23 (2 vCPUs, 4GB RAM) for ~$4/month, or CX33 (4 vCPUs, 8GB RAM) for ~$7/month
- **A domain name** pointed at your server IP
- **A GitHub account** (for the container registry)
- **Docker Desktop** on your development machine

That's it. No add-on marketplace. No dyno slider. No surprise bills.

> **Note on Hetzner naming:** In October 2025, Hetzner renamed their cloud instances. What was CX22 is now [CX23](https://www.hetzner.com/cloud/), and CX32 is now CX33, with slightly lower prices than before.

## The Cost Reality

Let's be honest about why this matters. Here's what running a Rails application actually costs:

| | Heroku | Hetzner + Kamal |
|---|---|---|
| **Compute** | [$7/mo (Basic) to $750/mo (Performance-XL)](https://www.heroku.com/pricing/) | [~$4-7/mo (CX23/CX33)](https://www.hetzner.com/cloud/) |
| **Database** | [$50/mo (Standard-0) or $200/mo (Premium-0)](https://www.heroku.com/pricing/) | PostgreSQL (self-hosted), $0 in dollars, your time to manage |
| **SSL** | Included | Let's Encrypt via kamal-proxy, $0 |
| **Background Jobs** | Separate worker dyno ($7-250/mo) | SolidQueue in Puma process, $0 |
| **Object Storage** | S3 add-on (~$5/mo+) | [Hetzner Object Storage (~$5/mo for 1TB)](https://www.hetzner.com/storage/object-storage/) |
| **Multiple environments** | Separate app = separate cost | Same server, separate containers, $0 |
| **Realistic monthly total** | $50-300+ for a small SaaS | **~$5-10** |

I run both staging and production on the same Hetzner server. Kamal's built-in proxy routes traffic to the right container based on hostname. Two environments, one server, one bill.

> **Price update note:** Hetzner [announced on February 2, 2026](https://www.hetzner.com/pressroom/statement-setup-fees-adjustment/) that prices will increase "in the coming weeks" due to surging hardware costs. The figures above are accurate as of publication but may change soon.

## Setting It Up: A Real-World Walkthrough

I'm going to walk through the actual configuration from a production Rails 8.1 application. No toy examples.

### Step 1: The Dockerfile

Rails 8 generates a production-ready Dockerfile for you. The important parts:

```dockerfile
ARG RUBY_VERSION=4.0.1
FROM docker.io/library/ruby:$RUBY_VERSION-slim AS base

WORKDIR /rails

# Multi-stage build: build gems and assets in a throwaway stage
FROM base AS build
COPY Gemfile Gemfile.lock ./
RUN bundle install && \
    bundle exec bootsnap precompile --gemfile

COPY . .
RUN bundle exec bootsnap precompile app/ lib/
RUN SECRET_KEY_BASE_DUMMY=1 ./bin/rails assets:precompile
# ^ This dummy key is only used during asset precompilation at build time.
#   The real SECRET_KEY_BASE (from Rails credentials) is injected at runtime.

# Final stage: lean production image
FROM base
COPY --from=build "${BUNDLE_PATH}" "${BUNDLE_PATH}"
COPY --from=build /rails /rails

# Non-root user for security
RUN groupadd --system --gid 1000 rails && \
    useradd rails --uid 1000 --gid 1000 --create-home --shell /bin/bash
USER 1000:1000

ENTRYPOINT ["/rails/bin/docker-entrypoint"]

# Thruster handles HTTP/2, asset caching, and X-Sendfile
EXPOSE 80
CMD ["./bin/thrust", "./bin/rails", "server"]
```

Notice the last two lines. Rails 8 includes [Thruster](https://github.com/basecamp/thruster), a tiny HTTP proxy that sits in front of Puma inside the container. It handles HTTP/2, gzip compression, and asset caching. The container exposes port 80, which is exactly what Kamal expects.

**Heroku comparison**: On Heroku, you'd set a `Procfile` with `web: bundle exec puma -C config/puma.rb`. With Kamal, the Dockerfile IS your Procfile, and it does more.

### Step 2: The Entrypoint

The Docker entrypoint runs automatically before your app starts:

```bash
#!/bin/bash -e

# Enable jemalloc for reduced memory usage and latency
if [ -z "${LD_PRELOAD+x}" ]; then
    LD_PRELOAD=$(find /usr/lib -name libjemalloc.so.2 -print -quit)
    export LD_PRELOAD
fi

# Auto-migrate on deploy
if [ "${@: -2:1}" == "./bin/rails" ] && [ "${@: -1:1}" == "server" ]; then
  ./bin/rails db:prepare
  ./bin/rails db:seed
fi

exec "${@}"
```

This is the equivalent of Heroku's `release` phase, migrations run automatically on every deploy. No separate step, no forgetting to run `heroku run rails db:migrate`.

### Step 3: The Kamal Configuration

Here's where the magic happens. Create `config/deploy.yml`:

```yaml
# Name of your application
service: my_app

# Docker image name (GitHub Container Registry)
image: your-username/my_app

# Server(s) to deploy to
servers:
  web:
    - 203.0.113.42  # Your Hetzner server IP

# SSL and routing via kamal-proxy
proxy:
  ssl: true
  host: your-app.example.com
  healthcheck:
    path: /up
    interval: 3

# Container registry credentials
registry:
  server: ghcr.io
  username: your-github-username
  password:
    - KAMAL_REGISTRY_PASSWORD

# Environment variables
env:
  secret:
    - RAILS_MASTER_KEY
  clear:
    APP_HOST: your-app.example.com
    MY_APP_DATABASE_HOST: 172.17.0.1
    MY_APP_DATABASE_PORT: 5432
    RAILS_MAX_THREADS: 5
    WEB_CONCURRENCY: 3
    SOLID_QUEUE_IN_PUMA: true
    RUBY_YJIT_ENABLE: 1
    RAILS_LOG_LEVEL: info

# Keep 10 versions for rollback
retain_containers: 10

# Bridge assets between versions (no 404s during deploy)
asset_path: /rails/public/assets

# Build for amd64 (Hetzner servers)
builder:
  arch: amd64

# SSH configuration
ssh:
  user: your-ssh-user

# Persistent storage
volumes:
  - "my_app_storage:/rails/storage"

# Handy aliases
aliases:
  console: app exec --interactive --reuse "bin/rails console"
  shell: app exec --interactive --reuse "bash"
  logs: app logs -f
  dbc: app exec --interactive --reuse "bin/rails dbconsole"
```

**Heroku comparison**: This single file replaces your `Procfile`, `app.json`, Heroku config vars, add-on declarations, and buildpack configuration. Everything about your deployment lives in one place, checked into version control.

### Step 4: Secrets

Create `.kamal/secrets`:

```bash
KAMAL_REGISTRY_PASSWORD=$KAMAL_REGISTRY_PASSWORD
RAILS_MASTER_KEY=$(cat config/credentials/production.key)
```

That's it. Two lines. Kamal reads these when deploying and injects them into your container.

**Heroku comparison**: Instead of `heroku config:set RAILS_MASTER_KEY=...` (which stores secrets on someone else's server), your master key stays on your machine and is injected at deploy time. Nothing sensitive is stored remotely.

### Step 5: Set Up Your Hetzner Server

1. **Create a server** on [Hetzner Cloud](https://www.hetzner.com/cloud), CX23 or CX33, Ubuntu 24.04
2. **Add your SSH key** during server creation
3. **Install Docker** on the server:

```bash
ssh your-user@your-server-ip
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker your-user
```

4. **Install PostgreSQL**:

```bash
sudo apt install postgresql postgresql-contrib
sudo -u postgres createuser your_app
sudo -u postgres createdb -O your_app your_app_production
sudo -u postgres psql -c "ALTER USER your_app WITH PASSWORD 'a-strong-password';"
```

5. **Configure PostgreSQL** to listen on the Docker bridge so your container can reach it.

   Your Rails app runs inside a Docker container, but PostgreSQL runs directly on the host. The address `172.17.0.1` is the host machine's IP on Docker's default bridge network, it's how containers talk to host-level services. Edit `/etc/postgresql/*/main/postgresql.conf`:

   ```
   listen_addresses = 'localhost,172.17.0.1'
   ```

   And add to `/etc/postgresql/*/main/pg_hba.conf`:

   ```
   host all all 172.17.0.0/16 scram-sha-256
   ```

6. **Secure the server with UFW**. Since we're opening PostgreSQL on the Docker bridge, lock down external access:

   ```bash
   # Crucial: allow SSH first, or you'll lock yourself out of the server!
   sudo ufw allow 22/tcp
   sudo ufw allow 80/tcp    # HTTP (Let's Encrypt + redirect)
   sudo ufw allow 443/tcp   # HTTPS
   sudo ufw default deny incoming
   sudo ufw default allow outgoing
   sudo ufw enable
   ```

   > **Warning**: Always allow SSH (port 22) *before* enabling UFW on a remote server. If you set `default deny incoming` and enable the firewall without an SSH rule, you will be locked out and need to use Hetzner's web console to recover.

   PostgreSQL on `172.17.0.1` is only reachable from the Docker bridge. UFW ensures it's not exposed to the internet. Without a firewall, any process on the internal network could attempt to connect to your database.

7. **Point your DNS** to the server IP.

### Step 6: Deploy

```bash
export KAMAL_REGISTRY_PASSWORD="your-github-pat"
bin/kamal setup -d production
```

First deploy takes a few minutes (building the image, pushing to registry, pulling on the server, starting the container, provisioning the SSL certificate). Every deploy after that is faster.

From then on:

```bash
bin/kamal deploy -d production
```

One command. Zero downtime. Automatic SSL. Sound familiar? It should, it's `git push heroku main`, but you own everything.

## Multi-Environment: Staging + Production on One Server

One of Heroku's hidden costs is that every environment is a separate app with separate billing. With Kamal, you create destination-specific override files.

`config/deploy.staging.yml`:

```yaml
servers:
  web:
    - 203.0.113.42  # Same server!

proxy:
  ssl: true
  host: staging.your-app.example.com
  healthcheck:
    path: /up
    interval: 3

env:
  secret:
    - RAILS_MASTER_KEY
  clear:
    RAILS_ENV: staging
    APP_HOST: staging.your-app.example.com
    MY_APP_DATABASE_USERNAME: my_app_staging
    WEB_CONCURRENCY: 2
    RAILS_LOG_LEVEL: debug

volumes:
  - "my_app_staging_storage:/rails/storage"
```

Deploy to staging:

```bash
bin/kamal deploy -d staging
```

Kamal's built-in proxy (kamal-proxy) routes traffic based on hostname, `your-app.example.com` goes to the production container, `staging.your-app.example.com` goes to staging. Both on the same $4/month server. Both with their own SSL certificates.

## Heroku vs. Kamal (ehm, my take on this)

### What Heroku Does Better

Let's be fair. Heroku still wins in some areas:

- **Zero server management**: You never think about OS updates, disk space, or security patches. With Kamal, the server is yours, and so is its maintenance.
- **Add-on ecosystem**: Need Redis, Elasticsearch, or a monitoring tool? One click. With Kamal, you install and configure these yourself (or use managed services).
- **Team onboarding**: Adding a developer to a Heroku app is a dashboard click. With Kamal, they need SSH access and Docker installed.
- **Instant scaling**: Drag a slider, get more dynos. With Kamal, scaling means adding servers to your `deploy.yml` and deploying.

### What Kamal Does Better

- **Cost**: 10-50x cheaper for equivalent resources. This isn't marginal, it's a different order of magnitude.
- **Performance**: A $4/month Hetzner CX23 (2 vCPUs, 4GB RAM) outperforms Heroku's Basic and Standard dynos. You get dedicated resources, not shared containers on congested infrastructure.
- **Transparency**: Your deployment is a Dockerfile and a YAML file, both in version control. No black box. No buildpack magic. No wondering why your slug size is 500MB.
- **The Solid Stack**: Rails 8's SolidQueue, SolidCache, and SolidCable replace Redis and separate job workers. Everything runs in one container. On Heroku, you'd pay for a Redis add-on and a worker dyno. With Kamal, it's all included.
- **Freedom**: No vendor lock-in. Your Kamal config works on Hetzner, DigitalOcean, AWS EC2, a Raspberry Pi, or a machine under your desk. If Hetzner raises prices, you point at a different IP and deploy.
- **Control**: Need to tune PostgreSQL? SSH in and edit the config. Need to inspect a production database? `bin/kamal dbc -d production`. Need a Rails console? `bin/kamal console -d production`. No intermediary layer.

### Where They're Surprisingly Similar

The developer experience is closer than you might think:

| Task | Heroku | Kamal |
|---|---|---|
| Deploy | `git push heroku main` | `bin/kamal deploy -d production` |
| Rollback | `heroku rollback` | `bin/kamal rollback -d production` |
| Logs | `heroku logs --tail` | `bin/kamal logs -d production` |
| Console | `heroku run rails console` | `bin/kamal console -d production` |
| Env vars | `heroku config:set KEY=value` | Edit `deploy.yml`, redeploy |
| DB migrate | `heroku run rails db:migrate` | Automatic on deploy |
| SSL | Automatic | Automatic |
| Zero-downtime | Yes (Preboot) | Yes (kamal-proxy) |

## The Rails 8 Advantage

If you're starting a new Rails 8 app today, the alignment with Kamal is remarkable:

- `rails new` generates a production Dockerfile
- Thruster is included for HTTP/2 and asset compression
- SolidQueue replaces Sidekiq/Redis for background jobs
- SolidCache replaces Redis/Memcached for caching
- SolidCable replaces Redis for Action Cable
- Kamal is included in the Gemfile

The entire stack runs in a single container. No Redis. No separate worker process. No add-ons. This is exactly the setup that makes Kamal + Hetzner so compelling, your monthly hosting bill can be less than a cup of coffee.

## Getting Started

If you're migrating from Heroku, here's the path:

1. **Upgrade to Rails 8** if you haven't already. The Solid stack eliminates most add-on dependencies.
2. **Generate a Dockerfile**: `rails app:update:dockerfile` (or start from the one Rails 8 generates).
3. **Create a Hetzner server** (10 minutes, ~$4-7/month).
4. **Write your `deploy.yml`** using the example above as a starting point.
5. **Run `bin/kamal setup -d production`** and watch your app come to life.

The whole process takes an afternoon. The savings last forever.

## Production Hardening: What Heroku Did for You

Moving off a PaaS means taking ownership of things Heroku handled silently. Here are the ones that bite people.

### Database Backups

Heroku gave you automated daily Postgres backups with one-click restore. On your own server, `db:prepare` is a migration strategy, not a backup strategy. Set up automated backups from day one.

A simple cron job that dumps to Hetzner Object Storage (S3-compatible):

```bash
# /etc/cron.d/pg_backup - runs daily at 3 AM
0 3 * * * your-user pg_dump -h localhost -U your_app your_app_production | gzip | \
  aws s3 cp - s3://your-bucket/backups/$(date +\%Y-\%m-\%d).sql.gz \
  --endpoint-url https://fsn1.your-objectstorage.com
```

For more robust setups, look at [wal-g](https://github.com/wal-g/wal-g) for continuous WAL archiving with point-in-time recovery, the closest equivalent to what Heroku Postgres provides out of the box.

### Disk Space Discipline

With `retain_containers: 10`, Docker images accumulate fast. Ten versions of a Rails app plus Ruby base layers plus assets can easily exceed 20GB on a small Hetzner CX node.

Run cleanup periodically:

```bash
bin/kamal prune all -d production
```

Or automate it with a cron job. Your future self, staring at a "no space left on device" error at midnight, will thank you.

### Decoupling for Production: Separate Your Database

> **An honest note about the setup described in this post.**

The walkthrough above runs PostgreSQL and the Rails container on the same Hetzner server. This works great for getting started, for staging environments, and for low-to-medium traffic applications. If your startup is on budget you may start here.

But for a production environment that needs to grow, the wisest path is to **decouple your database onto a separate server**:

| Concern | Single Server | Decoupled |
|---|---|---|
| **Resource contention** | Puma and PostgreSQL compete for RAM/CPU | Each gets dedicated resources |
| **Backup & restore** | Dump from the same machine under load | Independent backup schedules, no app impact |
| **Scaling** | Upgrade the entire server to get more DB power | Scale app and DB independently |
| **Security** | One breach exposes everything | Database on a private network, no public IP |
| **Maintenance** | OS update = downtime for both | Patch app server without touching the DB |

The migration path is straightforward with Kamal:

1. **Spin up a second Hetzner server** (or use a managed PostgreSQL service like [Ubicloud](https://www.ubicloud.com/) if you want truly hands-off DB management, note that Hetzner itself [does not offer managed databases](https://www.hetzner.com/cloud/)).
2. **Set up PostgreSQL** on the new server, reachable via Hetzner's private network (vSwitch or Cloud Networks, no public internet exposure).
3. **Update your `deploy.yml`**, change `DATABASE_HOST` from `172.17.0.1` to the private IP of your database server.
4. **Migrate your data** with `pg_dump` / `pg_restore`.
5. **Deploy**: `bin/kamal deploy -d production`. Done.

Your Kamal config doesn't care whether the database is on the same machine, a private network peer, or a managed service across the planet. It's just an environment variable. That's the beauty of decoupled configuration.

**A realistic production budget with decoupled architecture:**

| Component | Hetzner Product | Monthly Cost |
|---|---|---|
| App server | CX23 (2 vCPU, 4GB) | ~$4 |
| Database server | CX33 (4 vCPU, 8GB) | ~$7 |
| Object storage | 100GB bucket | ~$1 |
| Cloud Network | Private networking | $0 |
| **Total** | | **~$12/month** |

Still a fraction of Heroku. And now you have a setup that can handle serious traffic with proper isolation.

## When You Need Real Power: The AX41-NVMe

The cloud instances above (CX23/CX33) are perfect for getting started and running small-to-medium production workloads. But what if you're running a high-traffic SaaS or need serious compute power?

Hetzner's [AX41-NVMe dedicated server](https://www.hetzner.com/dedicated-rootserver/ax41-nvme) is where things get interesting. This is a bare-metal machine, no virtualization overhead, just raw hardware dedicated entirely to your application.

**Here's how it stacks up against Heroku's high-end offerings:**

| Metric | Hetzner AX41-NVMe | Heroku Performance-L | Heroku Performance-XL |
|---|---|---|---|
| **Monthly cost** | **$42** | **$500** | **$750** |
| CPU | AMD Ryzen 5 3600<br/>6 cores / 12 threads (dedicated) | Dedicated (unspecified) | Dedicated (unspecified) |
| RAM | **64 GB DDR4** | 14 GB | 62 GB |
| Storage | 2 x 512 GB NVMe SSD (RAID-1 capable) | Ephemeral | Ephemeral |
| Network | 1 Gbit/s, **unlimited traffic** | 2 TB/mo soft limit | 2 TB/mo soft limit |
| Managed? | No (bare metal, full root) | Fully managed PaaS | Fully managed PaaS |

Let that sink in: **The AX41-NVMe costs $42/month and provides 64 GB of RAM**, more than Heroku's $750/month Performance-XL dyno with 62 GB. That's an **18x price difference** for comparable or superior hardware.

Even comparing to the Performance-L ($500/mo, 14 GB RAM), the Hetzner server delivers **4.6x more RAM at 8.4% of the cost**.

### What You Can Run on an AX41-NVMe

On a single AX41-NVMe server, you could comfortably run:

- Your Rails application (multiple Puma processes)
- PostgreSQL with plenty of RAM for query caching
- Redis for caching and job queues (if not using Solid*)
- Sidekiq workers (if not using SolidQueue)
- Full staging environment in separate containers
- Automated backups with retention

**The equivalent setup on Heroku would cost:**

| Component | Heroku cost |
|---|---|
| Web process (14 GB RAM class) | $500 (Performance-L) |
| Postgres (8 GB RAM, HA) | $350 (Premium-2) |
| Redis (1 GB) | $200 (Premium 5) |
| Background workers | $250 (Performance-M) |
| Staging environment | $50+ (separate app) |
| **Total** | **$1,350+/mo** |

**Hetzner AX41-NVMe total:** **$42/mo**

That's a **32x cost difference** for functionally equivalent infrastructure.

### The Trade-Off: Convenience vs. Control

Heroku charges this premium for a reason:

- **Zero ops burden**: No server management, no security patches, no database tuning, no infrastructure decisions
- **Instant scaling**: Click a button, get more capacity
- **Battle-tested reliability**: Heroku's uptime and operational excellence are well-established
- **Add-on ecosystem**: One-click integration with dozens of services
- **Support**: Enterprise customers get actual human support

The AX41-NVMe requires you to:

- Manage OS updates and security patches
- Configure and tune PostgreSQL yourself
- Set up monitoring, logging, and alerting
- Handle database backups and disaster recovery
- Scale by provisioning new servers and orchestrating load balancing

**For teams with DevOps expertise**, the AX41-NVMe is a no-brainer. You're already doing this work anyway, and saving $1,300+/month buys a lot of engineering time.

**For teams without ops experience**, Heroku's premium might be worth it, at least until your costs hit a threshold where hiring a part-time DevOps engineer becomes cheaper than paying Heroku's markup.

### The Heroku Enterprise Tier Context

This price-to-performance gap becomes especially relevant in light of [today's announcement](https://www.heroku.com/blog/an-update-on-heroku/). Heroku Enterprise contracts, where these high costs accumulate most painfully, are now End of Sale for new customers.

As [Mikel Lindsaar noted in his commentary](https://www.salesforceben.com/salesforce-shuts-down-heroku-enterprise-sales-for-new-customers/): *"Fundamentally, the sales didn't meet expectations."* It's not hard to see why. When your enterprise customers realize they're paying $1,500+/month for infrastructure they could self-host for $42-100/month, the value proposition becomes hard to defend, especially when modern tools like Kamal make self-hosting dramatically simpler than it was in Heroku's heyday.

**Heroku's value proposition has always been operational simplicity.** For small teams and early-stage startups without DevOps expertise, that premium can be entirely justified. The ability to focus purely on product while Heroku handles everything else is genuinely valuable.

But at the Enterprise tier, the tier now being discontinued, the cost gap becomes hardest to defend. Enterprise customers tend to have (or can afford to hire) operations expertise. They're already managing complex infrastructure in other parts of their stack. And they're paying Heroku's premium at scale, where every dollar compounds.

This is the nuance worth understanding: Heroku isn't "dead" or "bad", it's simply that the economics shift dramatically as your scale and sophistication grow. For a side project or MVP? Heroku's simplicity might be worth every penny. For a venture-backed SaaS doing $1M+ ARR with engineering resources? The same math often points toward owning your infrastructure.

And that's exactly the gap Kamal is designed to fill.

## A Fond Farewell

Heroku gave us a gift: it proved that deployment shouldn't be painful. It showed that developers deserve better than wrestling with Apache configs and manually SSH-ing into servers.

Kamal carries that torch forward. It takes the same philosophy, deployment should be one command, and applies it to your own infrastructure, at your own price, on your own terms.

Today, as Heroku enters its twilight, the Rails ecosystem is in a better place than ever. We're not losing something, we're graduating from it.

```bash
bin/kamal deploy -d production
```

Welcome home.

---

*This post is based on the real production configuration of an incoming product, a Rails 8.1 SaaS [REDACTED], running on a single Hetzner CX server with Kamal 2.9.0.*

### AI usage disclosure
*Most of the work for this project has been by me as a solo developer assisted with Claude Code Opus 4.5*

*A technical review of this post has been done by Gemini 3*

*Grammar has been reviewed and corrected by Claude Sonnet 4.5 as Spanish is my native language*

*Hetzner does not sponsor me in any shape or form, but they should*
