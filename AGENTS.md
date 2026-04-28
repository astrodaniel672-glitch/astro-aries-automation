# ASTRO ARIES STUDIO — Codex Agent Rules

This is a private automation system for ASTRO ARIES STUDIO.

The goal is not only to copy the existing Skywork workflow, but to build a cleaner, safer, more modular and better organized automation platform.

## Main role of this project

Build and maintain a system for:

- astrology orders
- Supabase order tracking
- Google Drive organization
- Gmail delivery
- Instagram/Facebook/ManyChat lead handling
- Swiss Ephemeris calculations
- astrology Data Sheet generation
- premium Word/PDF report generation
- Serbian client-facing astrology communication

## Security rules

- Never hardcode secrets, API keys, passwords, access tokens, refresh tokens, service role keys or private keys in source code.
- Never commit `.env` files to GitHub.
- Use environment variables or secure secrets for all credentials.
- Never print full secret values in logs.
- If multiple credential candidates exist, create local validation tools that test them safely and report VALID / INVALID / EXPIRED / MISSING.

## Business identity

- Brand: ASTRO ARIES STUDIO
- Language: Serbian, ekavica
- Tone: professional astrologer, premium, precise, direct, human
- Do not reveal AI nature in client-facing content.
- Do not invent prices, bank details, client data, order status or delivery confirmation.

## Development rules

- Keep code modular.
- Separate backend routes, services, astrology engine, document generation and credential checks.
- Prefer simple Python/FastAPI structure.
- Keep README and docs updated.
- When old Skywork instructions conflict with this project structure, organize and migrate them into the proper docs file instead of copying everything into one large prompt.

## Astrology rules

- Always generate calculated Data Sheet before final interpretation.
- Use Swiss Ephemeris / pyswisseph for calculations.
- Use tropical zodiac and Placidus houses unless configured otherwise.
- Convert local birth time to UTC correctly.
- Do not write house-based interpretation without exact birth time and place.
- Interpret from calculated data, not from generic horoscope assumptions.

## Client report rules

- Serbian ekavica.
- Narrative style, not taxative/bullet style in final client text.
- No generic horoscope language.
- No contradictions.
- No copy-paste between clients.
- Final text must sound like a professional human astrologer.
- Daniel reviews before automatic delivery unless explicitly approved otherwise.
