import ctypes  # An included library with Python install.
import os
import pathlib
import typing
import sys

##  Styles:
##  0 : OK
##  1 : OK | Cancel
##  2 : Abort | Retry | Ignore
##  3 : Yes | No | Cancel
##  4 : Yes | No
##  5 : Retry | No
##  6 : Cancel | Try Again | Continue
# MB_HELP = 0x4000
# ICON_EXLAIM=0x30
# ICON_INFO = 0x40
# ICON_STOP = 0x10


def MBox(text: str, title: str = 'The Onion Pack', style: int = 0):
    return ctypes.windll.user32.MessageBoxW(0, text, title, style)


def find_file(filename: str, start_at: str = '.') -> typing.Optional[str]:

    def raiser(err):
        raise err

    found = None
    # print(start_at)
    # p = pathlib.WindowsPath(start_at).resolve()
    for root, dirs, files in os.walk(start_at, onerror=raiser):
        if filename in files:
            found = os.path.join(root, filename)
            break




    return found
