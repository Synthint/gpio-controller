FROM arm64v8/ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-lgpio

RUN python3 -m pip install gpiod --break-system-packages