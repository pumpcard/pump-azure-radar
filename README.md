# pump-azure-radar

A thin wrapper around [azure-radar](https://pypi.org/project/azure-radar/) that adds a
one-command push of your Azure inventory and billing CSVs to Pump's self-serve
onboarding endpoint — no standing cross-account access required.

Everything in azure-radar (`inventory`, `billing`, `diagram`, `run`) works unchanged.
The Pump push is `run --upload-token`.

## Install

```bash
pip install pump-azure-radar
```

You also need the [Azure CLI](https://docs.microsoft.com/cli/azure/install-azure-cli)
signed in to the subscription you want to onboard (`az login`).

## Usage

`pump-azure-radar` runs the normal azure-radar CLI with `--upload-token` added to `run`:

```bash
pump-azure-radar --help
pump-azure-radar inventory      # azure-radar built-in
pump-azure-radar billing --days 90
```

## Pump onboarding

In the Pump app, mint an upload token. Pump shows you a ready-to-paste command.

Run it against the subscription you want to onboard:

```bash
az account set --subscription <subscription-id>
pump-azure-radar run --upload-token <TOKEN>
```

This inventories the subscription read-only, pulls billing from Cost Management,
writes `azure_inventory.csv` and `azure_billing.csv` locally, and uploads both
straight to Pump. Pump detects both files, runs its analysis, and surfaces the
findings in the app.

- `--billing` is added automatically when `--upload-token` is given.
- `--days` sets the billing window (30, 60 or 90; default 30).
- `--billing-output` changes the billing CSV path (default `azure_billing.csv`).
- Reading cost data needs the **Cost Management Reader** role on the subscription.

Only files written during this run are uploaded, so a stale CSV from an earlier
run is never sent by mistake. If billing fails, the inventory is still uploaded.

### What leaves your machine

Only the two CSVs. The token carries no Azure credentials and no company id — Pump
binds the company and derives the S3 key server-side, so a token can only ever
write its own upload's prefix. Each file goes to S3 through a short-lived
presigned PUT URL that Pump mints on demand.

### Pointing at a non-prod backend

The token exchange defaults to `https://api.pump.co`. Override it for local testing:

```bash
pump-azure-radar run --upload-token <TOKEN> --api-base http://localhost:8001
# or
PUMP_API_BASE=http://localhost:8001 pump-azure-radar run --upload-token <TOKEN>
```

### How the push works

`pump_azure_radar/upload.py`:

1. For each role (`inventory`, `billing`), POSTs `{api_base}/api/v1/estimate/radar/urls`
   with `{"token", "role"}` and receives a presigned S3 PUT URL.
2. PUTs the corresponding CSV with `Content-Type: text/csv` (the presigned URL
   signs the content-type, so it must match).

## Relationship to upstream

This package builds on azure-radar (MIT). The scanning and billing code is
upstream's; the Pump push is this package's addition. Unlike gcp-radar, azure-radar
has no plugin hook and already writes separate inventory and billing CSVs, so this
wrapper calls azure-radar's CLI in-process and uploads its output files as-is.

## Development

```bash
pip install -e ".[dev]"
pytest
```
