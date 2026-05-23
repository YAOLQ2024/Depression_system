# LAN HTTPS Certificates

这个目录只用于存放局域网 HTTPS 测试用证书，不提交真实证书文件。

默认约定文件名：

- `lan-cert.pem`
- `lan-key.pem`

建议使用 `mkcert` 生成，例如：

```powershell
mkcert -install
mkcert -cert-file infra/certs/lan-cert.pem -key-file infra/certs/lan-key.pem localhost 127.0.0.1 ::1 <当前部署机器局域网IP>
```
