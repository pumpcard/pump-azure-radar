"""Rewrite azure-radar's inventory with the columns Pump's analysis reads.

azure-radar's inventory has no resource id, subscription or tags, and lists the
``az`` default subscription even when ``AZURE_SUBSCRIPTION_ID`` names the one its
billing reads. Pump joins the two files and checks tagging and ownership, so the
upload is relisted from the billed subscription with those columns added.
"""

import csv
import json
import subprocess

from azure_radar.billing import get_subscription_id
from azure_radar.inventory import normalize_service_type

COLUMNS = ["Id", "Name", "Type", "ServiceType", "ResourceGroup", "Location", "SubscriptionId", "Tags"]
QUERY = "[].{id: id, name: name, type: type, resourceGroup: resourceGroup, location: location, tags: tags}"


def write_inventory(path):
    """Write the billed subscription's resources to *path* and return how many there were."""
    subscription_id = get_subscription_id()
    result = subprocess.run(
        ["az", "resource", "list", "--subscription", subscription_id, "--query", QUERY, "-o", "json"],
        capture_output=True,
        text=True,
        check=True,
    )
    resources = json.loads(result.stdout)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        for r in resources:
            writer.writerow([
                r["id"],
                r["name"],
                r["type"],
                normalize_service_type(r["type"]),
                r["resourceGroup"],
                r["location"],
                subscription_id,
                json.dumps(r["tags"]) if r["tags"] else "",
            ])
    return len(resources)
