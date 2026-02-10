---
layout: post
title: "Securing Kamal Deployments with Bitwarden: No More Secrets in Git"
date: 2026-02-10
categories: rails deployment security
---

If you're deploying Rails with Kamal, you've probably hit this problem: where do you store your secrets?

You can't commit `RAILS_MASTER_KEY` to git. You can't store production database credentials in a plain text file on your laptop. And you definitely shouldn't be copy-pasting secrets from a shared Google Doc at 2am during an emergency deployment.

The traditional solution? Environment variables on the deploy machine, or maybe a `.kamal/secrets` file that you carefully add to `.gitignore` and pray nobody accidentally commits. It works, but it's fragile. Every new developer needs a Slack DM with the secrets. Every CI/CD pipeline needs secrets manually configured. Every server rotation means updating multiple places.

There's a better way: Bitwarden. You're probably already using it for passwords. Turns out it's also perfect for deployment secrets. And Kamal 2 has built-in support for it.

## Why Bitwarden for Secrets?

Here's what makes Bitwarden different from other secret management solutions:

1. **You're already using it.** No new accounts, no new bills, no new infrastructure to maintain.
2. **It works everywhere.** Laptop, CI/CD, emergency deployments from a friend's computer, all using the same vault.
3. **It has a proper CLI.** Not just a UI tool with a hacked-together script, but a real CLI designed for automation.
4. **Kamal supports it natively.** No custom scripts or adapters to maintain.

Plus, if you're already paying for Bitwarden Premium ($10/year) or have a free account, you don't need anything else.

## How Rails Credentials Work (Quick Refresher)

Rails credentials are encrypted YAML files. You edit them with:

```bash
rails credentials:edit -e staging
```

But that command needs a key file (`config/credentials/staging.key`) to decrypt the credentials. That key file is what we need to protect. Lose it, and your credentials are gone forever. Leak it, and your app is compromised.

The problem: how do you securely share that key with your deploy machine, CI/CD pipeline, and teammates?

## Storing Secrets in Bitwarden

### Prerequisites

First, install the Bitwarden CLI:

```bash
# macOS
brew install bitwarden-cli

# Linux
curl -sL https://vault.bitwarden.com/download/?app=cli&platform=linux -o bw.zip
unzip bw.zip && chmod +x bw && sudo mv bw /usr/local/bin/
```

Unlock your vault and save the session:

```bash
export BW_SESSION=$(bw unlock --raw)
```

### The Simple Approach: Secure Notes

The easiest way to store a credential key is as a Secure Note. This works great for manual retrieval but won't work with Kamal's built-in adapter (more on that later).

Here's how to store a Rails credential key:

```bash
# Step 1: Encode the item as base64 JSON
ENCODED=$(echo '{
  "organizationId": null,
  "collectionIds": null,
  "folderId": null,
  "type": 2,
  "name": "MyApp - Staging Key",
  "notes": "37a76b7f0f178ffd39a40a53c4302b13",
  "favorite": false,
  "fields": [],
  "secureNote": { "type": 0 },
  "reprompt": 0
}' | bw encode)

# Step 2: Create the item
BW_SESSION="<your-session-token>" bw create item "$ENCODED"
```

Item types reference:
- 1 = Login
- 2 = Secure Note
- 3 = Card
- 4 = Identity
- 5 = SSH Key

Now you can retrieve it anywhere:

```bash
# Get the staging key
bw get notes "MyApp - Staging Key"

# Write it to disk for local development
bw get notes "MyApp - Development Key" > config/credentials/development.key
chmod 600 config/credentials/development.key
```

This is perfect for onboarding new developers. Clone the repo, unlock Bitwarden, run one command, and you've got all the credential keys.

### The Kamal 2 Way: Custom Fields

Kamal 2 has a built-in Bitwarden adapter, but it works differently. It reads custom fields from a Login item, not the notes field of a Secure Note.

This is actually better because you can store multiple secrets in a single item, and Kamal can fetch them all at once.

#### Creating a Kamal-Compatible Item

Here's how to create a single Bitwarden item that holds all your staging secrets:

```bash
ENCODED=$(echo '{
  "organizationId": null,
  "collectionIds": null,
  "folderId": null,
  "type": 1,
  "name": "MyApp - Staging Secrets",
  "notes": "Kamal deployment secrets for staging environment",
  "favorite": false,
  "fields": [
    {
      "name": "RAILS_MASTER_KEY",
      "value": "<your-staging-key-value>",
      "type": 1
    },
    {
      "name": "RAILS_STAGING_KEY",
      "value": "<your-staging-key-value>",
      "type": 1
    },
    {
      "name": "SECRET_KEY_BASE",
      "value": "<your-secret-key-base>",
      "type": 1
    },
    {
      "name": "SENTRY_DSN",
      "value": "<your-sentry-dsn>",
      "type": 1
    }
  ],
  "login": {},
  "reprompt": 0
}' | bw encode)

BW_SESSION="<your-session-token>" bw create item "$ENCODED"
```

