#!/usr/bin/env python
import configparser
import contextlib
import ctypes
import datetime
# import logging
import os
import pathlib
import random
import subprocess
import sys
import tempfile
from time import sleep, strftime, localtime, time
from typing import Optional
import threading
import uuid
import webbrowser
import winreg

from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.background import BackgroundScheduler
from filelock import FileLock, Timeout
from PIL import Image
# import pystray
import requests
from requests.exceptions import SSLError

from . import tor
from . import tray as pystray   # to patch 'notify' capabilities into pystray
from . import box
from .simplecontroller import SimplePort
from .util import MBox
from .version import VersionManager


# Hide the console...
kernel32 = ctypes.WinDLL('kernel32')
user32 = ctypes.WinDLL('user32')
SW_HIDE = 0
hWnd = kernel32.GetConsoleWindow()

filetime = os.path.getmtime(__file__)
__stamp__ = strftime('%Y%m%d|%H%M%S', localtime(filetime))


class Pack:

    def __init__(self, config):

        self.cron = BackgroundScheduler()

        self.config = config

        self.cwd = pathlib.WindowsPath(self.config['cwd'])

        self.status = 0
        self.update_status = None
        self.update_stamp = None

        # Hide the ConsoleWindow - if not in Debug or Trace mode!
        if hWnd and not (config['debug'] or config['trace']):
            user32.ShowWindow(hWnd, SW_HIDE)

        # The Version Management system
        self.vm = VersionManager('127.0.0.1:9050', __stamp__)

        # Prepare Tor
        self.password = uuid.uuid4().hex
        self.relay = tor.Tor(self.config['tor'], self.config['data'])

        # torrc
        torrc = pathlib.Path(config['data']) / 'torrc' / 'torrc'
        self.torrc = torrc.resolve()
        if not self.torrc.exists():
            self.torrc.parent.mkdir(parents=True, exist_ok=True)
            self.torrc.touch()

        # The Onion Box
        self.box = box.TheOnionBox(config)

        # Stop signal, to terminate our run_loop
        self.stop = threading.Event()

        # Our App ... to configure TOP & control Tor
        from .app import App
        self.app = App(self)

        # the Tray icon
        self.tray = pystray.Icon('theonionpack', title='The Onion Pack')

        self.tray.icon = Image.open(str(self.cwd / 'icons' / 'top16.ico'))

        self.tray.menu = pystray.Menu(
            pystray.MenuItem(
                'Monitor',
                action=self.on_monitor,
                default=True
            ),
            pystray.MenuItem(
                'Relay Control...',
                action=self.on_control
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                'Options...',
                action=self.on_options
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                'Stop!',
                action=self.on_quit
            )
        )

        self.tray.visible = True

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

                # launch the AutoUpdater
                if self.check_update() is False:

                    # If True, we've already launched an AutoUpdate!

                    self.cron.start()

                    # run the Tray icon
                    # !! This is a blocking call !!
                    self.tray.run(self.run_loop)

                    # the block may be released by self.on_quit, issued by an operator via the Tray
                    # ... or by a system command (like SIGTERM).

        except Timeout:
            MBox("It seems like another instance of The Onion Pack is already running. Aborting launch procedure...",
                 style=0x10)

        finally:
            self.tray.visible = False
            self.lock.release()

        if running:

            # Stop the TOP app (in case not stopped already in do_quit)
            self.app.stop()

            # Stop theonionbox
            self.box.stop()

            # Tor has OwningControllerProcess defined ... thus will terminate as soon as we're done.

            if self.status:

                reason = ['instance of TheOnionBox', 'App server']

                MBox(f"Our {reason[self.status - 1]} terminated.\r\nThus we have to terminate as well! Sorry...",
                     style=0x10)

        if self.cron.running:
            self.cron.shutdown()
        # self.reg.Close()
        sys.exit(0)

    def run_loop(self, icon: pystray.Icon):

        icon.visible = True

        # Monitor to check, if TOB still runs
        # ... and to collect the messages of the relay monitored.
        def _run_monitor():
            # quit if TheOnionBox died!

            if not self.stop.is_set():
                if self.box.poll() is not None:

                    # indicate that the Box terminated!
                    self.status = 1
                    self.do_quit()
                    return

                self.relay.collect_messages()

        self.cron.add_job(_run_monitor, 'interval', seconds=2)

        try:
            self.app.run()
        except:
            # if the app terminates ... we are going to terminate as well!
            self.status = 2
            self.do_quit()

    # Autoupdate
    def check_update(self, mode: Optional[str] = None) -> int:

        if mode is None:
            mode = self.app.autoupdate

        if mode is None or mode == 'off':
            with contextlib.suppress(JobLookupError):
                self.cron.remove_job(job_id='updater')
            if self.update_status is None:
                self.update_status = 0
            return False

        self.update_stamp = datetime.datetime.fromtimestamp(time()).strftime('%Y-%m-%d %H:%M:%S')
        self.update_status = 3  # Checking: This triggers a spinner @ the client.

        if self.vm.update() is False:

            if mode == 'user':
                message = 'I failed to check for updates of The Onion Pack. Please retry later.'
                self.tray.notify(message)
            else:
                self.cron.add_job(self.check_update,
                                  'date',
                                  run_date=datetime.datetime.now() + datetime.timedelta(seconds=10),
                                  id='updater',
                                  replace_existing=True
                                  )

            self.update_status = -1     # Error
            return False

        update = []

        v = self.relay.version
        if v and self.vm.Tor.version and v < self.vm.Tor.version:
            update.append('the Tor Windows Expert Bundle')

        v = self.relay.obfs.version
        if v and self.vm.obfs.version and v < self.vm.obfs.version:
            update.append('obfs4proxy')

        v = self.box.version
        if v and self.vm.Box.version and v < self.vm.Box.version:
            update.append('The Onion Box')

        v = self.version
        if v and self.vm.Pack.version and v < self.vm.Pack.version:
            update.append('The Onion Pack')

        if len(update) > 0:

            # If this check was issued by a user, we only show a notification!
            run_mode = 'notify' if mode == 'user' else mode

            run = {
                'auto': " I'm going to download and run my latest installer now - to perform the update.",
                'notify': ' Please run my installer to update.'
            }

            if len(update) > 1:
                m = update.pop()
                message = f'There are updates available for {", ".join(update)} and {m}.'
            else:
                message = f'There is an update available for {update[0]}.'

            if (256 - len(run[run_mode])) < len(message):
                message = "There are several updates available."

            message += run[run_mode]
            self.tray.notify(message)
            self.update_status = 2      # Update found

            if mode == 'auto':
                if self.get_latest_pack():
                    sleep(2)
                    self.do_quit()
                    return True

        else:

            message = "No updates available!" if mode == 'user' else ''    # remove any message!
            self.tray.notify(message)
            self.update_status = 1      # checked, no update

        if mode != 'user':
            self.cron.add_job(self.check_update,
                              'date',
                              run_date=datetime.datetime.now() + datetime.timedelta(minutes=random.randrange(30, 60)),
                              id='updater',
                              replace_existing=True
                              )

        return self.update_status

    # Tray menu actions
    def on_monitor(self, icon, item):
