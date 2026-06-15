#!/usr/bin/env python3
"""
Convert a nested DICOM folder tree to NIfTI.

Expected input structure:
    root/
        phase_folder/
            mrn/
                accession_number/
                    series/
                        *.dcm

Output mirrors the same hierarchy, with each `series` folder converted
to one or more .nii.gz files via dcm2niix.

Usage:
    python convert_dicom_to_nifti.py <input_root> <output_root> [--workers N]

Requires `dcm2niix` on PATH (brew install dcm2niix).
"""

import argparse
import shutil
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path


def has_dicoms(folder: Path) -> bool:
    for p in folder.iterdir():
        if p.is_file():
            return True
    return False


def convert_series(series_dir: Path, out_dir: Path) -> tuple[Path, bool, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "dcm2niix",
        "-z", "y",          # gzip output
        "-f", "%p_%s",      # filename: protocol_seriesnum
        "-o", str(out_dir),
        str(series_dir),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        ok = result.returncode == 0
        msg = result.stderr.strip() or result.stdout.strip().splitlines()[-1] if result.stdout else ""
        return series_dir, ok, msg
    except Exception as e:
        return series_dir, False, str(e)


def find_series(input_root: Path):
    """Yield (series_dir, relative_path) for every leaf series folder."""
    for phase in sorted(p for p in input_root.iterdir() if p.is_dir()):
        for mrn in sorted(p for p in phase.iterdir() if p.is_dir()):
            for accession in sorted(p for p in mrn.iterdir() if p.is_dir()):
                for series in sorted(p for p in accession.iterdir() if p.is_dir()):
                    if has_dicoms(series):
                        yield series, series.relative_to(input_root)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input_root", type=Path)
    ap.add_argument("output_root", type=Path)
    ap.add_argument("--workers", type=int, default=4, help="parallel dcm2niix processes")
    args = ap.parse_args()

    if shutil.which("dcm2niix") is None:
        sys.exit("error: dcm2niix not found on PATH (try: brew install dcm2niix)")

    if not args.input_root.is_dir():
        sys.exit(f"error: input root not found: {args.input_root}")

    args.output_root.mkdir(parents=True, exist_ok=True)

    jobs = [(s, args.output_root / rel) for s, rel in find_series(args.input_root)]
    if not jobs:
        sys.exit("no series folders with files found under input root")

    print(f"found {len(jobs)} series; converting with {args.workers} workers")
    n_ok = n_fail = 0
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(convert_series, s, o): s for s, o in jobs}
        for fut in as_completed(futures):
            series, ok, msg = fut.result()
            tag = "ok " if ok else "FAIL"
            print(f"[{tag}] {series}")
            if not ok:
                print(f"       {msg}")
                n_fail += 1
            else:
                n_ok += 1

    print(f"\ndone: {n_ok} succeeded, {n_fail} failed")
    sys.exit(0 if n_fail == 0 else 1)


if __name__ == "__main__":
    main()