Field types:
- 0 = Text (visible in the UI)
- 1 = Hidden (recommended for secrets)

#### Updating Your Kamal Secrets File

Now update `.kamal/secrets.staging` to use the Bitwarden adapter:

```bash
# .kamal/secrets.staging

# Fetch all staging secrets from Bitwarden in a single call
SECRETS=$(kamal secrets fetch \
  --adapter bitwarden \
  --account your-email@example.com \
  --from "MyApp - Staging Secrets" \
  KAMAL_REGISTRY_PASSWORD RAILS_MASTER_KEY RAILS_STAGING_KEY SECRET_KEY_BASE SENTRY_DSN)

# Extract individual values
KAMAL_REGISTRY_PASSWORD=$(kamal secrets extract KAMAL_REGISTRY_PASSWORD ${SECRETS})
RAILS_MASTER_KEY=$(kamal secrets extract RAILS_MASTER_KEY ${SECRETS})
RAILS_STAGING_KEY=$(kamal secrets extract RAILS_STAGING_KEY ${SECRETS})
SECRET_KEY_BASE=$(kamal secrets extract SECRET_KEY_BASE ${SECRETS})
SENTRY_DSN=$(kamal secrets extract SENTRY_DSN ${SECRETS})
```

The old way required credential key files on disk:

```bash
# Old approach - fragile and manual
RAILS_STAGING_KEY=$(cat config/credentials/staging.key)
RAILS_MASTER_KEY=$(cat config/credentials/staging.key)
```

The new way pulls everything from Bitwarden automatically. No files on disk. No manual copying. No "Hey can you Slack me the staging key?" messages.

## Deploying with Bitwarden

The deployment workflow is now dead simple:

```bash
# 1. Unlock Bitwarden
export BW_SESSION=$(bw unlock --raw)

# 2. Deploy (Kamal fetches secrets automatically)
bin/kamal deploy -d staging
```

That's it. No key files needed on the deploy machine. As long as the `bw` CLI is installed and the vault is unlocked, Kamal handles everything else.

### Production Secrets

For production, create a separate item with production values:

```bash
# .kamal/secrets (production)

SECRETS=$(kamal secrets fetch \
  --adapter bitwarden \
  --account your-email@example.com \
  --from "MyApp - Production Secrets" \
  KAMAL_REGISTRY_PASSWORD RAILS_MASTER_KEY SENTRY_DSN)

KAMAL_REGISTRY_PASSWORD=$(kamal secrets extract KAMAL_REGISTRY_PASSWORD ${SECRETS})
RAILS_MASTER_KEY=$(kamal secrets extract RAILS_MASTER_KEY ${SECRETS})
SENTRY_DSN=$(kamal secrets extract SENTRY_DSN ${SECRETS})
```

**Pro tip:** Use different Bitwarden accounts for staging and production if you want separation of concerns. Or use Bitwarden Organizations to manage access control at the team level.

## Making It Work in CI/CD

If you're deploying from GitHub Actions, the official Kamal Docker image doesn't include the `bw` CLI. You'll need to install it first.

Here's a complete GitHub Actions workflow:

```yaml
# .github/workflows/deploy.yml
name: Deploy to Staging

on:
  push:
    branches: [staging]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Bitwarden CLI
        run: |
          curl -sL https://vault.bitwarden.com/download/?app=cli&platform=linux \
            -o bw.zip
          unzip bw.zip
          chmod +x bw
          sudo mv bw /usr/local/bin/

      - name: Authenticate with Bitwarden
        env:
          BW_CLIENTID: ${{ secrets.BW_CLIENTID }}
          BW_CLIENTSECRET: ${{ secrets.BW_CLIENTSECRET }}
          BW_PASSWORD: ${{ secrets.BW_PASSWORD }}
        run: |
          bw login --apikey
          echo "BW_SESSION=$(bw unlock --passwordenv BW_PASSWORD --raw)" >> $GITHUB_ENV

      - name: Deploy with Kamal
        run: bin/kamal deploy -d staging
```

You'll need to add three secrets to your GitHub repository:

1. **BW_CLIENTID** - Your Bitwarden API client ID
2. **BW_CLIENTSECRET** - Your Bitwarden API client secret
3. **BW_PASSWORD** - Your Bitwarden master password

