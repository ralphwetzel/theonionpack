#!/usr/bin/env python
import configparser
import contextlib
import ctypes
import datetime
import os
import pathlib
import random
import subprocess
import sys
import tempfile
from time import sleep, strftime, localtime
import threading
import uuid
import webbrowser
import winreg

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
if hWnd:
    user32.ShowWindow(hWnd, SW_HIDE)

filetime = os.path.getmtime(__file__)
__stamp__ = strftime('%Y%m%d|%H%M%S', localtime(filetime))


class Pack():

    def __init__(self, config):

        self.cron = BackgroundScheduler()

        self.config = config

        self.cwd = pathlib.WindowsPath(self.config['cwd'])

        self.status = 0

        # The AutoUpdate behaviour shall be persisted into the registry
        # Default behavior ... in case we encounter issues when accessing the registry!
        self.autoupdate = 'notify'
        # Our registry key: Set 'autoupdate' to 'notify' if it doesn't exist!
        with contextlib.suppress(OSError):
            self.reg = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, 'TheOnionPack', access=winreg.KEY_ALL_ACCESS)
            try:
                self.autoupdate = winreg.QueryValue(self.reg, 'autoupdate')
            except FileNotFoundError:
                winreg.SetValue(self.reg, 'autoupdate', winreg.REG_SZ, self.autoupdate)

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
                'Updates',
                pystray.Menu(
                    pystray.MenuItem(
                        'Show notification if update is available',
                        checked=self.on_get_autupdate('notify'),
                        radio=True,
                        action=self.on_set_autoupdate('notify')
                    ),
                    pystray.MenuItem(
                        'Perform auto update if update is available',
                        checked=self.on_get_autupdate('auto'),
                        radio=True,
                        action=self.on_set_autoupdate('auto')
                    )
                )
            ),
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
            self.lock.release()

        if running:

            # Stop theonionbox
            self.box.stop()

            # Tor has OwningControllerProcess defined ... thus will terminate as soon as we're done.

            if self.status == 1:
                MBox("Our instance of TheOnionBox terminated.\r\nThus we have to terminate as well! Sorry...",
                     style=0x10)

        self.cron.shutdown()
        self.reg.Close()
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

    # Autoupdate
    def check_update(self):

        vm = VersionManager('127.0.0.1:9050', __stamp__)
        if vm.update() is False:
            self.cron.add_job(self.check_update,
                              'date',
                              run_date=datetime.datetime.now() + datetime.timedelta(seconds=10)
                              )
            return False

        update = []

        v = self.relay.version
        if v and vm.Tor.version and v < vm.Tor.version:
            update.append('the Tor Windows Expert Bundle')

        v = self.relay.obfs.version
        if v and vm.obfs.version and v < vm.obfs.version:
            update.append('obfs4proxy')

        v = self.box.version
        if v and vm.Box.latest_version and v < vm.Box.version:
            update.append('The Onion Box')

        v = self.version
        if v and vm.Pack.version and v < vm.Pack.version:
            update.append('The Onion Pack')

        if len(update) > 0:

            run = {
                'auto': " I'm going to download and run my latest installer now - to perform the update.",
                'notify': ' Please run my installer to update.'
            }

            if len(update) > 1:
                m = update.pop()
                message = f'There are updates available for {", ".join(update)} and {m}.'
            else:
                message = f'There is an update available for {update[0]}.'

            if (256 - len(run[self.autoupdate])) < len(message):
                message = "There are several updates available."
            message += run[self.autoupdate]
            self.tray.notify(message)

            if self.autoupdate == 'auto':
                if self.get_latest_pack():
                    sleep(2)
                    self.do_quit()
                    return True

        else:
            self.tray.notify()  # remove any message!

        self.cron.add_job(self.check_update,
                          'date',
                          run_date=datetime.datetime.now() + datetime.timedelta(minutes=random.randrange(30, 60))
                          )

        return False

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

    def on_get_autupdate(self, status):
        def get_autoupdate(item):
            try:
                v = winreg.QueryValue(self.reg, 'autoupdate')
            except:
                return self.autoupdate == status
            return v == status
        return get_autoupdate

    def on_set_autoupdate(self, status):
        def set_autoupdate(item):
            with contextlib.suppress(Exception):
                winreg.SetValue(self.reg, 'autoupdate', winreg.REG_SZ, status)
            self.autoupdate = status
        return set_autoupdate

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

        if r is None:
            return False

        if r.status_code == requests.codes.ok:
            json = r.json()
            assets = json.get('assets', None)

            url = None
            for a in assets:
                name = a.get('name', None)
                if name == 'TheOnionPack.exe':
                    url = a.get('browser_download_url', None)
                    if url is not None:
                        break

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
