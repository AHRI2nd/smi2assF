"""Publish complete ASS files without exposing partial writes."""
import os
from pathlib import Path
import tempfile


def publish_ass(path: Path, contents: bytes, overwrite: bool) -> str:
    """Stage beside the destination, then atomically publish complete bytes."""
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '.', suffix='.tmp', dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
        if overwrite:
            os.replace(temporary, path)
        else:
            try:
                if os.name == 'nt':
                    # Windows rename refuses an existing destination.
                    os.rename(temporary, path)
                else:
                    # Hard-link publication is atomic and never replaces an entry.
                    os.link(temporary, path)
            except FileExistsError:
                return 'existing'
        return 'written'
    finally:
        temporary.unlink(missing_ok=True)
