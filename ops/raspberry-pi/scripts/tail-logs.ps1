param(
    [ValidateSet("manon", "manon_db", "n8n", "cloudflared", "health", "backup", "restart")]
    [string]$Service = "manon",
    [int]$Lines = 120,
    [switch]$Follow,
    [string]$HostName = "raspberrypi",
    [string]$User = "ben"
)

$target = "$User@$HostName"
$followFlag = if ($Follow) { "-f" } else { "" }

switch ($Service) {
    "manon" {
        ssh $target "docker logs $followFlag --tail $Lines manon 2>&1"
    }
    "manon_db" {
        ssh $target "docker logs $followFlag --tail $Lines manon_db 2>&1"
    }
    "n8n" {
        ssh $target "docker logs $followFlag --tail $Lines n8n-n8n-1 2>&1"
    }
    "cloudflared" {
        if ($Follow) {
            ssh $target "journalctl -u cloudflared -n $Lines -f --no-pager"
        } else {
            ssh $target "journalctl -u cloudflared -n $Lines --no-pager"
        }
    }
    "health" {
        ssh $target "tail $(if ($Follow) { '-f' } else { '' }) -n $Lines ~/healthchecks/manon_healthcheck.log 2>/dev/null || true"
    }
    "backup" {
        ssh $target "tail $(if ($Follow) { '-f' } else { '' }) -n $Lines ~/backups/backup.log 2>/dev/null || true"
    }
    "restart" {
        ssh $target "tail $(if ($Follow) { '-f' } else { '' }) -n $Lines ~/manon_deployer/weekly_restart.log 2>/dev/null || true"
    }
}
