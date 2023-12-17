FROM python:3.12-slim

ARG USERNAME=app
WORKDIR /usr/src/app

COPY requirements.txt .
RUN set -eux; \
    \
    pip install -r requirements.txt; \
    \
    adduser --disabled-password --no-create-home --gecos ${USERNAME} ${USERNAME}; \
    chown -R ${USERNAME}:${USERNAME} /usr/src/app

COPY . .

USER ${USERNAME}
ENV HOME=/tmp

EXPOSE 8000
CMD [ "python", "waitress-raw.py", "-lh", "0.0.0.0", "-lp", "8000", "-t", "15" ]
