# VPS Deployment (Docker)

The bot runs in **long-polling** mode, so it needs only outbound internet
access — no open ports, no domain, no reverse proxy, no TLS.

## 1. Prerequisites on the VPS

Ubuntu/Debian example:

```bash
# Install Docker Engine + Compose plugin
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # log out/in afterwards so `docker` works without sudo
```

Verify:

```bash
docker --version
docker compose version
```

## 2. Get the code onto the server

```bash
git clone <your-repo-url> smm_bot
cd smm_bot
```

## 3. Create the `.env` file

```bash
cp .env.example .env
nano .env
```

Fill in at minimum:

- `TELEGRAM_BOT_TOKEN` — from [@BotFather](https://t.me/BotFather)
- `AI_PROVIDER` and the matching API key (`GEMINI_API_KEY`, `GROQ_API_KEY`, or `OPENAI_API_KEY`)

Leave `DATABASE_PATH=work/smm_bot.sqlite3` and `TEMP_DIR=work/tmp` as-is — they
map to the persistent `bot-data` Docker volume.

## 4. Build and start

```bash
docker compose up -d --build
```

The `restart: unless-stopped` policy means the container auto-restarts on crash
and comes back up after a server reboot.

## 5. Operate

```bash
docker compose logs -f          # live logs
docker compose ps               # status
docker compose restart          # restart
docker compose down             # stop & remove container (data volume kept)
```

## 6. Update after pulling new code

```bash
git pull
docker compose up -d --build
```

## Data & backups

All persistent state (SQLite DB + temp files) lives in the named volume
`bot-data` (`/app/work` inside the container). To back up the database:

```bash
docker compose cp smm-bot:/app/work/smm_bot.sqlite3 ./smm_bot.sqlite3.bak
```

## Notes

- Logs are capped at 3 × 10 MB via the json-file driver (see `docker-compose.yml`).
- Only one instance may poll a given bot token at a time. Don't run the bot
  locally and on the VPS with the same token simultaneously — Telegram will
  return `409 Conflict`.
