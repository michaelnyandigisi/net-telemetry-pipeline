#Importing Reqired Libraries

import json
import os
import subprocess
import sys

import psycopg2

#Connect to Ookla Speedtest CLI

def run_speedtest():
    out = subprocess.run(
        [
            "speedtest",
            "--accept-license",
            "--accept-gdpr",
            "--format=json"
        ],
        capture_output=True,
        text=True
        timeout=120,
        check=True,
    )
    
    return json.loads(out.stdout)

# Convert bytes/sec to Mbps

def mbps(bytes_per_second):
    return bytes_per_second * 8 / 1_000_000


# Main orchestrator that cordinates collection and storage of speedtest results

def main():
    r = run_speedtest()
    
    row = (
        mbps(r["download"]["bandwidth"]),
        mbps(r["upload"]["bandwidth"]),
        r["ping"]["latency"],
        r["ping"]["jitter"],
    )
    
    conn = psycopg2.connect(
        host=os.environ["DB_HOST"],
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        
    )
    
    with conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO speedtest_logs
            (download_speed, upload_speed, ping, jitter)
            VALUES (%s, %s, %s, %s)
            """,
            row,
        )

    conn.close()
    
    print("logged", row)
    
    if __name__ == "__main__":
        try:
            main()
        except Exception as exc:
            print("Speedtest failed:", exc, file=sys.stderr)
            sys.exit(1)
