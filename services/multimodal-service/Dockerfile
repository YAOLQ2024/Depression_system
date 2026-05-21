FROM python:3.11-slim@sha256:67e6a6053f28db54c173ad84a4bf88fdd4e338793dc09672e87ee38e3b1b378c

ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn
ARG APT_MIRROR=https://mirrors.tuna.tsinghua.edu.cn
ENV PIP_INDEX_URL=${PIP_INDEX_URL} \
    PIP_TRUSTED_HOST=${PIP_TRUSTED_HOST} \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=10 \
    LD_LIBRARY_PATH=/usr/local/lib/python3.11/site-packages/nvidia/cudnn/lib:/usr/local/lib/python3.11/site-packages/nvidia/cublas/lib:/usr/local/lib/python3.11/site-packages/nvidia/cuda_runtime/lib:/usr/local/lib/python3.11/site-packages/nvidia/cuda_nvrtc/lib:/usr/local/lib/python3.11/site-packages/nvidia/cuda_cupti/lib:/usr/local/lib/python3.11/site-packages/nvidia/cufft/lib:/usr/local/lib/python3.11/site-packages/nvidia/curand/lib:/usr/local/lib/python3.11/site-packages/nvidia/cusolver/lib:/usr/local/lib/python3.11/site-packages/nvidia/cusparse/lib:/usr/local/lib/python3.11/site-packages/nvidia/nccl/lib:/usr/local/lib/python3.11/site-packages/nvidia/nvtx/lib:/usr/local/lib/python3.11/site-packages/nvidia/nvjitlink/lib:${LD_LIBRARY_PATH}

WORKDIR /app
RUN set -eux; \
    if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i "s|http://deb.debian.org/debian|${APT_MIRROR}/debian|g; s|http://deb.debian.org/debian-security|${APT_MIRROR}/debian-security|g" /etc/apt/sources.list.d/debian.sources; \
    elif [ -f /etc/apt/sources.list ]; then \
        sed -i "s|http://deb.debian.org/debian|${APT_MIRROR}/debian|g; s|http://deb.debian.org/debian-security|${APT_MIRROR}/debian-security|g" /etc/apt/sources.list; \
    fi; \
    for attempt in 1 2 3 4 5; do \
        apt-get update \
        && apt-get install -y --no-install-recommends --fix-missing \
            libgl1 \
            libglib2.0-0 \
            libgomp1 \
            ffmpeg \
        && break; \
        if [ "$attempt" -eq 5 ]; then \
            exit 1; \
        fi; \
        rm -rf /var/lib/apt/lists/*; \
        sleep 5; \
    done; \
    rm -rf /var/lib/apt/lists/*
COPY requirements-heavy.txt requirements-app.txt requirements.txt ./
RUN pip install --no-cache-dir -r requirements-heavy.txt
RUN pip install --no-cache-dir -r requirements-app.txt
COPY alembic ./alembic
COPY app ./app
COPY runtime-assets ./runtime-assets
COPY scripts ./scripts
COPY tests ./tests
COPY alembic.ini pyproject.toml README.md seed.py .env.example ./
RUN sed -i 's/\r$//' scripts/start.sh && chmod +x scripts/start.sh
CMD ["./scripts/start.sh"]
