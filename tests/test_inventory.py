import csv
import json
import subprocess

from pump_azure_radar import inventory

VM_ID = "/subscriptions/sub-1/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/vm1"


def test_relists_the_billed_subscription_with_ids_and_tags(monkeypatch, tmp_path):
    monkeypatch.setenv("AZURE_SUBSCRIPTION_ID", "sub-1")
    resources = [
        {"id": VM_ID, "name": "vm1", "type": "Microsoft.Compute/virtualMachines",
         "resourceGroup": "rg", "location": "eastus", "tags": {"env": "dev", "owner": "data"}},
        {"id": "/subscriptions/sub-1/resourceGroups/rg/providers/Microsoft.Storage/storageAccounts/st1",
         "name": "st1", "type": "Microsoft.Storage/storageAccounts",
         "resourceGroup": "rg", "location": "eastus", "tags": None},
    ]
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, stdout=json.dumps(resources), stderr="")

    monkeypatch.setattr(inventory.subprocess, "run", fake_run)
    path = tmp_path / "azure_inventory.csv"

    assert inventory.write_inventory(path) == 2
    assert calls[0][:5] == ["az", "resource", "list", "--subscription", "sub-1"]
    with open(path, newline="") as f:
        vm, storage = csv.DictReader(f)
    assert (vm["Id"], vm["ServiceType"], vm["SubscriptionId"]) == (VM_ID, "Virtual Machines", "sub-1")
    assert json.loads(vm["Tags"]) == {"env": "dev", "owner": "data"}
    assert storage["Tags"] == ""
