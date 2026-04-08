from __future__ import annotations

from datetime import datetime, timezone
import json
import sys

from dotenv import load_dotenv

from src.config import AppConfig
from src.runner import run_monitoring, run_result_to_dict


def main() -> int:
    load_dotenv()

    try:
        config = AppConfig.from_env()
    except ValueError as exc:
        error_payload = {
            "status": "configuration_error",
            "error": str(exc),
        }
        print(json.dumps(error_payload, ensure_ascii=False), file=sys.stderr)
        return 2

    now_utc = datetime.now(timezone.utc)
    try:
        result = run_monitoring(config=config, now_utc=now_utc)
    except Exception as exc:  # pylint: disable=broad-except
        error_payload = {
            "status": "runtime_error",
            "error": str(exc),
        }
        print(json.dumps(error_payload, ensure_ascii=False), file=sys.stderr)
        return 1

    print(json.dumps(run_result_to_dict(result), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
