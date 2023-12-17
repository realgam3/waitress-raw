FROM python:3.12-alpine

ARG USERNAME=app
WORKDIR /usr/src/app

COPY requirements.txt .
RUN set -eux; \
    \
    pip install -r requirements.txt; \
    \
    adduser --disabled-password --no-create-home --gecos ${USERNAME} ${USERNAME}

COPY . .

USER ${USERNAME}
ENV HOME=/tmp

EXPOSE 5000
CMD [ "python", "-m", "waitress_raw" ]
