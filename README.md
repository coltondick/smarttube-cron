# SmartTube-Cron Auto-Updater

This is a simple Docker setup that keeps SmartTube updated on your Android TV.

I built this because manually checking for updates, downloading APKs, and sideloading them is a hassle. This container automates the whole process in the background.

## How it works

The container runs a Python script on a schedule (default is 3 AM). Here is the workflow:

1.  **Checks GitHub:** It looks at the official SmartTube repository for the latest "Stable" release.
2.  **Smart Caching:** It saves version info in a local database so it doesn't spam GitHub and get you rate-limited.
3.  **Downloads & Installs:** If there is a new version (and you don't have it yet), it downloads the APK and installs it to your TV using ADB.

## Prerequisites

You need a few things to get this running:

- **Docker:** Installed on your server or NAS.
- **An ADB Server:** This container relies on a separate ADB connection to talk to your TV. The script is hardcoded to look for a host named `adb` on port `5037`. The default `docker-compose.yaml` included the required ADB server container.

## Quick Start

The easiest way to run this is with Docker Compose.

1.  Create a `docker-compose.yaml` file (or use the one provided).
2.  Update the `DEVICE` IP to match your TV.
3.  Run `docker compose up -d`.

### Example Configuration

```yaml
services:
  smarttube-cron:
    image: ghcr.io/coltondick/smarttube-cron:latest
    container_name: smarttube-cron
    environment:
      # REQUIRED: The IP address of your Android TV
      - DEVICE=192.168.1.50
      # OPTIONAL: When to run the check. Defaults to 3 AM daily.
      - CRON_SCHEDULE=0 3 * * *
      # OPTIONAL: Set your timezone
      - TZ=America/Vancouver
      - PUID=1000
      - PGID=1000
    volumes:
      # This saves the cache database so it survives restarts
      - ./data:/app/data
    restart: unless-stopped

  adb:
    image: barnybbb/adb-hass-androidtv:latest
    container_name: adb
    ports:
      - 5037:5037
    environment:
      - TZ=America/Vancouver
      - PUID=1000
      - PGID=1000
    restart: unless-stopped
```

## Environment Variables

| Variable        | Description                                            |
| :-------------- | :----------------------------------------------------- |
| `DEVICE`        | **Required.** The IP address of your Android TV.       |
| `CRON_SCHEDULE` | The cron schedule for updates. Default is `0 3 * * *`. |
| `TZ`            | Your timezone (e.g., `America/Vancouver`).             |
| `PUID`/`PGID`   | User and Group IDs for file permissions.               |

## First Run: Authorization

Since this runs in the background you need to do this manually once to authorize the ADB connection to your device.

1.  Start the container: `docker compose up -d`
2.  Run this command to force a connection attempt:
    ```bash
    docker exec -it smarttube-cron sh -c 'adb -H adb -P 5037 connect $DEVICE'
    ```
3.  Check your TV screen immediately.
4.  Check the box **"Always allow from this computer"** and select **Allow**.

If you don't do this, the script will fail every night because it's unauthorized.

## Troubleshooting

- **Connection Refused:** If the logs say it can't connect, check your ADB container. The Python script specifically looks for a host named `adb`. If your ADB service is named something else in Docker, you'll need to rename it or link it.
- **Waiting for variables:** If the container hangs at start, it's likely waiting for the `DEVICE` variable. Make sure that is set correctly in your compose file.
