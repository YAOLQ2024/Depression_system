FROM node:22.22.0-alpine AS consultation-client-builder

ENV NODE_OPTIONS="--dns-result-order=ipv4first"

WORKDIR /app/client

RUN npm config set registry https://registry.npmmirror.com/

COPY client/package.json ./package.json
COPY client/tsconfig.json ./tsconfig.json
COPY client/tsconfig.node.json ./tsconfig.node.json
COPY client/vite.config.ts ./vite.config.ts
RUN npm install

COPY client/public ./public
COPY client/index.html ./index.html
COPY client/src ./src

RUN npm run build

FROM python:3.11-slim

ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn
ENV PIP_INDEX_URL=${PIP_INDEX_URL} \
    PIP_TRUSTED_HOST=${PIP_TRUSTED_HOST} \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=10

WORKDIR /app
COPY server/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY server ./server
COPY --from=consultation-client-builder /app/client/dist ./client/dist
WORKDIR /app/server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
