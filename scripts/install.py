#!/usr/bin/env python3

import os
import sqlite3
import time
import requests
import subprocess
import logging
from datetime import datetime


# Load environment variables
def load_env_file(filepath="/tmp/env_vars"):
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ[key] = value


load_env_file()

# Constants
DEVICE = os.environ.get("DEVICE")
API_URL = "https://api.github.com/repos/yuliskov/SmartTube/releases/latest"
APK_PATH = "/tmp/smarttube_latest.apk"
DB_PATH = "/app/data/smarttube_cache.db"
CACHE_TTL = 6 * 60 * 60  # 6 hours

# PATH fix
os.environ["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/usr/local/sbin"

# Logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS cache (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """
    )
    conn.commit()
    return conn


def db_get(conn, key):
    cur = conn.cursor()
    cur.execute("SELECT value FROM cache WHERE key = ?", (key,))
    row = cur.fetchone()
    return row[0] if row else None


def db_set(conn, key, value):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO cache (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
    conn.commit()


def cleanup():
    if os.path.exists(APK_PATH):
        logging.info("Removing temporary APK file.")
        os.remove(APK_PATH)


def conditional_github_request(etag, last_modified):
    """Send a conditional GET request using ETag + Last-Modified headers."""
    headers = {}

    if etag:
        headers["If-None-Match"] = etag

    if last_modified:
        headers["If-Modified-Since"] = last_modified

    logging.info("Sending conditional GitHub request...")
    response = requests.get(API_URL, headers=headers, timeout=10)

    return response


def parse_release_data(json_data):
    """Extract version + download URL from release assets."""
    for asset in json_data["assets"]:
        n = asset["name"].lower()
        if "stable" in n and "arm64" in n:
            version = asset["name"].split("_")[2]
            return version, asset["browser_download_url"]
    return None, None


def download_apk(url):
    logging.info("Downloading APK...")
    r = requests.get(url, timeout=20)
    r.raise_for_status()

    with open(APK_PATH, "wb") as f:
        f.write(r.content)


def install_apk(version):
    logging.info("Connecting to ADB...")
    subprocess.run(["adb", "-H", "adb", "-P", "5037", "connect", DEVICE], check=True)

    logging.info(f"Installing SmartTube {version} ...")
    subprocess.run(
        ["adb", "-H", "adb", "-P", "5037", "-s", DEVICE, "install", "-r", APK_PATH],
        check=True,
    )


def main():
    logging.info("---------------------------------------------------------")
    logging.info(f"Execution started at {datetime.now()}")

    conn = init_db()

    # Load cache fields
    etag = db_get(conn, "etag")
    last_modified = db_get(conn, "last_modified")
    cached_version = db_get(conn, "latest_version")
    cached_url = db_get(conn, "latest_url")
    last_installed = db_get(conn, "last_installed")
    last_checked = db_get(conn, "last_checked")

    if last_checked and (time.time() - float(last_checked)) < CACHE_TTL:
        if cached_version and cached_url:
            logging.info("Cache TTL valid → using cached release info.")
            latest_version = cached_version
            apk_url = cached_url
        else:
            logging.warning("Cache TTL valid but missing fields — will query GitHub.")
    else:
        try:
            response = conditional_github_request(etag, last_modified)

            if response.status_code == 304:
                # No change → reuse cache
                logging.info("GitHub returned 304 (Not Modified). Cache is up to date.")
                latest_version = cached_version
                apk_url = cached_url

            else:
                response.raise_for_status()
                json_data = response.json()

                latest_version, apk_url = parse_release_data(json_data)
                if not latest_version:
                    logging.error("Could not extract asset info from GitHub JSON.")
                    return

                # Store fresh metadata
                db_set(conn, "latest_version", latest_version)
                db_set(conn, "latest_url", apk_url)
                db_set(conn, "etag", response.headers.get("ETag", ""))
                db_set(conn, "last_modified", response.headers.get("Last-Modified", ""))
                db_set(conn, "last_checked", str(time.time()))

        except Exception as e:
            logging.error(f"GitHub request failed: {e}")

            # Use cached metadata if possible
            if cached_version and cached_url:
                logging.info("Falling back to cached release metadata.")
                latest_version = cached_version
                apk_url = cached_url
            else:
                logging.error("No cached metadata available. Aborting.")
                return

    logging.info(f"Latest known version: {latest_version}")

    if last_installed == latest_version:
        logging.info(f"SmartTube {latest_version} already installed. Exiting.")
        return

    try:
        download_apk(apk_url)
        install_apk(latest_version)

        db_set(conn, "last_installed", latest_version)

        logging.info(f"SmartTube {latest_version} installed successfully!")

    except Exception as e:
        logging.error(f"Installation error: {e}")

    finally:
        cleanup()
        conn.close()


if __name__ == "__main__":
    main()
