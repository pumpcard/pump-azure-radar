"""``pump-azure-radar``: azure-radar's CLI plus ``run --upload-token``.

azure-radar builds its ``run`` command internally, so we can't add flags to it.
Instead we strip our own flags from argv, hand the rest to azure-radar's real
Typer app, and once ``run`` has written its CSVs, upload ``azure_inventory.csv``
and ``azure_billing.csv`` to Pump.
"""

import argparse
import os
import sys
import time

DEFAULT_API_BASE = "https://api.pump.co"

# azure-radar always writes the inventory here (relative to the working directory).
INVENTORY_CSV = "azure_inventory.csv"
DEFAULT_BILLING_CSV = "azure_billing.csv"


def _pump_args(argv):
    p = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    p.add_argument("--upload-token")
    p.add_argument("--api-base", default=os.environ.get("PUMP_API_BASE", DEFAULT_API_BASE))
    return p.parse_known_args(argv)


def _billing_output(argv):
    p = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    p.add_argument("--billing-output", default=DEFAULT_BILLING_CSV)
    return p.parse_known_args(argv[1:])[0].billing_output  # argv[0] is "run"


def _written_since(path, start):
    """True if *path* exists and was (re)written at or after *start*."""
    return os.path.isfile(path) and os.path.getmtime(path) >= start


def main():
    from azure_radar.cli import app

    pump, rest = _pump_args(sys.argv[1:])
    is_run = bool(rest) and rest[0] == "run"
    if pump.upload_token and not is_run:
        sys.exit("pump-azure-radar: --upload-token is only supported with the 'run' command.")
    if pump.upload_token and "--billing" not in rest:
        rest.append("--billing")  # Pump needs billing data alongside the inventory

    start = time.time()
    try:
        app(args=rest, prog_name=os.path.basename(sys.argv[0]))
    except SystemExit as e:
        if e.code not in (None, 0):
            raise  # azure-radar failed, so don't upload

    if not (pump.upload_token and is_run):
        return

    from pump_azure_radar.upload import UploadError, upload_csvs

    billing_csv = _billing_output(rest)
    files = {}
    if _written_since(INVENTORY_CSV, start):
        files["inventory"] = INVENTORY_CSV
    if _written_since(billing_csv, start):
        files["billing"] = billing_csv
    if "inventory" not in files:
        sys.exit(f"  [!] {INVENTORY_CSV} was not written: nothing to upload.")
    if "billing" not in files:
        print("\n  [!] No billing CSV was written: uploading inventory only.")

    print("\nUploading to Pump …")
    try:
        upload_csvs(pump.api_base, pump.upload_token, files)
    except UploadError as e:
        sys.exit(f"  [!] {e}")


if __name__ == "__main__":
    main()
