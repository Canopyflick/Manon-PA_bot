# Manon Bot Deployment

This directory contains tools and instructions for deploying the Manon Telegram bot on a Raspberry Pi or other Linux server.

## Prerequisites

- A Raspberry Pi or Linux server with Docker and Docker Compose installed
- Access to the GitHub Container Registry where the Manon bot images are published
- Appropriate API keys for Telegram, OpenAI, and other services

## Initial Setup

1. Create a deployment directory on your server:

```bash
mkdir -p ~/manon_deployer/logger
cd ~/manon_deployer
```

2. Copy these files to your deployment directory:
   - `docker-compose.yml`
   - `update_container.sh`
   - `manage_manon.sh`
   - `weekly_restart.sh`
   - `.env.template` (rename to `.env` and fill in your API keys)

3. Make the scripts executable:

```bash
chmod +x update_container.sh manage_manon.sh weekly_restart.sh
```

4. Create a `.env` file with your configuration:

```bash
cp .env.template .env
nano .env  # Edit with your actual API keys and settings
```

## Starting the Bot

To start the bot for the first time:

```bash
bash update_container.sh
```

This will pull the latest Docker image and start the containers.

## Managing the Bot

The `manage_manon.sh` script provides several commands to help manage the bot:

- **View logs**: `./manage_manon.sh logs`
- **Update to latest version**: `./manage_manon.sh update`
- **Clean up old Docker images**: `./manage_manon.sh cleanup`
- **Back up the database**: `./manage_manon.sh backup`

## Automatic Updates

Pi uses shared `/home/ben/scripts/ghcr-update-container.sh` (login → pull → digest compare → `compose up -d --no-build` only if changed).

```bash
crontab -e
```

Add this line to check for updates every hour (minute 22):

```
22 * * * * cd /home/ben/manon_deployer && bash update_container.sh >> /home/ben/manon_deployer/update_container.log 2>&1
```

`update_container.sh` flags:

- `--dry-run` — pull and log whether redeploy would happen; no restart
- `--build-fallback` — manual recovery: `git pull` + `docker compose build` if GHCR is unavailable

## Weekly restart (Tuesday & Friday 03:00)

The bot can hang while the Docker container still appears healthy. Twice-weekly restarts clear that state.

1. Copy `weekly_restart.sh` to your deploy directory and make it executable (see Initial Setup).
2. Install the cron job (uses the server’s local timezone, e.g. Europe/Berlin on the Pi):

```bash
crontab -e
```

Add:

```
0 3 * * 2,5 /home/your_username/manon_deployer/weekly_restart.sh >> /home/your_username/manon_deployer/weekly_restart.log 2>&1
```

(`2` = Tuesday, `5` = Friday.)

Or install in one step (replace `your_username`):

```bash
( crontab -l 2>/dev/null | grep -v weekly_restart.sh; echo '0 3 * * 2,5 /home/your_username/manon_deployer/weekly_restart.sh >> /home/your_username/manon_deployer/weekly_restart.log 2>&1' ) | crontab -
```

Logs are appended to `weekly_restart.log` in the deploy directory.

## Troubleshooting

If the bot isn't working correctly:

1. Check container status: `docker ps -a`
2. View detailed logs: `docker logs manon`
3. Inspect database container: `docker logs manon_db`
4. Restart containers: `docker compose down && docker compose up -d`

## Database Management

The PostgreSQL database is persisted in a Docker volume. To back up the database:

```bash
./manage_manon.sh backup
```

This will create a dump file in the `~/backups` directory with the current date.

To restore from a backup:

```bash
# Create backup directory if it doesn't exist
mkdir -p ~/backups

# Restore from a specific dump file
docker exec -i manon_db psql -U manon manon_db < ~/backups/your_backup_file.dump
```

## Complete Reinstallation

If you need to completely reinstall on a new system:

1. Set up the deployment directory as described in "Initial Setup"
2. Run the update script to start containers: `bash update_container.sh`
3. Restore the database if needed (see "Database Management")