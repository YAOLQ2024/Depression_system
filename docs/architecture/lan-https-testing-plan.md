# 局域网 HTTPS 测试方案

## 目标

让当前部署机器在局域网内通过 HTTPS 提供统一入口，保证浏览器在访问问诊页面时能够正常申请：

- 摄像头
- 麦克风

## 方案结论

当前仓库采用：

- `docker-compose.dev.yml` 作为基础开发环境
- `docker-compose.lan-https.yml` 作为 HTTPS 反向代理覆盖层
- `Caddy` 作为统一 HTTPS 入口
- `mkcert` 作为本地开发证书生成工具

对外访问入口统一为：

- `https://localhost`
- `https://<当前部署机器局域网IP>`

其中：

- `/` 转发到 `consultation`
- `/api/v1` 转发到 `gateway-service`

## 为什么不能继续用 HTTP

`http://<局域网IP>:3000` 不是浏览器认可的安全上下文。

在这种访问方式下，浏览器很可能拒绝：

- `getUserMedia`
- 麦克风授权
- 摄像头授权

## 工程文件

本方案对应的正式工程文件如下：

- `infra/compose/docker-compose.lan-https.yml`
- `infra/caddy/Caddyfile`
- `infra/certs/README.md`
- `infra/certs/.gitignore`

前端适配文件：

- `apps/consultation/client/public/config.js`
- `apps/consultation/client/src/services/api/client.ts`

## 当前机器实施步骤

### 1. 安装并初始化 `mkcert`

```powershell
mkcert -install
```

### 2. 生成证书

把 `<当前部署机器局域网IP>` 替换成实际地址，例如 `10.101.10.121`：

```powershell
mkcert -cert-file infra/certs/lan-cert.pem -key-file infra/certs/lan-key.pem localhost 127.0.0.1 ::1 <当前部署机器局域网IP>
```

### 3. 启动 HTTPS 入口

```powershell
docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.lan-https.yml up -d --build consultation gateway-service caddy
```

如果当前机器还需要 GPU 版 `multimodal-service`，可继续叠加 GPU compose：

```powershell
docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.gpu.yml -f infra/compose/docker-compose.lan-https.yml up -d --build multimodal-service consultation-service consultation gateway-service caddy
```

## 同事拉代码后的使用方式

同事拉代码后，不会自动拥有你这台机器的证书。

每一台作为“当前部署机器”的设备，都需要各自执行：

1. `mkcert -install`
2. 按自己机器的局域网 IP 生成 `infra/certs/lan-cert.pem` 和 `infra/certs/lan-key.pem`
3. 使用 `docker-compose.dev.yml + docker-compose.lan-https.yml` 启动

## 多设备联调说明

如果其它测试设备要访问当前部署机器：

1. 打开 `https://<当前部署机器局域网IP>`
2. 如果浏览器仍提示证书不受信任，需要先在该设备上信任当前部署机器对应的本地 CA
3. 首次进入页面后，手动允许摄像头和麦克风权限

## 当前状态记录

本次方案已经在当前机器执行完成，当前机器实际局域网 IP 为 `10.101.10.121`。

已完成项：

- HTTPS 页面入口
- HTTPS 同源 `/api/v1`
- 适合局域网内多设备联调的浏览器媒体权限环境

本次已完成的真实操作：

1. `mkcert -install`
2. 生成 `infra/certs/lan-cert.pem` 与 `infra/certs/lan-key.pem`
3. 使用 `docker-compose.dev.yml + docker-compose.lan-https.yml` 启动 `consultation`、`gateway-service`、`caddy`
4. 本机校验通过：
   - `https://localhost/config.js`
   - `https://localhost/api/v1/system/bootstrap`
   - `https://10.101.10.121/config.js`
   - `https://10.101.10.121/api/v1/system/bootstrap`

补充说明：

- Windows 自带 `curl` 可能因为 `schannel` 的吊销检查报 `CRYPT_E_NO_REVOCATION_CHECK`
- 这不代表 HTTPS 站点不可用
- 本次校验已通过 `curl.exe --ssl-no-revoke` 完成