pr        webbrowser.open_new_tab('http://127.0.0.1:8080/')

    def on_control(self, icon, item):
        port = self.app.port
        webbrowser.open_new_tab(f'http://127.0.0.1:{port}/control')

    def on_options(self, icon, item):
        port = self.app.port
        webbrowser.open_new_tab(f'http://127.0.0.1:{port}/options')

    def on_quit(self, icon, item):
        self.do_quit()

    def do_quit(self):

        # indicate that the stop procedure has been launched
        self.stop.set()

        # Stop the app
        # -> This is mandatory prerequisite to stop the tray!!
        self.app.stop()

        # Stop the Tray
        self.tray.stop()

        # cleanup is being performed in self.run()

    @property
    def version(self):
        cwd = pathlib.Path(__file__).resolve()
        cwd = cwd.parent.parent
        assert cwd.exists()

        config = configparser.ConfigParser()
        config.read(str(cwd / 'setup.ini'))
        v = config.get(section='theonionpack', option='version', fallback=None)
        if v is not None:
            v = v.split('.')
            if len(v) < 3:
                v.append('0')
            return [int(y) for y in v]

        return None

    def get_latest_pack(self):

        url = self.get_updater_url()

        if url is not None:

            file = tempfile.NamedTemporaryFile(suffix='.exe', delete=False)

            r = requests.get(url, stream=True)
            for chunk in r.iter_content(chunk_size=512):
                if chunk:  # filter out keep-alive new chunks
                    file.write(chunk)

            file.close()

            params = [file.name]
            params.append('/SILENT')
            # params.append('/VERYSILENT')
            params.append('/LOG')
            params.append('/SUPPRESSMSGBOXES')
            params.append('/TASKS="startup,obfs4proxy"')
            subprocess.Popen(params, close_fds=True, creationflags=subprocess.DETACHED_PROCESS + subprocess.CREATE_NEW_PROCESS_GROUP)
            return True

        return False

    @staticmethod
    def get_updater_url() -> Optional[str]:

        headers = {'accept-encoding': 'gzip'}
        address = '//api.github.com/repos/ralphwetzel/theonionpack/releases/latest'

        r = None
        try:
            r = requests.get('https:' + address, headers=headers, timeout=10)
        except SSLError:
            with contextlib.suppress(Exception):
                r = requests.get('http:' + address, headers=headers, timeout=10)
        except:
            pass

        if r is None or r.status_code != requests.codes.ok:
            return None

        json = r.json()
        assets = json.get('assets', None)

        url = None
        for a in assets:
            name = a.get('name', None)
            if name == 'TheOnionPack.exe':
                url = a.get('browser_download_url', None)
                if url is not None:
                    break

        return url
