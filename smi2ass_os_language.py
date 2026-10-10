"""Read the user's UI language preferences without changing OS settings."""

import ctypes
import sys


def macos_ui_languages():
    cf = ctypes.CDLL('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
    pointer = ctypes.c_void_p
    index_type = ctypes.c_long
    signatures = {
        'CFLocaleCopyPreferredLanguages': ([], pointer),
        'CFArrayGetCount': ([pointer], index_type),
        'CFArrayGetValueAtIndex': ([pointer, index_type], pointer),
        'CFStringGetLength': ([pointer], index_type),
        'CFStringGetMaximumSizeForEncoding': ([index_type, ctypes.c_uint32], index_type),
        'CFStringGetCString': ([pointer, pointer, index_type, ctypes.c_uint32], ctypes.c_bool),
        'CFRelease': ([pointer], None),
    }
    for name, (arguments, result) in signatures.items():
        function = getattr(cf, name)
        function.argtypes, function.restype = arguments, result
    languages = cf.CFLocaleCopyPreferredLanguages()
    if not languages:
        return ()
    try:
        names = []
        for index in range(cf.CFArrayGetCount(languages)):
            value = cf.CFArrayGetValueAtIndex(languages, index)
            length = cf.CFStringGetMaximumSizeForEncoding(cf.CFStringGetLength(value), 0x08000100) + 1
            buffer = ctypes.create_string_buffer(length)
            if cf.CFStringGetCString(value, buffer, length, 0x08000100):
                names.append(buffer.value.decode('utf-8'))
        return tuple(names)
    finally:
        cf.CFRelease(languages)


def windows_ui_languages():
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    preferred = kernel.GetUserPreferredUILanguages
    integer = ctypes.c_uint32
    preferred.argtypes = [integer, ctypes.POINTER(integer), ctypes.c_wchar_p, ctypes.POINTER(integer)]
    preferred.restype = ctypes.c_int
    count, size = integer(), integer()
    if preferred(8, ctypes.byref(count), None, ctypes.byref(size)) and 0 < size.value <= 65536:
        buffer = ctypes.create_unicode_buffer(size.value)
        if preferred(8, ctypes.byref(count), buffer, ctypes.byref(size)):
            names = tuple(name for name in buffer[:].split('\0') if name)
            if names:
                return names
    fallback = kernel.GetUserDefaultUILanguage
    fallback.argtypes, fallback.restype = [], ctypes.c_uint16
    language_id = fallback()
    if not language_id:
        raise OSError('Could not read Windows UI language')
    return ('ko' if language_id & 0x3ff == 0x12 else 'en',)


def preferred_ui_languages():
    if sys.platform == 'darwin':
        return macos_ui_languages()
    if sys.platform == 'win32':
        return windows_ui_languages()
    return ()
