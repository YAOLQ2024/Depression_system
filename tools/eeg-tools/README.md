# EEG Tools

`tools/eeg-tools` 是 Windows 宿主机 EEG 工具的唯一正式入口。

它把下面两类能力收口到一个 CLI：

- `bridge`：真实蓝牙 EEG 设备 -> Redis Stream
- `replay raw|simulate`：录制文件回放或无设备模拟 -> Redis Stream

源码运行和单 EXE 打包都只保留这一套。

## 子命令

### `bridge`

打印配置：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_eeg_tools.ps1 -Command bridge -PrintConfig
```

启动真实 bridge：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_eeg_tools.ps1 -Command bridge
```

### `replay raw`

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_eeg_tools.ps1 `
  -Command replay `
  -Mode raw `
  -ReplayFile E:\DataSets\Projects\depression-system\tools\eeg-tools\data\records\sample.jsonl `
  -Speed 1.0
```

### `replay simulate`

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_eeg_tools.ps1 `
  -Command replay `
  -Mode simulate `
  -DurationSeconds 30 `
  -Speed 1.0
```

## 配置文件

统一入口不会把配置硬编码进 EXE。

源码运行时读取：

- 仓库根 `.env`
- `tools/eeg-tools/.env`

打包成 EXE 后，读取：

- EXE 同级目录 `.env`

## EXE 打包

### 通用 CLI EXE

安装打包依赖：

```powershell
pip install -r tools/eeg-tools/requirements-build.txt
```

执行打包脚本：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_eeg_tools_exe.ps1
```

默认输出：

- `tools/eeg-tools/dist/eeg-tools.exe`

EXE 运行示例：

```powershell
.\eeg-tools.exe bridge
.\eeg-tools.exe replay raw --file .\records\sample.jsonl --speed 8
.\eeg-tools.exe replay simulate --duration-seconds 30 --speed 1
```

### 单用途 bridge EXE

如果你只想快速启动真实 EEG 蓝牙桥接，可以单独打一个 `eeg-bridge.exe`。

安装打包依赖：

```powershell
pip install -r tools/eeg-tools/requirements-build.txt
```

执行打包脚本：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_eeg_bridge_exe.ps1
```

默认输出：

- 仓库根目录 `eeg-bridge.exe`

运行示例：

```powershell
.\eeg-bridge.exe
.\eeg-bridge.exe --print-config
```
