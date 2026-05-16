"""Data lineage helpers for manual CSV snapshots."""

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

SNAPSHOT_COLUMNS = ["data_snapshot_id", "source", "last_updated_utc"]


def parse_utc(value, context):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{context} has invalid last_updated_utc: {value}") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{context} last_updated_utc must include timezone")
    return parsed.astimezone(timezone.utc)


def file_sha256(path):
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def data_snapshot_hash(paths=None):
    from src.data_loader import FIXTURES_FILE, OVERRIDES_FILE, STATE_FILE

    paths = paths or [STATE_FILE, FIXTURES_FILE, OVERRIDES_FILE]
    digest = sha256()
    for path in paths:
        path = Path(path)
        digest.update(path.name.encode("utf-8"))
        digest.update(file_sha256(path).encode("utf-8"))
    return digest.hexdigest()[:16]


def collect_snapshot_metadata(paths=None):
    import pandas as pd
    from src.data_loader import FIXTURES_FILE, OVERRIDES_FILE, STATE_FILE

    paths = paths or [STATE_FILE, FIXTURES_FILE, OVERRIDES_FILE]
    rows = []
    for path in paths:
        df = pd.read_csv(path, nrows=1)
        missing = [col for col in SNAPSHOT_COLUMNS if col not in df.columns]
        if missing:
            raise ValueError(f"{Path(path).name} is missing metadata columns: {', '.join(missing)}")
        rows.append(
            {
                "file": Path(path).name,
                "data_snapshot_id": str(df.loc[0, "data_snapshot_id"]),
                "source": str(df.loc[0, "source"]),
                "last_updated_utc": parse_utc(df.loc[0, "last_updated_utc"], Path(path).name).isoformat(),
                "file_hash": file_sha256(path)[:16],
            }
        )
    return rows
