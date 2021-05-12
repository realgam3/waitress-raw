import sys
import json
import waitress
from threading import Thread
from waitress.channel import HTTPChannel
from waitress.utilities import BadRequest
from waitress.task import WSGITask, ErrorTask
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

__version__ = "0.1"


def parse_environment(environ):
    response_json = {
        "protocol": environ["SERVER_PROTOCOL"],
        "method": environ["REQUEST_METHOD"],
        "path": environ["PATH_INFO"],
        "query_string": environ["QUERY_STRING"],
        "headers": {
            key.replace("HTTP_", "", 1).replace("_", "-").title(): value for key, value in
            filter(lambda kv: kv[0].startswith("HTTP_"), environ.items())
        },
        "body": environ["wsgi.input"].read().decode("utf-8"),
        "request": environ["RAW_REQUEST"].decode("utf-8")
    }
    if "CONTENT_LENGTH" in environ:
        response_json["headers"]["Content-Length"] = environ["CONTENT_LENGTH"]
    if "CONTENT_TYPE" in environ:
        response_json["headers"]["Content-Type"] = environ["CONTENT_TYPE"]

    if "ERROR" in environ:
        response_json["error"] = environ["ERROR"]

    return response_json


def maintenance(self, now):
    cutoff = now - self.adj.channel_timeout
    for channel in self.active_channels.values():
        if (not channel.requests) and channel.last_activity < cutoff:
            if getattr(self.adj, "reset_on_timeout", False):
                channel.will_close = True
            elif channel.request:
                channel.request.error = BadRequest("Request Timed Out")
                error_task = RawErrorTask(channel, channel.request)
                error_task.execute()


class RawWSGITask(WSGITask):
    def get_environment(self):
        environ = super(RawWSGITask, self).get_environment()
        environ["RAW_REQUEST"] = bytes(self.channel.data)
        return environ


class RawErrorTask(ErrorTask):
    def __init__(self, channel, request):
        super(RawErrorTask, self).__init__(channel, request)
        self.environ = None

    def get_environment(self):
        environ = self.environ
        if environ is not None:
            return environ

        if not hasattr(self.request, "path"):
            self.request.path = ""

        if not hasattr(self.request, "command"):
            self.request.command = ""

        if not hasattr(self.request, "query"):
            self.request.query = ""

        if not hasattr(self.request, "url_scheme"):
            self.request.url_scheme = ""

        environ = RawWSGITask(self.channel, self.request).get_environment()
        self.environ = environ
        return environ

    def execute(self):
        environ = self.get_environment()
        environ["RAW_REQUEST"] = bytes(self.channel.data)

        e = self.request.error
        status, headers, environ["ERROR"] = e.to_response()

        body = json.dumps(parse_environment(environ), indent=2).encode("utf-8")
        headers = dict(headers)
        headers.update({
            "Content-Type": "application/json"
        })

        self.status = status
        self.response_headers.extend(headers.items())
        self.response_headers.append(("Connection", "close"))
        self.close_on_finish = True
        self.content_length = len(body)
        self.write(body)


class RawHTTPChannel(HTTPChannel):
    task_class = RawWSGITask
    error_task_class = RawErrorTask

    def __init__(self, server, sock, addr, adj, map=None):
        super(RawHTTPChannel, self).__init__(server, sock, addr, adj, map=map)
        self.data = b""

    def received(self, data):
        self.data = data
        res = super(RawHTTPChannel, self).received(data)
        return res


class RawHTTPEchoServer(Thread):
    def __init__(self, host="127.0.0.1", port=8000, scheme="http", channel_timeout=5, reset_on_timeout=False, **kwargs):
        super(RawHTTPEchoServer, self).__init__(**kwargs)
        self.server = waitress.create_server(
            application=self.request_handler,
            host=host, port=port, url_scheme=scheme,
            channel_timeout=channel_timeout
        )
        self.server.channel_class = RawHTTPChannel
        self.server.__class__.maintenance = maintenance
        self.server.adj.reset_on_timeout = reset_on_timeout

    @staticmethod
    def request_handler(environ, start_response):
        status_text = "200 OK"
        response_headers = {
            "Content-Type": "application/json"
        }.items()

        body_bytes = json.dumps(parse_environment(environ), indent=2).encode("utf-8")
        start_response(status_text, response_headers)
        return [body_bytes]

    def run(self):
        self.server.run()

    def stop(self):
        self.server.close()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


def main(args=None):
    if args is None:
        args = sys.argv[1:]

    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument("-v", "--version", action="version", version="%(prog)s {ver}".format(ver=__version__))

    # Proxy Configuration
    parser.add_argument("-lh", "--host",
                        help="listen host.",
                        default="0.0.0.0")
    parser.add_argument("-lp", "--port",
                        help="listen port",
                        type=int,
                        default=8000)
    parser.add_argument("-s", "--scheme",
                        help="url scheme",
                        default="http")
    parser.add_argument("-t", "--timeout",
                        help="timeout in seconds",
                        dest="channel_timeout",
                        type=int,
                        default=5)
    parser.add_argument("-r", "--reset-on-timeout",
                        help="reset on timeout",
                        action="store_true")

    sys_args = vars(parser.parse_args(args=args))
    server = RawHTTPEchoServer(**sys_args)
    server.run()
