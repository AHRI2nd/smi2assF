"""Publish complete ASS files without exposing partial writes."""
import os
import stat
from pathlib import Path
import tempfile


class UnsafeOutputPath(OSError):
    """An output entry is not an ordinary file."""


def validate_output(path: Path):
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return
    if not stat.S_ISREG(mode) or path.is_symlink() or path.is_junction():
        raise UnsafeOutputPath('Unsafe output entry: %s' % path)


def publish_ass(path: Path, contents: bytes, overwrite: bool) -> str:
    """Stage beside the destination, then atomically publish complete bytes."""
    validate_output(path)
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '.', suffix='.tmp', dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
        validate_output(path)
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
                validate_output(path)
                return 'existing'
        return 'written'
    finally:
        temporary.unlink(missing_ok=True)
