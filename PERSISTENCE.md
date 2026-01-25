# Database Persistence & Backup

## Volume Configuration

The database and uploads are now stored in persistent bind mounts:

```
data/
├── postgres/
│   └── data/     # PostgreSQL database files (in subdirectory)
└── uploads/      # User uploaded files
```

These directories are:
- ✅ **Persistent**: Survive container restarts and rebuilds
- ✅ **Local**: Stored on host filesystem at `./data/`
- ✅ **Versioned**: Directory structure tracked in git, contents ignored
- ✅ **Backed up**: Automated backup scripts available

## Backup & Restore

### Create Backup
```bash
./scripts/backup.sh
```

This creates timestamped backups in `./backups/`:
- `phonox_db_YYYYMMDD_HHMMSS.sql` - Database dump
- `phonox_uploads_YYYYMMDD_HHMMSS.tar.gz` - Uploads archive

### Restore Backup
```bash
./scripts/restore.sh YYYYMMDD_HHMMSS
```

Example:
```bash
./scripts/restore.sh 20260125_021500
```

### Automatic Cleanup
- Backups older than 7 days are automatically deleted
- Modify the retention period in `scripts/backup.sh` if needed

## Volume Management

### Check Volume Status
```bash
docker volume ls | grep phonox
ls -la data/
```

### Manual Database Access
```bash
# Connect to database
docker exec -it phonox_db psql -U phonox -d phonox

# View database files
docker exec phonox_db ls -la /var/lib/postgresql/data
```

### Reset Everything (⚠️ Data Loss)
```bash
docker compose down
rm -rf data/postgres/* data/uploads/*
docker compose up -d
```

## Migration Notes

- Old Docker volumes will be preserved alongside new bind mounts
- Database data is now stored in `./data/postgres/` on the host
- Uploads are stored in `./data/uploads/` on the host
- Both directories are automatically created and configured

## Cron Job (Optional)

Add to crontab for daily backups:
```bash
0 2 * * * cd /path/to/phonox && ./scripts/backup.sh >/dev/null 2>&1
```