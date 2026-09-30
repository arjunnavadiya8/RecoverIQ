from __future__ import annotations

import argparse
import json

from recoveriq.config import ARTIFACT_DIR, DB_PATH, REPORT_DIR, ROOT
from recoveriq.data import download_olist, generate_demo_data, ingest_raw


def _warehouse() -> dict[str, str]:
    from dbt.cli.main import dbtRunner

    result = dbtRunner().invoke(
        ["build", "--project-dir", str(ROOT), "--profiles-dir", str(ROOT)]
    )
    if not result.success:
        raise RuntimeError("dbt build failed")
    return {"status": "built", "database": str(DB_PATH)}


def _clean_derived() -> dict[str, int]:
    removed = 0
    if DB_PATH.exists():
        DB_PATH.unlink()
        removed += 1
    for directory in [ARTIFACT_DIR, REPORT_DIR]:
        if directory.exists():
            for path in directory.iterdir():
                if path.is_file() and path.name != ".gitkeep":
                    path.unlink()
                    removed += 1
    return {"removed_files": removed}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="recoveriq")
    sub = parser.add_subparsers(dest="command", required=True)
    download = sub.add_parser("download")
    download.add_argument("--force", action="store_true")
    demo = sub.add_parser("demo-data")
    demo.add_argument("--rows", type=int, default=2500)
    demo.add_argument("--force", action="store_true")
    sub.add_parser("ingest")
    sub.add_parser("warehouse")
    sub.add_parser("train")
    causal = sub.add_parser("causal")
    causal.add_argument("--bootstrap", type=int, default=500)
    pipeline = sub.add_parser("pipeline")
    pipeline.add_argument("--demo", action="store_true")
    pipeline.add_argument("--rows", type=int, default=2500)
    sub.add_parser("clean-derived")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "download":
        output = download_olist(args.force)
    elif args.command == "demo-data":
        output = generate_demo_data(args.rows, args.force)
    elif args.command == "ingest":
        output = ingest_raw()
    elif args.command == "warehouse":
        output = _warehouse()
    elif args.command == "train":
        from recoveriq.modeling import train_models

        output = train_models()
    elif args.command == "causal":
        from recoveriq.causal import run_causal_analysis

        output = run_causal_analysis(args.bootstrap)
    elif args.command == "clean-derived":
        output = _clean_derived()
    elif args.command == "pipeline":
        from recoveriq.causal import run_causal_analysis
        from recoveriq.modeling import train_models

        if args.demo:
            generate_demo_data(args.rows, force=True)
        else:
            download_olist()
        ingest_raw()
        _warehouse()
        output = {"training": train_models(), "causal": run_causal_analysis()}
    else:
        raise AssertionError(args.command)
    print(json.dumps(output, indent=2, default=str))


if __name__ == "__main__":
    main()
