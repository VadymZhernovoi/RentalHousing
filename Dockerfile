FROM ubuntu:latest
LABEL authors="vadymzhernovoi"

ENTRYPOINT ["top", "-b"]