import collections
import os
import pathlib
import subprocess
import threading
import typing
import uuid

from shelljob import proc

from .torhasher import hash_password

class Tor():

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

        self.path = find('tor.exe', tor)

        if self.path is None:
            raise FileNotFoundError("Could not find tor.exe.")

        self.geoIP = find('geoip', tor)
        self.geoIP6 = find('geoip6', tor)
        # self.torrc_defaults = find('torrc-defaults', tor)
        self.data = data

        self._messages = collections.deque(maxlen=400)
        self.lock = threading.RLock()

    def run(self, owner_pid: int = os.getpid(), password: str = None, additional_command_line: typing.List[str] = None):

        if self.process is not None:
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
        self.process.run(params)

        return self.process

    def collect_messages(self):
        if self.process.is_pending():
            self.lock.acquire()
            lines = self.process.readlines(timeout=0.25)
            for proc, line in lines:
                l = line.decode('utf-8').rstrip('\r\n')
                if len(l) > 0:
                    self._messages.append(l)
            self.lock.release()

    @property
    def messages(self):
        self.lock.acquire()
        retval = list(self._messages)
        self.lock.release()
        return retval

    @property
    def version(self):
        params = [str(self.path)]
        params.extend(['--version'])
        v = subprocess.check_output(params).decode('utf-8')
        return v
