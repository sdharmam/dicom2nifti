# AGENTS.md

Guidance for AI coding agents working in this repository.

## Project

Batch converter from a nested DICOM folder tree to NIfTI (`.nii.gz`).

Expected input hierarchy:

```
root/
  phase/              # e.g. arterial, venous, delayed
    mrn/              # patient medical record number
      accession/      # study accession number
        series/       # one folder per DICOM series
          *.dcm
```

Output mirrors the same hierarchy under a user-specified output root.

## Entry point

- `convert_dicom_to_nifti.py` — single-file CLI. Walks the 4-level hierarchy and runs `dcm2niix -z y` on each leaf series in parallel via `ProcessPoolExecutor`.

```
python convert_dicom_to_nifti.py <input_root> <output_root> [--workers N]
```

## Dependencies

- Python 3.9+ (uses `tuple[...]` PEP 604 generics).
- `dcm2niix` on `PATH` (`brew install dcm2niix` on macOS, `apt install dcm2niix` on Debian/Ubuntu).
- No Python package dependencies — standard library only.

## Conventions

- Keep the tool single-file and stdlib-only unless there is a strong reason to add a dependency.
- The folder depth (`phase/mrn/accession/series`) is load-bearing. If you generalize it, keep the 4-level walker as the default and add an opt-in flag for depth-tolerant walking — do not silently change behavior.
- Output filenames use the dcm2niix pattern `%p_%s` (protocol + series number). Patient identifiers (mrn, accession) live in the **folder path**, not the filename, so the output stays de-identifiable by dropping parent directories.
- Failures on individual series must not abort the whole run. The pool collects per-series results and prints a final `ok/fail` tally; preserve that behavior.

## Data handling

- This tool processes PHI (DICOM headers contain patient identifiers). Do not log header contents, MRNs, or accession numbers beyond the folder path already shown in progress output.
- Never commit sample DICOMs, NIfTIs, or any folder named like an MRN/accession to the repo.

## Testing

- No automated tests yet. When adding features, smoke-test against a small synthetic tree:
  ```
  mkdir -p /tmp/dcm_in/phaseA/MRN1/ACC1/series1
  # drop a few .dcm files in series1
  python convert_dicom_to_nifti.py /tmp/dcm_in /tmp/dcm_out --workers 1
  ```
- Verify the output path mirrors the input path and at least one `.nii.gz` appears.

## Commit style

- Imperative subject, ~70 chars max.
- Body explains the *why* when non-obvious.
- Do not add AI co-author trailers.
