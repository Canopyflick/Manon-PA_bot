param(
    [string]$HostName = "raspberrypi",
    [string]$User = "ben"
)

$target = "$User@$HostName"

$remote = @'
set -e
echo "== Host =="
hostname
date -Is
uptime -p
timedatectl show -p Timezone --value 2>/dev/null || cat /etc/timezone 2>/dev/null || true
echo

echo "== System =="
df -h /
free -h
echo

echo "== Services =="
systemctl is-active docker cron cloudflared 2>/dev/null || true
echo

echo "== Containers =="
docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
echo

echo "== Manon Inspect =="
docker inspect manon --format "Status={{.State.Status}} Exit={{.State.ExitCode}} RestartCount={{.RestartCount}} Policy={{.HostConfig.RestartPolicy.Name}}" 2>/dev/null || true
echo

echo "== Postgres =="
docker exec manon_db pg_isready -U manon -d manon_db 2>/dev/null || true
echo

echo "== Network =="
getent hosts api.telegram.org || true
curl -fsS --max-time 10 https://api.telegram.org >/dev/null && echo "telegram_api=reachable" || echo "telegram_api=unreachable"
curl -fsS --max-time 10 http://localhost:5678/ >/dev/null && echo "n8n_local=reachable" || echo "n8n_local=unreachable"
echo

echo "== Cron =="
crontab -l 2>/dev/null || true
echo

echo "== Obsidian =="
docker ps -f name=onedrive --format "table {{.Names}}\t{{.Status}}" 2>/dev/null || true
/home/ben/obsidian/scripts/obsidian-sync-status.sh 2>/dev/null || true
echo

echo "== Recent Backups =="
find "$HOME/backups" -maxdepth 2 -type f -printf "%TY-%Tm-%Td %TH:%TM %p %s bytes\n" 2>/dev/null | sort | tail -12 || true
echo

echo "== Recent Health =="
tail -20 "$HOME/healthchecks/manon_healthcheck.log" 2>/dev/null || true
'@

$remote = $remote -replace "`r`n", "`n"
$remote | ssh $target "bash -s"
