FROM golang:1.24-alpine AS builder
ENV CGO_ENABLED=0 GOMAXPROCS=2 GOPROXY=https://proxy.golang.org,direct
RUN go install -p 2 -trimpath github.com/minio/minio@RELEASE.2025-10-15T17-29-55Z \
    && cp /go/pkg/mod/github.com/minio/minio@*/LICENSE /tmp/MINIO-LICENSE

FROM python:3.11-slim
COPY --from=builder /go/bin/minio /usr/local/bin/minio
COPY --from=builder /tmp/MINIO-LICENSE /usr/share/doc/minio/LICENSE
EXPOSE 9000 9001
ENTRYPOINT ["/usr/local/bin/minio"]
CMD ["server", "/data", "--console-address", ":9001"]
