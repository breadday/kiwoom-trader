"""Run one paper-mode, read-only Kiwoom daily-chart smoke test.

Credentials are read from a local kiwoomcli-exported env file and are never
printed. The file must remain outside Git; the repository .gitignore excludes
kiwoom_*.env.
"""

from argparse import ArgumentParser
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api.kiwoom_api import KiwoomAPI


def load_credentials(path: Path) -> None:
    """Load only the demo key names needed by this project's API client."""
    values = {}
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        values[name.strip()] = value.strip()
    try:
        app_key = values["APP_KEY_MOCK"] if "APP_KEY_MOCK" in values else values["KIWOOM_APP_KEY"]
        app_secret = values["APP_SECRET_MOCK"] if "APP_SECRET_MOCK" in values else values["KIWOOM_APP_SECRET"]
        os.environ["KIWOOM_APP_KEY"] = app_key
        os.environ["KIWOOM_APP_SECRET"] = app_secret
    except KeyError as exc:
        raise ValueError(
            "credential file must contain APP_KEY_MOCK/APP_SECRET_MOCK "
            "or KIWOOM_APP_KEY/KIWOOM_APP_SECRET"
        ) from exc


def main() -> int:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--credentials-file", required=True, type=Path)
    parser.add_argument("--code", default="005930")
    parser.add_argument("--base-date", required=True, help="YYYYMMDD")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    load_credentials(args.credentials_file)
    os.environ["KIWOOM_BASE_URL"] = "https://mockapi.kiwoom.com"
    api = KiwoomAPI(paper=True)
    bars = api.get_daily_chart(
        args.code,
        base_dt=args.base_date,
        limit=args.limit,
    )
    if not bars:
        raise RuntimeError("read-only smoke returned no daily bars")
    print(
        "READ_ONLY_SMOKE_OK",
        f"code={args.code}",
        f"bars={len(bars)}",
        f"first_date={bars[0]['date']}",
        f"last_date={bars[-1]['date']}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
