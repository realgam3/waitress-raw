# waitress-raw

[![PyPI version](https://img.shields.io/pypi/v/waitress-raw)](https://pypi.org/project/waitress-raw/)
[![Downloads](https://pepy.tech/badge/waitress-raw)](https://pepy.tech/project/waitress-raw)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/waitress-raw)  

Raw HTTP Echo Server For Security Researchers and HTTP Debug

![Logo](https://raw.githubusercontent.com/realgam3/waitress-raw/main/assets/img/waitress-raw-logo.png)

## Installation

### Prerequisites

* Python 3.7+.
* waitress (https://docs.pylonsproject.org/projects/waitress/en/latest/).

### From pip

```shell
pip3 install waitress-raw
```

### From Docker

```shell
docker pull realgam3/waitress-raw
```

### From Source

```shell
git clone https://github.com/realgam3/waitress-raw.git
cd waitress-raw

# Install python dependencies.
pip3 install -r requirements.txt

# Confirm that everything works
python3 waitress-raw.py --help
```

Bug reports on installation issues are welcome!

## Usage

### Basic Usage

 ```shell
 waitress-raw -lh 0.0.0.0 -lp 8000 -c ./examples/loggers/streamhandler.yml
 ```  

### Docker Usage

```shell
docker run -v "${PWD}/examples/loggers/streamhandler.yml:/usr/src/app/config.yml:ro" -p 8000:8000 --rm realgam3/waitress-raw
```

### Command Line Arguments

```shell
waitress-raw --help
```

```text
usage: waitress-raw [-h] [-v] [-lh HOST] [-lp PORT] [-s SCHEME] [-t CHANNEL_TIMEOUT] [-r] [-V] [-c CONFIG_PATH]

options:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit
  -lh HOST, --host HOST
                        listen host. (default: 0.0.0.0)
  -lp PORT, --port PORT
                        listen port (default: 8000)
  -s SCHEME, --scheme SCHEME
                        url scheme (default: http)
  -t CHANNEL_TIMEOUT, --timeout CHANNEL_TIMEOUT
                        timeout in seconds (default: 5)
  -r, --reset-on-timeout
                        reset on timeout (default: False)
  -V, --verbose         verbose (default: False)
  -c CONFIG_PATH, --config CONFIG_PATH
                        config path (default: config.yml)
```
