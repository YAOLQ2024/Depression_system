# 局域网访问与设备授权

本机当前地址为 `192.168.50.41`。问诊入口：[https://192.168.50.41](https://192.168.50.41)；管理入口：[https://192.168.50.41:8443](https://192.168.50.41:8443)。设备须在能够访问该地址的局域网中，访客 Wi-Fi 的设备隔离可能阻止访问。

旧 HTTP 地址 `http://192.168.50.41:3000`、`http://192.168.50.41:3001` 分别跳转到上述 HTTPS 入口。前端 API、上传和事件流都经由当前 HTTPS 入口访问网关。

## 每台客户端首次安装证书

从 [公开 CA 下载入口](http://192.168.50.41/local-ca.crt) 下载 `mcs-jetson-local-ca.crt`。该文件是公开根证书；服务端私钥无需传给客户端。下载后的证书主题应为 `MCS Jetson Local CA`，证书 SHA-256 指纹为：

```text
D8:15:67:F6:15:8B:0D:70:9F:B0:BA:96:91:60:F0:C5:BF:60:C3:6C:65:55:55:E0:11:54:B7:75:39:DE:89:85
```

这是证书 DER 内容的指纹，不是 PEM 文件的 SHA-256。Linux/macOS 可用 `openssl x509 -in mcs-jetson-local-ca.crt -noout -fingerprint -sha256` 核对。下载入口也支持 HTTPS；首次安装前可通过 HTTP 获取公开证书，并核对本说明中的指纹。

### Windows / Chrome、Edge

双击证书，选择“安装证书”→“当前用户”→“将所有的证书都放入下列存储”→“受信任的根证书颁发机构”。完成后关闭并重新打开浏览器。

也可在下载目录运行以下命令，将证书加入当前用户的根证书存储：

```powershell
certutil -user -addstore Root .\mcs-jetson-local-ca.crt
```

命令参数参考 [Microsoft certutil 文档](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/certutil)。受组织策略管理的电脑可能需要管理员部署证书。

### Android

下载证书后，在系统设置中搜索“安装证书”或“CA 证书”，将文件安装为 **CA 证书**。常见入口为“安全和隐私”→“更多安全设置”→“加密与凭据”→“安装证书”；不同厂商菜单可能不同。完成后重启 Chrome，再打开问诊 HTTPS 地址。系统可能要求设备解锁密码。

Google 的[证书安装说明](https://support.google.com/pixelphone/answer/2844832?hl=zh-Hans)可用于定位凭据管理入口；其中 WLAN 证书示例用于无线网络认证，本系统需要安装的是网站 CA 证书。

### iPhone / iPad

使用 Safari 下载并安装证书描述文件，安装入口通常为“设置”→“通用”→“VPN 与设备管理”。然后进入“设置”→“通用”→“关于本机”→“证书信任设置”，开启对 `MCS Jetson Local CA` 的完全信任，再重新打开 Safari。

手动安装描述文件后还需开启 SSL 信任，参见 [Apple 官方说明](https://support.apple.com/zh-cn/102390)。

### macOS

在“钥匙串访问”中导入证书，打开该证书的“信任”设置，将 SSL 信任设为“始终信任”，关闭窗口并确认系统认证请求，然后重新打开浏览器。参见 [Apple 证书信任设置说明](https://support.apple.com/zh-cn/guide/keychain-access/kyca11871/mac)。

### Ubuntu / Chromium

安装系统信任：

```bash
sudo cp mcs-jetson-local-ca.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates
```

若 Chromium 仍提示证书不可信，在浏览器证书管理界面导入 CA，或使用 NSS 工具导入。Chromium 146 起默认数据库是 `~/.local/share/pki/nssdb`；已有 `~/.pki/nssdb` 时继续使用旧路径。以下示例适用于已存在的新路径数据库：

```bash
sudo apt install libnss3-tools
certutil -d sql:$HOME/.local/share/pki/nssdb -A -t 'C,,' \
  -n 'MCS Jetson Local CA' -i mcs-jetson-local-ca.crt
```

参见 [Chromium 官方证书管理说明](https://chromium.googlesource.com/chromium/src/+/master/docs/linux/cert_management.md)。本 Jetson 已安装系统信任及当前用户的 Chromium NSS 信任。其他 Linux 用户和使用独立证书库的浏览器需分别配置。

## 登录、摄像头与麦克风

安装信任后，打开 HTTPS 地址，应无证书警告。登录后从首页点击“开始问诊”，在准备页点击“立即授权”，允许摄像头和麦克风访问。设备就绪后再确认数据采集授权并开始问诊。

系统采集的是**当前访问设备**的摄像头和麦克风。手机访问时采集手机设备，电脑访问时采集电脑设备。浏览器网站权限及操作系统隐私权限都需允许；设备被其他应用占用时先释放设备再重试。仅点击证书警告中的“继续访问”不能替代正确安装信任。

媒体采集需要安全上下文，参见 [MDN getUserMedia](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia)。本次自动验收覆盖 Chromium；Safari、手机浏览器和各客户端的实体设备仍需在对应设备上完成一次准备页授权及问诊录制上传验收。

## 地址维护

当前服务器证书覆盖 `192.168.50.41`、`localhost`、`medai`、`127.0.0.1`、`::1`。建议在路由器中为 Jetson 保留当前 DHCP 地址。IP 变化时需要重新签发覆盖新 IP 的服务器证书、更新访问地址并重启 Caddy；使用现有 CA 签发时，客户端无需重新安装根证书。

本轮没有修改路由器配置。无需在路由器上配置公网端口转发。
