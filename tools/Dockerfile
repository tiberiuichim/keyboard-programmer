FROM python:3.12-slim
RUN apt-get update -qq \
 && apt-get install -y -qq --no-install-recommends libusb-1.0-0 usbutils \
 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir pyusb
