"""Uploads the menu images to the configured S3 bucket (idempotent).

Run once per environment, e.g. locally against LocalStack or in Railway with
`railway run --service backend python scripts/seed_assets.py`.
"""

import argparse
import sys
from pathlib import Path

from botocore.exceptions import ClientError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.service.assets import build_s3_client  # noqa: E402

DEFAULT_SOURCE = Path(__file__).resolve().parents[2] / "frontend" / "public" / "assets" / "menu"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args()

    files = sorted(args.source.glob("*.jpg"))
    if not files:
        print(f"No .jpg files found in {args.source}", file=sys.stderr)
        return 1

    client = build_s3_client()
    try:
        client.head_bucket(Bucket=settings.S3_BUCKET)
    except ClientError:
        client.create_bucket(Bucket=settings.S3_BUCKET)

    for path in files:
        client.upload_file(
            str(path),
            settings.S3_BUCKET,
            f"menu/{path.name}",
            ExtraArgs={"ContentType": "image/jpeg"},
        )
        print(f"uploaded menu/{path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
