# Downloader Bot

A Telegram bot for downloading media from popular social platforms.

## Supported Platforms

- TikTok (videos & photo carousels)
- Twitter / X
- Instagram
- YouTube

## Features

- Multi-language support: English, Русский, O'zbek
- Favorites system for audio tracks
- Statistics tracking per user
- Docker deployment ready

## Requirements

- Python 3.10+
- Docker & Docker Compose

## Setup

1. Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

2. Run with Docker:

```bash
docker-compose up -d
```

## Environment Variables

See `.env.example` for all required variables.

> **Security note:** Never commit `.env`, user data files (`*_users.txt`), or logs to version control.

## Project Structure

```
src/app/
  core/        — configuration
  database/    — DB queries
  handlers/    — message & callback handlers
  keyboards/   — inline & reply keyboards
  services/    — download logic per platform
  middleware/  — auth, logging
  filters/     — message filters
  dialogs/     — FSM dialogs
  states/      — FSM states
  utils/       — helpers
translations/  — i18n (en / ru / uz)
```

## License

MIT
