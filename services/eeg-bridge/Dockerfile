FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bluez \
        dbus \
        libdbus-1-3 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY tools/eeg-tools/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY tools/eeg-tools /app/tools/eeg-tools

ENV PYTHONPATH=/app/tools/eeg-tools/bridge-runtime
WORKDIR /app/tools/eeg-tools/bridge-runtime

CMD ["python", "-m", "app.main"]
