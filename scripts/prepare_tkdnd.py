#!/usr/bin/env python3

import hashlib
import io
import platform
import tarfile
from pathlib import Path
from urllib.request import urlopen


TKDND_ARCHIVE_URL = (
    'https://github.com/petasis/tkdnd/releases/download/'
    'tkdnd-release-test-v2.9.5/'
    'tkdnd-2.9.5-macOS-tcl9.0-x86_64-x64-14.2.1.tgz'
)
TKDND_ARCHIVE_SHA256 = (
    '156491344752f9f91601fc873a0f5803f866f17decb86c62fb65af0a6bd8a0dc'
)
TKDND_FILES = frozenset({
    'libtcl9tkdnd2.9.5.dylib',
    'pkgIndex.tcl',
    'tkdnd.tcl',
    'tkdnd_compat.tcl',
    'tkdnd_generic.tcl',
    'tkdnd_macosx.tcl',
    'tkdnd_unix.tcl',
    'tkdnd_utils.tcl',
    'tkdnd_windows.tcl',
})


def needs_tcl9_intel_binary(system, machine, tcl_major):
    return system == 'Darwin' and machine == 'x86_64' and tcl_major >= 9


def install_tkdnd_archive(
    archive_bytes,
    target_directory,
    expected_sha256=TKDND_ARCHIVE_SHA256,
):
    actual_sha256 = hashlib.sha256(archive_bytes).hexdigest()
    if actual_sha256 != expected_sha256:
        raise ValueError('TkDND archive SHA-256 checksum mismatch.')

    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode='r:gz') as archive:
        members = archive.getmembers()
        file_members = [member for member in members if member.isfile()]
        directory_names = {
            member.name.rstrip('/') for member in members if member.isdir()
        }
        expected_names = {
            'tkdnd2.9.5/' + filename for filename in TKDND_FILES
        }
        if (
            {member.name for member in file_members} != expected_names
            or directory_names != {'tkdnd2.9.5'}
            or len(file_members) + len(directory_names) != len(members)
        ):
            raise ValueError('TkDND archive has unexpected archive contents.')

        target_directory = Path(target_directory)
        target_directory.mkdir(parents=True, exist_ok=True)
        for member in file_members:
            filename = Path(member.name).name
            source = archive.extractfile(member)
            if source is None:
                raise ValueError('TkDND archive contains an unreadable file.')
            (target_directory / filename).write_bytes(source.read())


def main():
    if platform.system() != 'Darwin' or platform.machine() != 'x86_64':
        return 0

    import tkinter
    import tkinterdnd2

    tcl_major = int(tkinter.Tcl().eval('info patchlevel').split('.')[0])
    if not needs_tcl9_intel_binary('Darwin', 'x86_64', tcl_major):
        return 0

    package_directory = Path(tkinterdnd2.__file__).resolve().parent
    target_directory = package_directory / 'tkdnd' / 'osx-x64-tcl9'
    expected_binary = target_directory / 'libtcl9tkdnd2.9.5.dylib'
    if expected_binary.is_file():
        print('Intel Mac Tcl 9 TkDND binary is already installed.')
        return 0

    print('Installing the Tcl 9 TkDND binary for Intel macOS...')
    with urlopen(TKDND_ARCHIVE_URL, timeout=30) as response:
        archive_bytes = response.read()
    install_tkdnd_archive(archive_bytes, target_directory)
    print('Installed verified Intel Mac Tcl 9 TkDND binary.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
