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

Today Salesforce announced that [Heroku Enterprise contracts are officially End of Sale for new customers](https://www.heroku.com/blog/an-update-on-heroku/). The company is "redirecting product and engineering investments toward AI initiatives," and Heroku is moving into what they diplomatically call a "sustaining engineering model", [industry shorthand for maintenance mode](https://simonwillison.net/2026/Feb/6/an-update-on-heroku/) with no new features planned.

For those of us who built our first Rails apps on Heroku, who fell in love with `git push heroku main` and watched our apps come to life in seconds, this hits differently. But the Rails ecosystem didn't stand still. While Heroku was being absorbed into Salesforce's orbit, DHH and the Rails team were building something that recaptures that same spirit of simplicity, except this time, you own the server.

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
    - 203.0.113.42 # Your Hetzner server IP

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

   > **Warning**: Always allow SSH (port 22) _before_ enabling UFW on a remote server. If you set `default deny incoming` and enable the firewall without an SSH rule, you will be locked out and need to use Hetzner's web console to recover.

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
    - 203.0.113.42 # Same server!

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

## The Rails 8 Advantage

If you're starting a new Rails 8 app today, the alignment with Kamal is remarkable:

- `rails new` generates a production Dockerfile
- Thruster is included for HTTP/2 and asset compression
- SolidQueue replaces Sidekiq/Redis for background jobs
- SolidCache replaces Redis/Memcached for caching
- SolidCable replaces Redis for Action Cable
- Kamal is included in the Gemfile

The entire stack runs in a single container. No Redis. No separate worker process. No add-ons. This is exactly the setup that makes Kamal + Hetzner so compelling, your monthly hosting bill can be less than a cup of coffee.

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

## Getting Started

If you're migrating from Heroku, here's the path:

1. **Upgrade to Rails 8** if you haven't already. The Solid stack eliminates most add-on dependencies.
2. **Generate a Dockerfile**: `rails app:update:dockerfile` (or start from the one Rails 8 generates).
3. **Create a Hetzner server** (10 minutes, ~$4-7/month).
4. **Write your `deploy.yml`** using the example above as a starting point.
5. **Run `bin/kamal setup -d production`** and watch your app come to life.

The whole process takes an afternoon. The savings last forever.

## Command Reference

The developer experience is closer to Heroku than you might think:

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

---

_This post is based on the real production configuration of an incoming product, a Rails 8.1 SaaS [REDACTED], running on a single Hetzner CX server with Kamal 2.9.0._

### AI usage disclosure

_Most of the work for this project has been by me as a solo developer assisted with Claude Code Opus 4.5_

_A technical review of this post has been done by Gemini 3_

_Grammar has been reviewed and corrected by Claude Sonnet 4.5 as Spanish is my native language_

_Hetzner does not sponsor me in any shape or form, but they should_
