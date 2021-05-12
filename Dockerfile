FROM python:3.9-alpine

# Create app directory
RUN mkdir -p /app
WORKDIR /app

# Bundle app source
COPY . /app

RUN pip install -r requirements.txt

# Set non root user
RUN adduser -D -h /home/user -s /bin/bash user
RUN chown -R user:user /home/user
RUN chmod -R 755 .

USER user
ENV HOME /home/user

EXPOSE 5000
CMD [ "python", "-m", "waitress_raw" ]
