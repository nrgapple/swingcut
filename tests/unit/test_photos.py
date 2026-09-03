from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

import swingcut.sources.photos as photos_module
from swingcut.sources.photos import (
    PhotoAlbumInventory,
    PhotoAssetRecord,
    PhotosBridgeCancelled,
    PhotosBridgeClient,
    PhotosBridgeError,
    PhotosBridgeTimeout,
)


class FakeProcess:
    stderr = None

    def poll(self) -> int:
        return 0


class BridgeHarness:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []
        self.handler: Any = None

    def popen(self, command: list[str], **_: object) -> FakeProcess:
        self.commands.append(command)
        result = Path(command[command.index("--result-file") + 1])
        error = Path(command[command.index("--error-file") + 1])
        if self.handler is not None:
            self.handler(command, result, error)
        return FakeProcess()


def _private_write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")
    os.chmod(path, 0o600)


@pytest.fixture
def bridge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[PhotosBridgeClient, BridgeHarness]:
    app = tmp_path / "SwingcutPhotosBridge.app"
    app.mkdir()
    harness = BridgeHarness()
    monkeypatch.setattr(photos_module.subprocess, "Popen", harness.popen)
    client = PhotosBridgeClient(app, timeout_seconds=0.04, poll_seconds=0.005)
    return client, harness


def test_inventory_uses_launchservices_argument_array_and_exact_album(
    bridge: tuple[PhotosBridgeClient, BridgeHarness],
) -> None:
    client, harness = bridge
    harness.handler = lambda _command, result, _error: _private_write(
        result,
        {
            "album": "Exact; $(private)",
            "assets": [
                {
                    "assetID": "private-id",
                    "filename": "private.mov",
                    "creationDate": "2024-01-01T00:00:00Z",
                    "durationSeconds": 2.5,
                    "width": 1080,
                    "height": 1920,
                }
            ],
        },
    )

    inventory = client.inventory_album("Exact; $(private)")

    assert inventory.album == "Exact; $(private)"
    assert len(inventory.assets) == 1
    command = harness.commands[0]
    assert command[:5] == ["/usr/bin/open", "-n", "-a", str(client.app_path), "--args"]
    assert command[5:8] == ["list", "--album", "Exact; $(private)"]
    assert "--cancel-file" in command


def test_inventory_rejects_wrong_album_and_nonprivate_response(
    bridge: tuple[PhotosBridgeClient, BridgeHarness],
) -> None:
    client, harness = bridge
    harness.handler = lambda _command, result, _error: _private_write(
        result, {"album": "Other", "assets": []}
    )
    with pytest.raises(PhotosBridgeError, match="different album"):
        client.inventory_album("Exact")

    def public_result(_command: list[str], result: Path, _error: Path) -> None:
        result.write_text('{"album":"Exact","assets":[]}', encoding="utf-8")
        os.chmod(result, 0o644)

    harness.handler = public_result
    with pytest.raises(PhotosBridgeError, match="permissions"):
        client.inventory_album("Exact")


def test_export_is_sequential_hashed_and_preserves_per_asset_failures(
    bridge: tuple[PhotosBridgeClient, BridgeHarness], tmp_path: Path
) -> None:
    client, harness = bridge
    inventory = PhotoAlbumInventory(
        album="Exact",
        assets=[
            PhotoAssetRecord(
                assetID="one",
                filename="one.MP4",
                creationDate=None,
                durationSeconds=1.0,
                width=100,
                height=200,
            ),
            PhotoAssetRecord(
                assetID="two",
                filename="two.mov",
                creationDate=None,
                durationSeconds=1.0,
                width=100,
                height=200,
            ),
        ],
    )

    def export(command: list[str], result: Path, error: Path) -> None:
        asset_id = command[command.index("--asset-id") + 1]
        output = Path(command[command.index("--output") + 1])
        if asset_id == "two":
            error.write_text("synthetic source failure", encoding="utf-8")
            os.chmod(error, 0o600)
            return
        output.write_bytes(b"local exported copy")
        _private_write(
            result,
            {"assetID": asset_id, "outputPath": str(output), "bytes": output.stat().st_size},
        )

    harness.handler = export
    batch = client.export_album(inventory, tmp_path / "private-stage")

    assert len(batch.exported) == 1
    assert batch.exported[0].path.name == "asset-00001.mp4"
    assert batch.exported[0].content_sha256 == (
        "acdb7aed194986bc84e695aefa745c68b2806243c2896a4e4d505e33d4dfdda0"
    )
    assert [failure.asset_id for failure in batch.failures] == ["two"]
    assert len(harness.commands) == 2
    assert (tmp_path / "private-stage").stat().st_mode & 0o777 == 0o700


def test_import_requires_regular_file_and_verified_creation(
    bridge: tuple[PhotosBridgeClient, BridgeHarness], tmp_path: Path
) -> None:
    client, harness = bridge
    output = tmp_path / "Swingcut synthetic compilation.mp4"
    output.write_bytes(b"synthetic")
    harness.handler = lambda _command, result, _error: _private_write(
        result, {"assetID": "new-id", "verified": True}
    )

    imported = client.import_output(output)

    assert imported.asset_id == "new-id"
    command = harness.commands[0]
    assert command[5:8] == ["import-output", "--input", str(output.resolve())]

    link = tmp_path / "link.mp4"
    link.symlink_to(output)
    with pytest.raises(PhotosBridgeError, match="symbolic"):
        client.import_output(link)


def test_cancellation_and_timeout_are_bounded(
    bridge: tuple[PhotosBridgeClient, BridgeHarness],
) -> None:
    client, harness = bridge
    harness.handler = lambda _command, _result, _error: None

    with pytest.raises(PhotosBridgeCancelled):
        client.inventory_album("Exact", cancelled=lambda: True)
    with pytest.raises(PhotosBridgeTimeout):
        client.inventory_album("Exact")
