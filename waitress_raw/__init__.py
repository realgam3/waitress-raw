import sys
import yaml
import json
import logging
import waitress
import importlib
from io import BytesIO
from pathlib import Path
from copy import deepcopy
from threading import Thread
from waitress.channel import HTTPChannel
from waitress.utilities import BadRequest
from waitress.task import WSGITask, ErrorTask
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

from .__version__ import __version__

logger = logging.getLogger(__name__)


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
        "body": environ["wsgi.input"],
        "request": environ["RAW_REQUEST"]
    }
    if "CONTENT_LENGTH" in environ:
        response_json["headers"]["Content-Length"] = environ["CONTENT_LENGTH"]
    if "CONTENT_TYPE" in environ:
        response_json["headers"]["Content-Type"] = environ["CONTENT_TYPE"]

    if "ERROR" in environ:
        response_json["error"] = environ["ERROR"]

    try:
        to_log = deepcopy(response_json)
        headers = to_log.pop("headers") or {}
        for key, value in headers.items():
            header_name = key.lower()
            if header_name not in ["x-request-id", "x-test", "x-gotestwaf-test", "x-debug-id"]:
                continue
            to_log[header_name] = value

        body = to_log.pop("body") or BytesIO()
        index = body.tell()
        value = body.read()
        body.seek(index)

        to_log["headers"] = json.dumps(headers)
        to_log["body"] = repr(value)
        to_log["request"] = repr(to_log.pop("request") or "")
        logger.info("request", extra=to_log)
    except Exception as e:
        logger.exception(f"Failed to log request: {e}")

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
        if hasattr(self.channel, "data"):
            self.channel.data = b""
        return environ


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (bytes, bytearray)):
            return obj.decode("utf-8", errors="backslashreplace")
        elif hasattr(obj, "tell") and hasattr(obj, "read") and hasattr(obj, "seek"):
            index = obj.tell()
            value = obj.read()
            obj.seek(index)
            return self.default(value)
        return super().default(obj)


class RawErrorTask(ErrorTask):
    def __init__(self, channel, request):
        super(RawErrorTask, self).__init__(channel, request)
        self.environ = None

    def get_environment(self):
        environ = self.environ
        if environ is not None:
            return environ

        self.request.path = getattr(self.request, "path", "")
        self.request.command = getattr(self.request, "command", "")
        self.request.query = getattr(self.request, "query", "")
        self.request.url_scheme = getattr(self.request, "url_scheme", "")
        self.request.request_uri = getattr(self.request, "request_uri", "")

        environ = RawWSGITask(self.channel, self.request).get_environment()
        self.environ = environ
        return environ

    def execute(self):
        environ = self.get_environment()
        environ["RAW_REQUEST"] = bytes(self.channel.data)

        error = self.request.error
        status, headers, environ["ERROR"] = error.to_response()

        body = json.dumps(parse_environment(environ), cls=JSONEncoder, indent=2).encode(
            "utf-8", errors="backslashreplace"
        )
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
        self.data += data
        res = super(RawHTTPChannel, self).received(data)
        return res


class RawHTTPEchoServer(Thread):
    def __init__(self, host="127.0.0.1", port=8000, scheme="http",
                 channel_timeout=5, reset_on_timeout=False, config=None):
        config = config or {}
        thread_config = config.get("thread", {})
        super().__init__(**thread_config)
        waitress_config = config.get("waitress", {})
        self.server = waitress.create_server(
            application=self.request_handler,
            host=host, port=port, url_scheme=scheme,
            channel_timeout=channel_timeout,
            **waitress_config,
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

        body_bytes = json.dumps(parse_environment(environ), cls=JSONEncoder, indent=2).encode(
            "utf-8", errors="backslashreplace"
        )
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


def configure_logging_handlers(loggers):
    for handler_config in loggers:
        module_name, class_name = handler_config["handler"].rsplit(".", 1)
        try:
            module = importlib.import_module(module_name, module_name)
            handler_class = getattr(module, class_name, None)
            if not issubclass(handler_class, logging.Handler):
                return ValueError()
        except Exception:
            raise NotImplementedError("Could not load logging handler")

        args = handler_config.get("args", {})
        handler = handler_class(**args)

        fmt = handler_config.get("format")
        if fmt:
            formatter = logging.Formatter(
                fmt=fmt,
            )
            handler.setFormatter(fmt=formatter)

        logger.addHandler(handler)


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
    parser.add_argument("-V", "--verbose",
                        help="verbose",
                        action="store_true")
    parser.add_argument("-c", "--config",
                        help="config path",
                        dest="config_path",
                        default="config.yml")
    sys_args = vars(parser.parse_args(args=args))

    config = {}
    config_path = Path(sys_args.pop("config_path"))
    if config_path.exists():
        config = yaml.safe_load(config_path.read_text())
    sys_args["config"] = config

    verbose = sys_args.pop("verbose", False)
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    loggers_config = config.get("logging", [])
    configure_logging_handlers(loggers_config)

    server = RawHTTPEchoServer(**sys_args)
    server.run()
