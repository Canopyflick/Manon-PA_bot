# Manon Bot Deployment

This directory contains tools and instructions for deploying the Manon Telegram bot on a Raspberry Pi or other Linux server.

## Prerequisites

- A Raspberry Pi or Linux server with Docker and Docker Compose installed
- Access to the GitHub Container Registry where the Manon bot images are published
- Appropriate API keys for Telegram, OpenAI, and other services

## Initial Setup

1. Create a deployment directory on your server:

```bash
mkdir -p ~/manon_deployer/logs
cd ~/manon_deployer
```

2. Copy these files to your deployment directory:
   - `docker-compose.yml`
   - `update_container.sh`
   - `manage_manon.sh`
   - `.env.template` (rename to `.env` and fill in your API keys)

3. Make the scripts executable:

```bash
chmod +x update_container.sh manage_manon.sh
```

4. Create a `.env` file with your configuration:

```bash
cp .env.template .env
nano .env  # Edit with your actual API keys and settings
```

## Starting the Bot

To start the bot for the first time:

```bash
./update_container.sh
```

This will pull the latest Docker image and start the containers.

## Managing the Bot

The `manage_manon.sh` script provides several commands to help manage the bot:

- **View logs**: `./manage_manon.sh logs`
- **Update to latest version**: `./manage_manon.sh update`
- **Clean up old Docker images**: `./manage_manon.sh cleanup`
- **Back up the database**: `./manage_manon.sh backup`

## Automatic Updates

You can set up a cron job to automatically check for updates:

```bash
crontab -e
```

Add this line to check for updates every hour:

```
0 * * * * cd /home/your_username/manon_deployer && ./update_container.sh >> update_container.log 2>&1
```

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
2. Run the update script to start containers: `./update_container.sh`
3. Restore the database if needed (see "Database Management")