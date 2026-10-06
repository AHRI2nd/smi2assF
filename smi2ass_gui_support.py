import os
import stat
from dataclasses import dataclass
from pathlib import Path


SUPPORTED_SUFFIXES = {'.smi', '.SMI'}


@dataclass(frozen=True)
class SmiScanResult:
    files: tuple
    errors: tuple


def scan_smi_files(paths):
    found = {}
    errors = []
    for raw_path in paths:
        path = Path(raw_path).expanduser()
        try:
            mode = path.stat().st_mode
        except FileNotFoundError:
            continue
        except OSError as error:
            errors.append((path, error))
            continue

        if stat.S_ISDIR(mode):
            def on_walk_error(error, root=path):
                errors.append((Path(error.filename or root), error))

            for directory, _, filenames in os.walk(path, onerror=on_walk_error):
                for filename in filenames:
                    candidate = Path(directory) / filename
                    if candidate.suffix in SUPPORTED_SUFFIXES:
                        resolved = candidate.resolve()
                        found[os.path.normcase(str(resolved))] = resolved
        elif stat.S_ISREG(mode) and path.suffix in SUPPORTED_SUFFIXES:
            candidate = path
            resolved = candidate.resolve()
            found[os.path.normcase(str(resolved))] = resolved

    return SmiScanResult(
        files=tuple(sorted(found.values(), key=lambda item: str(item).casefold())),
        errors=tuple(errors),
    )


def collect_smi_files(paths):
    """Return supported subtitle files while preserving the legacy list API."""
    return list(scan_smi_files(paths).files)
