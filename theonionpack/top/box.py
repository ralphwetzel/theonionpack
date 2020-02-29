import contextlib
import importlib
import os
import pathlib
import re
import signal
import sys
import subprocess

from .util import MBox


class TheOnionBox():

    def __init__(self, config):

        self.config = config

        tob = importlib.util.find_spec('theonionbox')
        if tob is None:
            MBox("Error: Failed to locate Python package 'theonionbox'.", style=0x10)
            sys.exit(0)

        self.name = tob.name

        self.tob = None
        self.password = None

    def run(self, password: str = None):

        params = [sys.executable, '-m', self.name]

        if self.config['trace']:
            params.extend(['--trace'])
        elif self.config['debug']:
            params.extend(['--debug'])

        params.extend(['box', '--host', '127.0.0.1'])
        if password is not None:
            params.extend(['tor', '--password', password])
            self.password = password

        if self.config['trace'] or self.config['debug']:
            self.tob = subprocess.Popen(params, creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            self.tob = subprocess.Popen(params)

        return self.tob

    def stop(self):
        # if the subprocess is still running...
        if self.poll() is None:
            # ... terminate it.
            pid = self.tob.pid
            os.kill(pid, signal.SIGINT)
            self.tob.wait()

    def poll(self):
        return self.tob.poll()

    @property
    def version(self):
        params = [sys.executable, '-m', self.name]
        params.extend(['--version'])
        with contextlib.suppress(Exception):
            v = subprocess.check_output(params).decode('utf-8')
            v = re.findall('(?:Version )((?:\d+\.?){2,3})(?: \()', v)
            if len(v) > 0:
                v = v[0].split('.')
                while len(v) < 3:
                    v.append('0')
                return [int(y) for y in v]

        return None
