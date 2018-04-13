## 部署

### 安装 Python 环境

- 从 https://www.python.org/downloads/windows/ 下载 __64 位__ 最新稳定版本 Python 安装 (__版本 3.6.x 或更新__)

### 安装 AviSynth 及 VapourSynth 运行库

- AviSynth 安装文件位于 `bin\installer\AviSynth+r2294.exe` (__仅安装__ `AviSynth+ x64`)
- VapourSynth 安装文件位于 `bin\installer\VapourSynth-R43.exe` (__仅安装__ `VapourSynth 64-bit`)

### 安装需要的 PowerShell 模块

- 在 PowerShell 中使用 `Install-Module <Module_Name>` 命令安装需要的模块
- 模块列表
  - `Use-RawPipeline`: https://www.powershellgallery.com/packages/Use-RawPipeline/
  - `powershell-yaml`: https://www.powershellgallery.com/packages/powershell-yaml/
  - `PSStringTemplate`: https://www.powershellgallery.com/packages/PSStringTemplate/

### 重新启动系统

- 为保证环境变量等生效请重启操作系统
