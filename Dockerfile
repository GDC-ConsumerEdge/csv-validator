FROM --platform=linux/amd64 python:3.12-alpine

ADD . /app
WORKDIR /app
RUN pip3 install -r requirements-setuptools.txt --require-hashes --no-cache-dir && \
    pip3 install -r requirements.txt --require-hashes --no-cache-dir && \
    pip3 install --no-deps --no-index --no-build-isolation .

ENTRYPOINT [ "validate_csv" ]