Get the API credentials from your Bitwarden vault settings under **Account Settings > Security > Keys > View API Key**.

### Alternative: Bitwarden Secrets Manager

If you're running a lot of CI/CD pipelines, consider Bitwarden Secrets Manager. It's designed specifically for machine-to-machine secrets and uses access tokens instead of unlocking a user vault.

Kamal supports it with the `bitwarden-sm` adapter:

```bash
kamal secrets fetch --adapter bitwarden-sm --from <project-id> SECRET_NAME
```

This is cleaner for CI/CD because you don't need to store your master password in GitHub Secrets.

## Migrating from File-Based Secrets

If you're currently using `.kamal/secrets` files with credential keys on disk, here's the migration path:

1. Create Bitwarden items for each environment with all required secrets as custom fields
2. Update `.kamal/secrets` files to use the `bitwarden` adapter
3. Test locally with `export BW_SESSION=$(bw unlock --raw)` and deploy
4. Update CI/CD to install `bw` and authenticate
5. Delete credential key files from your deploy machines (keep them in the repo for local development)

The beauty of this approach is you can do it incrementally. Start with staging, verify it works, then move production.

## Troubleshooting

**"bw: command not found"**

Install the Bitwarden CLI. On macOS: `brew install bitwarden-cli`. On Linux: download from Bitwarden's website.

**"Session key is invalid"**

Your `BW_SESSION` expired. Run `export BW_SESSION=$(bw unlock --raw)` again.

**"Custom field not found"**

Make sure the field name in your Bitwarden item exactly matches what you're requesting in `kamal secrets fetch`. Field names are case-sensitive.

**Kamal can't find secrets**

Double-check:

1. The item name in `--from` matches your Bitwarden item name exactly
2. The email in `--account` matches your Bitwarden login
3. `BW_SESSION` is set and valid
4. The secrets are stored as custom fields (type 1), not in the notes field

## The Bigger Picture

Secrets management is one of those things that's easy to get wrong and hard to fix later. Bitwarden isn't just a nice-to-have, it's a forcing function for doing secrets right:

- **Centralized:** One source of truth, not scattered across `.env` files and Slack DMs
- **Auditable:** Bitwarden logs who accessed what and when
- **Revocable:** Rotate a secret in one place, and it's updated everywhere on the next deploy
- **Recoverable:** Team member leaves? They can't take the secrets with them, but you can still access them

And because Kamal supports it natively, there's no excuse not to use it.

## What's Next?

Once you've migrated to Bitwarden, consider:

1. Enabling 2FA on your Bitwarden account (you should already have this)
2. Creating separate items for each environment to minimize blast radius
3. Using Bitwarden Organizations if you're working with a team
4. Setting up Bitwarden Secrets Manager for cleaner CI/CD integration
5. Documenting the setup for your team (link to this post!)

The first time you onboard a new developer and they get all their credentials with a single `bw` command, you'll never go back to the old way.

## Quick Reference

**Store a credential key as a Secure Note**

```bash
ENCODED=$(echo '{
  "type": 2,
  "name": "App - Environment Key",
  "notes": "<your-key-value>",
  "secureNote": { "type": 0 }
}' | bw encode)

BW_SESSION="<your-session-token>" bw create item "$ENCODED"
```

**Retrieve a credential key**

```bash
bw get notes "App - Environment Key"
```

**Store secrets for Kamal (as custom fields)**

```bash
ENCODED=$(echo '{
  "type": 1,
  "name": "App - Environment Secrets",
  "fields": [
    {"name": "RAILS_MASTER_KEY", "value": "<your-value>", "type": 1},
    {"name": "SECRET_KEY_BASE", "value": "<your-value>", "type": 1}
  ],
  "login": {}
}' | bw encode)

BW_SESSION="<your-session-token>" bw create item "$ENCODED"
```

**Fetch secrets with Kamal**

```bash
SECRETS=$(kamal secrets fetch \
  --adapter bitwarden \
  --account your-email@example.com \
  --from "App - Environment Secrets" \
  RAILS_MASTER_KEY SECRET_KEY_BASE)

RAILS_MASTER_KEY=$(kamal secrets extract RAILS_MASTER_KEY ${SECRETS})
SECRET_KEY_BASE=$(kamal secrets extract SECRET_KEY_BASE ${SECRETS})
```

## Further Reading

- [Kamal Secrets Commands](https://kamal-deploy.org/docs/commands/secrets/)
- [Kamal Bitwarden Adapter Discussion](https://github.com/basecamp/kamal/discussions/1174)
- [Bitwarden CLI Documentation](https://bitwarden.com/help/cli/)
- [Bitwarden Secrets Manager](https://bitwarden.com/products/secrets-manager/)
