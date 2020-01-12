#!/usr/bin/env python
import ctypes
import os
import pathlib
import subprocess
import sys
import tempfile
from time import sleep
import threading
import uuid
import webbrowser
import winreg

from filelock import FileLock, Timeout
from PIL import Image
import pystray

from . import tor
from . import box
from .simplecontroller import SimplePort
from .util import MBox

# Hide the console...
kernel32 = ctypes.WinDLL('kernel32')
user32 = ctypes.WinDLL('user32')
SW_HIDE = 0
hWnd = kernel32.GetConsoleWindow()
if hWnd:
    user32.ShowWindow(hWnd, SW_HIDE)


class Pack():

    def __init__(self, config):
        self.config = config

        self.cwd = pathlib.WindowsPath(self.config['cwd'])

        self.status = 0

        # Prepare Tor
        self.password = uuid.uuid4().hex
        self.relay = tor.Tor(self.config['tor'], self.config['data'])

        # torrc
        torrc = pathlib.Path(config['data']) / 'torrc' / 'torrc'
        self.torrc = torrc.resolve()

        # The Onion Box
        self.box = box.TheOnionBox(config)

        # Stop signal, to terminate our run_loop
        self.stop = threading.Event()

        # the Tray icon
        self.tray = pystray.Icon('theonionpack', title='The Onion Pack')

        self.tray.icon = Image.open(str(self.cwd / 'icons' / 'top16.ico'))

        self.tray.menu = pystray.Menu(
            pystray.MenuItem(
                'Monitor...',
                action=self.on_monitor,
                default=True
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                'Relay Control',
                pystray.Menu(
                    pystray.MenuItem(
                        'Edit configuration file...',
                        action=self.on_open_torrc
                    ),
                    pystray.MenuItem(
                        'Show logfile...',
                        action=self.on_show_messages
                    ),
                    pystray.Menu.SEPARATOR,
                    pystray.MenuItem(
                        'Reload relay configuration',
                        action=self.on_reload_config
                    )
                )
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                'Stop!',
                action=self.on_quit
            )
        )

    def run(self):

        self.lock = FileLock(str(self.cwd / 'theonionpack.lock'))
        running = False

        try:
            with self.lock.acquire(timeout=0):

                # run The Onion Box
                tob = self.box.run(password=self.password)

                # run Tor
                self.relay.run(password=self.password)

                running = True

                # run the Tray icon
                # !! This is a blocking call !!
                self.tray.run(self.run_loop)

                # the block may be released by self.on_quit, issued by an operator via the Tray
                # ... or by a system command (like SIGTERM).

        except Timeout:
            MBox("It seems like another instance of The Onion Pack is already running. Aborting launch procedure...",
                 style=0x10)

        finally:
            self.lock.release()

        if running:

            # Stop theonionbox
            self.box.stop()

            # Tor has OwningControllerProcess defined ... thus will terminate as soon as we're done.

            if self.status == 1:
                MBox("Our instance of TheOnionBox terminated.\r\nThus we have to terminate as well! Sorry...",
                     style=0x10)

        sys.exit(0)

    def run_loop(self, icon: pystray.Icon):

        icon.visible = True

        while self.stop.is_set() is False:

            # quit if TheOnionBox died!
            if self.box.poll() is not None:

                # indicate that the Box terminated!
                self.status += 1
                self.do_quit()
                return

            self.relay.collect_messages()
            sleep(1)

    # Tray menu actions
    def on_monitor(self, icon, item):
        webbrowser.open_new_tab('http://127.0.0.1:8080/')

    def on_quit(self, icon, item):
        self.do_quit()

    def do_quit(self):

        # Stop the run_loop
        self.stop.set()

        # Stop the Tray
        self.tray.stop()

        # cleanup is being performed in self.run()

    # def get_tor_messages(self):
    #     while True:
    #         self.relay.collect_messages()
    #         sleep(5)

    def on_show_messages(self, icon, item):
        fd, name = tempfile.mkstemp(prefix="Tor_", suffix='.html', text=True)
        with open(fd, 'w') as tmp:
            tmp.write('<br>'.join(self.relay.messages))
        webbrowser.open_new_tab(name)

    def on_open_torrc(self):

        def get_default_windows_app(suffix):

            class_root = winreg.QueryValue(winreg.HKEY_CLASSES_ROOT, suffix)
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r'{}\shell\open\command'.format(class_root)) as key:
                command = winreg.QueryValueEx(key, '')[0]
                return command.split(' ')[0]

        if not self.torrc.exists():
            self.torrc.parent.mkdir(parents=True, exist_ok=True)
            self.torrc.touch()

        path = get_default_windows_app('.txt')
        subprocess.Popen([os.path.expandvars(path), str(self.torrc)])

    def on_reload_config(self):

        controller = None
        try:
            controller = SimplePort('127.0.0.1', 9051)
        except Exception:
            MBox('Failed to connect to the local Tor relay.', style=0x10)

        if controller is None:
            return

        ok = ''
        try:
            ok = controller.msg(f'AUTHENTICATE "{self.password}"')
        except:
            if ok != '250 OK':
                MBox('Failed to authenticate against local Tor relay.', style=0x10)
                controller.shutdown()
                return

        ok = ''
        try:
            ok = controller.msg("SIGNAL RELOAD")
        except:
            if ok != '250 OK':
                MBox('Failed to reload the Tor relay configuration.', style=0x10)

        controller.shutdown()
        return
