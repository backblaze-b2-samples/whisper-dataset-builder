#!/usr/bin/env python
"""Bulk-build a speech dataset for source recordings on B2.

Lists the sources/ prefix and runs the full VAD -> filter -> transcribe ->
package pipeline (via the service layer) for each recording, creating one
dataset per source. This is the write-amplification demo: one pass over the
source library fans out many labeled clip/transcript pairs across the bucket.

Run from the repo root:
    pnpm build:dataset                      # build a dataset for every source
    pnpm build:dataset -- --source KEY      # only this source recording
    pnpm build:dataset -- --layout hf_audiofolder

Or directly:
    cd services/api && .venv/bin/python scripts/build_dataset.py

Requires the ML stack (requirements-ml.txt) + ffmpeg. The .env at the repo root
supplies B2 credentials and (optionally) HF_TOKEN to use the pyannote VAD.
"""

import argparse
import logging
import sys
from pathlib import Path

# Make `app` importable when run as `python scripts/build_dataset.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

from app.service.build import build_dataset  # noqa: E402
from app.service.datasets import create_dataset, list_sources  # noqa: E402
from app.service.engine import pyannote_available, resolve_engine  # noqa: E402
from app.types import DatasetConfig  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("build_dataset")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bulk build speech datasets from B2 audio")
    parser.add_argument("--source", help="Only build for this source key")
    parser.add_argument(
        "--layout",
        choices=["ljspeech", "hf_audiofolder"],
        default="ljspeech",
    )
    parser.add_argument("--model", choices=["tiny", "base", "small"], default="base")
    args = parser.parse_args()

    engine = resolve_engine("auto")
    if not pyannote_available():
        log.warning("HF_TOKEN unset — using the token-free energy VAD fallback.")
    log.info("VAD engine: %s", engine)

    sources = list_sources()
    if args.source:
        sources = [s for s in sources if s.key == args.source]
    if not sources:
        log.info("No matching source recordings under sources/ — upload some first.")
        return 0

    log.info("Building datasets for %d source recording(s).", len(sources))
    failures = 0
    for i, s in enumerate(sources, start=1):
        log.info("[%d/%d] Building dataset for %s", i, len(sources), s.key)
        try:
            ds = create_dataset(
                name=s.filename,
                description=f"Auto-built from {s.key}",
                config=DatasetConfig(
                    source_key=s.key, layout=args.layout, whisper_model=args.model
                ),
            )
            built = build_dataset(ds)
            log.info("  -> %d clips (%.1fx amplification)", built.stats.clips_kept,
                     built.stats.write_amplification)
        except Exception:  # keep going through the batch
            failures += 1
            log.exception("Failed: %s", s.key)

    log.info("Done. %d succeeded, %d failed.", len(sources) - failures, failures)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
