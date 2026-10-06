import os
from pathlib import Path


SUPPORTED_SUFFIXES = {'.smi', '.SMI'}


def collect_smi_files(paths):
    found = {}
    for raw_path in paths:
        path = Path(raw_path).expanduser()
        if path.is_dir():
            candidates = path.rglob('*')
        elif path.is_file() and path.suffix in SUPPORTED_SUFFIXES:
            candidates = (path,)
        else:
            continue

        for candidate in candidates:
            if candidate.is_file() and candidate.suffix in SUPPORTED_SUFFIXES:
                resolved = candidate.resolve()
                found[os.path.normcase(str(resolved))] = resolved

    return sorted(found.values(), key=lambda item: str(item).casefold())
