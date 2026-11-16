# Operations Guide

Day-to-day procedures for running the Network Telemetry Pipeline on the Azure VM. Placeholders such as `<path-to-worker-env-file>` stand for values specific to your VM.

Backups and data retention are **not automated** in this project. The procedures below are manual.

Container commands use `docker exec` with a name filter, so they work from any directory. `docker compose` commands must be run from the folder that holds `docker-compose.yml`. The Jenkins pipeline deletes its temporary `.env` after each run, so Compose may warn about unset variables when you run it by hand outside a deploy; the running containers are not affected.

## Routine checks

**Is data still arriving?** The newest row should be less than about 10 minutes old (plus the test duration).

```bash
docker exec $(docker ps -qf name=postgres) psql -U admin -d net_telemetry \
  -c "SELECT now() - max(timestamp) AS age, count(*) AS rows FROM speedtest_logs;"
```

**Are the containers running?**

```bash
docker ps --format '{{.Names}}\t{{.Status}}'
```

PostgreSQL and Grafana should both be listed as `Up`. The worker container never appears here for long, because it exits after each run.

**Is cron scheduled?**

```bash
crontab -l
```

Expected entry:

```cron
*/10 * * * * /usr/bin/docker run --rm --network host --env-file <path-to-worker-env-file> my-speedtest-worker-image
```

## Run a measurement by hand

```bash
docker run --rm --network host --env-file <path-to-worker-env-file> my-speedtest-worker-image
```

A successful run takes roughly 20 to 40 seconds and prints a line starting with `logged`. A failure prints `Speedtest failed: ...` to stderr and exits with code 1.

## Pause and resume the worker

Open `crontab -e` and put `#` at the start of the worker line to pause. Remove it to resume. Stored data and dashboards are unaffected.

## Redeploy

1. Merge or push changes to `main`.
2. In Jenkins, open the pipeline job and click **Build Now** (or let your configured trigger start it).
3. Watch **Console Output**. The stages are Checkout, Build worker image, Deploy stack.
4. Run the routine checks above.

A deploy rebuilds `my-speedtest-worker-image`, so the next cron run uses the new code. `docker compose up -d` recreates a container only if its configuration changed, and the named volumes `pgdata` and `grafana-storage` are kept.

## Update the Grafana dashboard

Dashboards are provisioned from Git, so changes made only in the Grafana UI are lost if the volume is rebuilt.

1. Edit the dashboard in Grafana.
2. Export it as JSON (**Share, Export**).
3. Replace `grafana/provisioning/dashboards/network_dashboard.json` with the exported file.
4. Commit and push, then redeploy.

## Back up the database

```bash
docker exec $(docker ps -qf name=postgres) pg_dump -U admin net_telemetry \
  | gzip > telemetry-$(date +%F).sql.gz
```

Copy the file off the VM; a backup stored only on the same disk does not survive losing the VM.

## Restore the database

```bash
docker exec $(docker ps -qf name=postgres) psql -U admin -d net_telemetry \
  -c "DROP TABLE IF EXISTS speedtest_logs;"
gunzip -c telemetry-<YYYY-MM-DD>.sql.gz \
  | docker exec -i $(docker ps -qf name=postgres) psql -U admin -d net_telemetry
```

Rows written after the backup was taken are lost. Pause the worker first if you do not want new rows arriving mid-restore.

## Remove old data

The table grows by 144 rows a day at the current interval. To delete rows older than 90 days:

```bash
docker exec $(docker ps -qf name=postgres) psql -U admin -d net_telemetry \
  -c "DELETE FROM speedtest_logs WHERE timestamp < now() - interval '90 days';"
```

## Rotate credentials

1. Choose new values for `POSTGRES_PASSWORD` and `GRAFANA_ADMIN_PASSWORD`.
2. Replace the file in the Jenkins `telemetry-env` Secret file credential.
3. Update `DB_PASSWORD` in the worker settings file on the VM.
4. Change the actual PostgreSQL password inside the database; changing the environment variable alone does not alter an existing database:

   ```bash
   docker exec -it $(docker ps -qf name=postgres) psql -U admin -d net_telemetry \
     -c "ALTER USER admin PASSWORD '<new-password>';"
   ```

5. Run the Jenkins pipeline, then a manual measurement to confirm.

## Troubleshooting

| Symptom | Likely cause | What to check or do |
| --- | --- | --- |
| No new rows | Cron line missing or worker failing | `crontab -l`; run the worker by hand and read its error |
| `Speedtest failed:` and exit code 1 | Test timed out (120 s limit) or Ookla CLI error | Re-run by hand; check the VM's outbound network |
| Worker: connection refused | PostgreSQL container down | `docker ps`; `docker compose up -d` from the project folder |
| Worker: authentication failed | `DB_PASSWORD` does not match the database password | Compare with `POSTGRES_PASSWORD`; see Rotate credentials |
| Worker: `docker: command not found` or permission denied in cron | Cron user cannot run Docker, or the path differs | Use the full path `/usr/bin/docker`; add the user to the `docker` group |
| Jenkins: permission denied on `docker.sock` | `jenkins` user cannot run Docker | `sudo usermod -aG docker jenkins`, then `sudo systemctl restart jenkins` |
| Jenkins: credential not found | Secret file ID is not `telemetry-env` | Recreate the credential with that exact ID |
| Grafana panels show "No data" | Data source failing or empty time range | Grafana **Connections, Data sources, Telemetry, Save & test**; widen the time range |
| Grafana data source test fails | `POSTGRES_PASSWORD` not reaching Grafana | Confirm the variable is in `.env` and the stack was redeployed |
| Schema change not applied | `init.sql` runs only on a new, empty data volume | Apply the change manually with `psql` |
| Gaps in the charts | Failed or skipped runs | Check cron and worker errors at those times |
