import os
import sys

import pytest

from pump_azure_radar import cli


def _run_main(monkeypatch, tmp_path, argv, write=("azure_inventory.csv", "azure_billing.csv"),
              exit_code=0):
    seen = {}
    monkeypatch.chdir(tmp_path)

    def fake_app(args, prog_name):
        seen["args"] = list(args)
        for name in write:
            (tmp_path / name).write_text("a,b\n1,2\n")
        raise SystemExit(exit_code)  # Typer's standalone mode always exits

    monkeypatch.setattr("azure_radar.cli.app", fake_app)
    monkeypatch.setattr("pump_azure_radar.upload.upload_csvs",
                        lambda base, token, files: seen.update(base=base, token=token,
                                                                files=sorted(files)))
    monkeypatch.setattr(sys, "argv", ["pump-azure-radar"] + argv)
    cli.main()
    return seen


def test_run_with_token_strips_flags_adds_billing_and_uploads(monkeypatch, tmp_path):
    seen = _run_main(monkeypatch, tmp_path, ["run", "--days", "60", "--upload-token", "T"])
    assert seen["args"] == ["run", "--days", "60", "--billing"]
    assert (seen["token"], seen["base"]) == ("T", "https://api.pump.co")
    assert seen["files"] == ["billing", "inventory"]


def test_custom_billing_output_is_uploaded(monkeypatch, tmp_path):
    seen = _run_main(monkeypatch, tmp_path,
                     ["run", "--billing", "--billing-output", "spend.csv", "--upload-token", "T"],
                     write=("azure_inventory.csv", "spend.csv"))
    assert seen["args"].count("--billing") == 1
    assert seen["files"] == ["billing", "inventory"]


def test_api_base_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("PUMP_API_BASE", "http://localhost:8001")
    seen = _run_main(monkeypatch, tmp_path, ["run", "--upload-token", "T"])
    assert seen["base"] == "http://localhost:8001"


def test_stale_billing_csv_is_not_uploaded(monkeypatch, tmp_path):
    stale = tmp_path / "azure_billing.csv"
    stale.write_text("old\n")
    os.utime(stale, (1, 1))
    seen = _run_main(monkeypatch, tmp_path, ["run", "--upload-token", "T"],
                     write=("azure_inventory.csv",))
    assert seen["files"] == ["inventory"]


def test_run_without_token_does_not_upload(monkeypatch, tmp_path):
    seen = _run_main(monkeypatch, tmp_path, ["run"])
    assert "token" not in seen
    assert seen["args"] == ["run"]


def test_failed_run_does_not_upload(monkeypatch, tmp_path):
    with pytest.raises(SystemExit):
        _run_main(monkeypatch, tmp_path, ["run", "--upload-token", "T"], exit_code=1)


def test_token_rejected_outside_run(monkeypatch, tmp_path):
    with pytest.raises(SystemExit):
        _run_main(monkeypatch, tmp_path, ["inventory", "--upload-token", "T"])
