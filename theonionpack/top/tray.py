#####
# We need this patch until pystray has 'notify' capabilities.
# PR was provided @ 20200216

from pystray import Icon as BaseIcon
from pystray import Menu
from pystray import MenuItem
from pystray._win32 import win32

import ctypes
from ctypes import wintypes

# Patch the correct size of 'szTip' into NOTIFYICONDATA
class NOTIFYICONDATA_X(ctypes.Structure):

    class VERSION_OR_TIMEOUT(ctypes.Union):
        _fields_ = [
            ('uTimeout', wintypes.UINT),
            ('uVersion', wintypes.UINT)]

    _fields_ = [
        ('cbSize', wintypes.DWORD),
        ('hWnd', wintypes.HWND),
        ('uID', wintypes.UINT),
        ('uFlags', wintypes.UINT),
        ('uCallbackMessage', wintypes.UINT),
        ('hIcon', wintypes.HICON),
        ('szTip', wintypes.WCHAR * 128),    # this was 64, which is only valid < Windows 20000
        ('dwState', wintypes.DWORD),
        ('dwStateMask', wintypes.DWORD),
        ('szInfo', wintypes.WCHAR * 256),
        ('version_or_timeout', VERSION_OR_TIMEOUT),
        ('szInfoTitle', wintypes.WCHAR * 64),
        ('dwInfoFlags', wintypes.DWORD),
        ('guidItem', wintypes.LPVOID),
        ('hBalloonIcon', wintypes.HICON)
    ]

    _anonymous_ = [
        'version_or_timeout']

# apply the patch back into win32
win32.NOTIFYICONDATA = NOTIFYICONDATA_X
win32.LPNOTIFYICONDATA = ctypes.POINTER(win32.NOTIFYICONDATA)

# We need to re-define as well win32.Shell_NotifyIcon
Shell_NotifyIcon = ctypes.windll.shell32.Shell_NotifyIconW
Shell_NotifyIcon.argtypes = (
    wintypes.DWORD, win32.LPNOTIFYICONDATA)
Shell_NotifyIcon.restype = wintypes.BOOL

win32.Shell_NotifyIcon = Shell_NotifyIcon


class Icon(BaseIcon):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def notify(self, message=None, title=None):
        """Windows only: Show / hide (toast) notification

        :param title: The title <str> of the notification. Will be replaced with the title of the Icon if ``None``.

        :param message: The message <str> of the notification. Set this to ``None`` or ``''`` to hide the notification.

        """
        if message is None:
            self._message(
                win32.NIM_MODIFY,
                win32.NIF_INFO,
                szInfo=''
            )
        else:
            self._message(
                win32.NIM_MODIFY,
                win32.NIF_INFO,
                szInfo=message,
                szInfoTitle=title or self.title or ''
            )
