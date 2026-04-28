# ASTRO ARIES STUDIO — System Overview

This project is the new organized automation system for ASTRO ARIES STUDIO.

The goal is to migrate the existing Skywork workflow into a cleaner, safer and more modular Codex/GitHub-based system.

## Main modules

1. Backend API
   - receives orders
   - connects to Supabase
   - handles status updates
   - exposes health checks and webhooks

2. Supabase
   - stores orders
   - stores client data
   - stores delivery status
   - stores Drive links and report metadata

3. Google Drive
   - stores Data Sheets
   - stores final Word/PDF reports
   - keeps client folders organized

4. Gmail
   - sends order confirmations
   - sends finished reports
   - handles delivery messages

5. Instagram / Facebook / ManyChat
   - receives leads
   - collects birth data
   - creates new orders
   - sends safe short replies

6. Astro Engine
   - uses Swiss Ephemeris / pyswisseph
   - calculates natal data
   - calculates prediction layers
   - generates structured Data Sheets

7. Report Generator
   - creates premium Serbian astrology reports
   - uses ASTRO ARIES STUDIO style
   - prepares Word/PDF output

8. Security / Credentials
   - credentials are stored only in local .env files or secure secrets
   - no secret values are stored in GitHub
   - credential check tools may validate keys locally without printing them

## Migration principle

Skywork works as the current reference system, but this project should be better organized, more transparent and easier to maintain.

Old Skywork instructions should be reviewed and moved into the correct documentation file instead of being copied into one large prompt.
