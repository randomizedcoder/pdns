import http.client
import os
import socket
import stat
import time

from recursortests import RecursorTest


class UnixHTTPConnection(http.client.HTTPConnection):
    def __init__(self, path, timeout):
        super().__init__("localhost", timeout=timeout)
        self._path = path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self._path)


class APIUnixSocketRecursorTest(RecursorTest):
    _confdir = "APIUnixSocketRecursor"
    _wsSocket = os.path.abspath(os.path.join("configs", _confdir, "web.sock"))
    _wsTimeout = 2
    _wsPassword = "secretpassword"
    _apiKey = "secretapikey"

    # allow-from would deny a TCP client, it does not apply to a UNIX domain socket
    _config_template = """
webserver=yes
webserver-address=%s
webserver-password=%s
webserver-allow-from=192.0.2.1
api-key=%s
""" % (_wsSocket, _wsPassword, _apiKey)

    def waitForUnixSocket(self):
        for try_number in range(0, 1000):
            try:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(1.0)
                sock.connect(self._wsSocket)
                sock.close()
                return
            except Exception:
                pass
            time.sleep(0.01)
        raise AssertionError("no webserver on %s" % self._wsSocket)

    def testAPI(self):
        self.waitForUnixSocket()
        conn = UnixHTTPConnection(self._wsSocket, self._wsTimeout)
        conn.request("GET", "/api/v1/servers/localhost/statistics", headers={"x-api-key": self._apiKey})
        r = conn.getresponse()
        self.assertEqual(r.status, 200)
        self.assertTrue(r.read())

    def testAPIWithoutKey(self):
        self.waitForUnixSocket()
        conn = UnixHTTPConnection(self._wsSocket, self._wsTimeout)
        conn.request("GET", "/api/v1/servers/localhost/statistics")
        r = conn.getresponse()
        self.assertEqual(r.status, 401)

    def testSocketMode(self):
        self.waitForUnixSocket()
        st = os.stat(self._wsSocket)
        self.assertTrue(stat.S_ISSOCK(st.st_mode))
        self.assertEqual(stat.S_IMODE(st.st_mode), 0o660)
