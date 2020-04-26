import contextlib
import json
import pathlib
import socket
import subprocess
import time
import winreg

import bottle

import theonionbox.tob.libraries.latolatin as latolatin_tob
from .libraries import LatoLatin
from .simplecontroller import SimplePort
from .tor import Tor

class App:

    def __init__(self, pack):

        self.pack = pack

        self.app = bottle.Bottle()
        self.server = None
        self.port = None
        self.cwd = pack.cwd
        self.torrc = pack.torrc
        self.password = pack.password
        self.nickname = ''
        self.tor = pack.relay

        self.app.route('/',
                       method='GET',
                       callback=self.get_index)

        self.app.route('/control',
                       method='GET',
                       callback=self.get_control)

        self.app.route('/options',
                       method='GET',
                       callback=self.get_options)

        self.app.route('/data',
                       method='POST',
                       callback=self.post_data)

        self.app.route('/logo.ico',
                       method='GET',
                       callback=self.get_icon)

        self.app.route('/favicon.ico',
                       method='GET',
                       callback=self.get_icon)

        self.app.route('/action',
                       method='POST',
                       callback=self.post_action)

        # pull the LatoFont from The Onion Box!
        latoLibPath = pathlib.WindowsPath(latolatin_tob.__file__).parent / '..' / '..' / 'libs/LatoLatin'
        latoLibPath = latoLibPath.resolve()

        if latoLibPath.exists():
            latoLib = LatoLatin(str(latoLibPath))
            self.app.merge(latoLib)

        import configparser

        config = configparser.ConfigParser()
        file = self.cwd / 'setup.ini'
        config.read(str(file))
        self.title = config['theonionpack']['title']
        self.version = config['theonionpack']['version']
        self.desc = config['theonionpack']['description']
        self.copy = config['theonionpack']['copyright']

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

        # the timestamp of the latest check for an update
        # self.update_stamp = None
        # the result of the latest check
        # self.update_status = None

    def get_index(self):
        return bottle.HTTPError(404)

    def get_control(self):

        self.get_nickname()

        try:
            with open(self.torrc, 'r') as f:
                config = f.read()
        except:
            config = ''

        params = {
            'version': self.version
            , 'title': self.title
            , 'copyright': self.copy
            , 'torrc': self.torrc
            , 'config': config
            , 'nickname': self.nickname
        }
        page = self.cwd / 'pages' / 'control.html'
        return bottle.template(str(page), **params)
        # return bottle.static_file('control.html', root=str(pages), mimetype='text/html')

    def get_options(self):

        # query the registry for the autoupdate setting
        try:
            v = winreg.QueryValue(self.reg, 'autoupdate')
        except:
             update = self.autoupdate
        else:
            update = v

        params = {
            'version': self.version
            , 'title': self.title
            , 'copyright': self.copy
            , 'update': update
            , 'pack': self.pack.version
            , 'box': self.pack.box.version
            , 'tor': self.pack.relay.version
            , 'obfs': self.pack.relay.obfs.version
            , 'stamp': self.pack.update_stamp
            , 'status': self.pack.update_status
        }
        page = self.cwd / 'pages' / 'options.html'
        return bottle.template(str(page), **params)

    def get_icon(self):
        icons = self.cwd / 'icons'
        return bottle.static_file('top16.ico', root=str(icons), mimetype='image/vnd.microsoft.icon')

    def post_data(self):

        r = bottle.request
        action = bottle.request.forms.get('action', None)

        retval = {}

        if action is None:
            raise bottle.HTTPError(405)

        if action in ['control']:

            # The timestamp sent by "If-Modified-Since" / "Last-Modified" headers is limited to 'seconds' precision.
            # This creates a condition where messages are sent twice.
            # Thus we're using an ETag & "If-None-Match" mechanism here ... operating with an epoch timestamp as ETag!
            ims = bottle.request.get_header('If-None-Match')
            ims = float(ims) if ims else 0

            # We get the last_mod info directly from the Tor message collection system
            last_modified = self.tor.last_modified
            messages = self.tor.get_messages(since=ims, until=last_modified)

            if messages is None or len(messages) < 1:
                return bottle.HTTPResponse(status=304)

            retval['messages'] = messages
            retval['nickname'] = self.nickname
            retval['running'] = self.tor.running

            headers = {
                'ETag': str(last_modified)
            }

            # set the headers
            for header, value in headers.items():
                bottle.response.set_header(header, value)

        if action in ['options']:
            retval = {
                'update': self.autoupdate
                , 'stamp': self.pack.update_stamp
                , 'status': self.pack.update_status
                , 'pack': [self.pack.version, self.pack.vm.Pack.version]
                , 'box': [self.pack.box.version, self.pack.vm.Box.version]
                , 'tor': [self.pack.relay.version, self.pack.vm.Tor.version]
                , 'obfs': [self.pack.relay.obfs.version, self.pack.vm.obfs.version]
            }

        return json.JSONEncoder().encode(retval)

    def run(self):

        #####
        # Our Web Server
        # This is a customization of the standard (v0.13) bottle.py CherootServer
        class CherootServer(bottle.ServerAdapter):
            def run(self, handler):  # pragma: no cover
                from cheroot import wsgi
                self.options['bind_addr'] = (self.host, self.port)
                self.options['wsgi_app'] = handler
                self.server = wsgi.Server(**self.options)
                self.server.start()

            def shutdown(self):
                if self.server is not None:
                    self.server.stop()

        def pick_port() -> str:
            s = socket.socket()
            s.bind(('', 0))
            port = s.getsockname()[1]
            s.close()
            return port

        self.port = pick_port()
        self.server = CherootServer(host='127.0.0.1', port=self.port)

        self.server.run(self.app)

    def stop(self):
        if self.server is not None:
            self.server.shutdown()

        self.reg.Close()

    def create_controller(self):

        controller = None
        with contextlib.suppress(Exception):
            controller = SimplePort('127.0.0.1', 9051)

        if not controller:
            raise bottle.HTTPError(500, exception='Failed to connect to the local Tor relay.')

        ok = None
        with contextlib.suppress(Exception):
            ok = controller.msg(f'AUTHENTICATE "{self.password}"').strip()

        if ok != '250 OK':
            controller.shutdown()
            raise bottle.HTTPError(500, exception='Failed to authenticate against local Tor relay.')

        return controller

    def reload_config(self):

        try:
            controller = self.create_controller()
        except bottle.HTTPError:
            raise

        ok = None
        with contextlib.suppress(Exception):
            ok = controller.msg("SIGNAL RELOAD").strip()

        if ok != '250 OK':
            controller.shutdown()
            raise bottle.HTTPError(500, exception='Failed to reload the Tor relay configuration.')

        # take the opportunity to re-catch the Nickname
        self.get_nickname(controller=controller)

        controller.shutdown()

    def get_nickname(self, controller=None):

        # create a controller, if none was provided!
        if controller is None:
            try:
                c = self.create_controller()
            except Exception as exc:
                print(exc)
                return
        else:
            c = controller

        ok = ''
        with contextlib.suppress(Exception):
            ok = c.msg("GETCONF NICKNAME").strip()

        # ok should be '250 NICKNAME = ...'
        if len(ok) > 3 and ok[:3] == '250':
            pos = ok.find('=')
            if pos > 3:
                self.nickname = ok[pos + 1:]

        # if we created the controller, we shall shut it down as well!
        if controller is None:
            c.shutdown()

        return

    def stop_tor(self, signal='SHUTDOWN'):

        try:
            controller = self.create_controller()
        except bottle.HTTPError:
            raise

        ok = None
        with contextlib.suppress(Exception):
            ok = controller.msg(f"SIGNAL {signal}").strip()

        if ok != '250 OK':
            controller.shutdown()
            raise bottle.HTTPError(500, exception=f'Failed to {signal} the Tor relay configuration.')

        controller.shutdown()

    def post_action(self):

        r = bottle.request

        action = bottle.request.forms.get('action', None)

        if action is None:
            raise bottle.HTTPError(405)

        if action in ['save', 'savereload']:

            config = bottle.request.forms.get('torrc', None)
            if not config:
                raise bottle.HTTPError(400, exception='Configuration to be written to torrc is missing.')

            try:
                with open(self.torrc, 'w') as f:
                    f.write(config)
            except:
                raise bottle.HTTPError(500, exception='Failed to write to torrc file.')

        if action in ['reload', 'savereload']:
            self.reload_config()

        if action in ['restart']:
            if self.tor.running:
                # Let's try to be nice ... initially!
                self.stop_tor()

                # 5 seconds to shutdown cleanly...
                counter = 0
                while self.tor.running and counter < 5:
                    time.sleep(1)
                    counter += 1

            if self.tor.running:
                # If Tor is still running ... be brutal!
                self.tor.stop()

            self.tor.run(password=self.password)

        if action in ['torrc']:
            p = pathlib.WindowsPath(self.torrc).parent
            subprocess.Popen(f'explorer "{p.resolve()}"')

        if action in ['update']:
            # write autoupdate mode to registry
            status = bottle.request.forms.get('status', 'off')

            with contextlib.suppress(Exception):
                winreg.SetValue(self.reg, 'autoupdate', winreg.REG_SZ, status)
            self.autoupdate = status
            self.pack.check_update()

        if action in ['check_update']:
            self.pack.check_update('user')

        if action in ['get_updater']:
            url = self.pack.get_updater_url()
            if url is None:
                raise bottle.HTTPError(404)
            return json.JSONEncoder().encode(url)

        return bottle.HTTPResponse(status=200)
