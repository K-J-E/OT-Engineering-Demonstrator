#!/usr/bin/env python3
"""Generate the local application build-identity manifest for review evidence."""

import argparse
from pathlib import Path

from ot_demo.infrastructure.build_identity import write_build_manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--node-command", default="node")
    parser.add_argument("--npm-command", default="npm")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("build/manifests/application-build.json"),
    )
    args = parser.parse_args()
    repository_root = Path(__file__).resolve().parents[1]
    manifest = write_build_manifest(
        repository_root,
        repository_root / args.output,
        node_command=args.node_command,
        npm_command=args.npm_command,
    )
    print(manifest.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
