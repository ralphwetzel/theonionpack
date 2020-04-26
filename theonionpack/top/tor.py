import collections
import contextlib
import os
import pathlib
import re
import signal
import subprocess
import threading
import time
import typing
import uuid

from shelljob import proc

from .torhasher import hash_password


class obfs4Proxy:
    def __init__(self, path):
        self.path = path

    @property
    def version(self) -> typing.Optional[typing.List[int]]:
        if self.path is None:
            return None

        params = [str(self.path)]
        params.extend(['--version'])
        with contextlib.suppress(Exception):
            v = subprocess.check_output(params).decode('utf-8')
            v = re.findall('(?:obfs4proxy-)((?:\d+\.?){3})', v)
            if len(v) > 0:
                v = v[0].split('.')
                return [int(y) for y in v]

        return None


class Tor:

    def __init__(self, tor: str = '.\Tor', data: str = '.\Data'):

        def find(filename: str, start_at: str = '.') -> typing.Optional[str]:
            found = None
            p = pathlib.Path(start_at).resolve()
            for root, dirs, files in os.walk(str(p)):
                if filename in files:
                    found = os.path.join(root, filename)
                    break

            return found

        self.process = None
        self.owner = None
        self.tor = None

        self.path = find('tor.exe', tor)

        if self.path is None:
            raise FileNotFoundError("Could not find tor.exe.")

        self.geoIP = find('geoip', tor)
        self.geoIP6 = find('geoip6', tor)
        # self.torrc_defaults = find('torrc-defaults', tor)
        self.data = data

        self._messages = collections.deque(maxlen=400)
        self.lock = threading.RLock()

        self.obfs = obfs4Proxy(find('obfs4proxy.exe', tor))

        self.last_modified = 0

    def run(self, owner_pid: int = os.getpid(), password: str = None, additional_command_line: typing.List[str] = None):

        if self.running:
            raise OSError('Already running...')

        if self.path is None:
            return False

        # pwd = uuid.uuid4().hex
        self.password = hash_password(password) if password is not None else None
        # print(self.password)
        # check = subprocess.run([str(self.path), '--hash-password', pwd], stdout=subprocess.PIPE)
        # print(check.stdout.decode('utf-8'))
        # print(check.stdout)

        # return

        self.owner = owner_pid
        params = [str(self.path)]

        if self.owner > 0:
            params.extend(['__OwningControllerProcess', str(owner_pid)])

        if self.geoIP:
            params.extend(['GeoIPFile', self.geoIP])
        if self.geoIP6:
            params.extend(['GeoIPv6File', self.geoIP6])

        params.extend(['+__ControlPort', '9051'])
        params.extend(['+__SocksPort', '9050'])

        if self.password is not None:
            params.extend(['__HashedControlSessionPassword', self.password])

        params.extend(['DataDirectory', self.data])

        params.extend(['-f', str((pathlib.Path(self.data) / 'torrc/torrc').resolve())])
        params.extend(['--defaults-torrc', str((pathlib.Path(self.data) / 'torrc/torrc-defaults').resolve())])
        params.extend(['--ignore-missing-torrc'])

        # params = [str(self.path)]

        # params.extend(['--hash-password', 'test'])

        # params.extend(['| more'])

        # print(subprocess.list2cmdline(params))
        # self.process = subprocess.Popen(params, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        if additional_command_line is not None:
            params.extend(additional_command_line)

        # self.process = subprocess.Popen(params, stderr=subprocess.PIPE)
        # print(self.process)

        self.process = proc.Group()
        self.tor = self.process.run(params)

        return self.tor

    def collect_messages(self):
        if self.process and self.process.is_pending():
            self.lock.acquire()
            lines = self.process.readlines(timeout=0.25)
            if len(lines) > 0:
                self.last_modified = time.time()
                for proc, line in lines:
                    l = line.decode('utf-8').rstrip('\r\n')
                    if len(l) > 0:
                        self._messages.append([self.last_modified, l])
            self.lock.release()

    @property
    def messages(self):
        return self.get_messages()

    def get_messages(self, since: float = 0.0, until: typing.Optional[float] = None) -> typing.List[str]:

        self.lock.acquire()
        if until is None:
            until = self.last_modified

        retval = [m[1] for m in reversed(self._messages) if since < m[0] <= until]
        self.lock.release()

        retval.reverse()
        return retval

    @property
    def version(self) -> typing.Optional[typing.List[int]]:
        params = [str(self.path)]
        params.extend(['--version'])

        with contextlib.suppress(Exception):
            v = subprocess.check_output(params).decode('utf-8')
            v = re.findall('(?:Tor version )((?:\d+\.?){4})', v)
            if len(v) > 0:
                v = v[0].split('.')
                return [int(y) for y in v]

        return None

    def stop(self):
        # if the subprocess is still running...
        if self.running:
            # ... terminate it.
            pid = self.tor.pid
            os.kill(pid, signal.SIGINT)
            self.tor.wait()
            self.tor = None

        self.process = None

    def poll(self):
        return self.tor.poll()

    @property
    def running(self):
        if self.tor is None:
            return False

        return self.tor.poll() is None
