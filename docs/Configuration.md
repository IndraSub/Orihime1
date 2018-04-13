## 配置

待编辑

请参考 `episodes\example` 中的 `.yaml` 文件

`.project.yaml` 为项目配置文件，统一设定项目的处理参数；其他 `.yaml` 文件为分集配置文件，设定每集的标题和输入输出文件等

`episodes\example` 仅作为简单示例，详细用例请参考实际任务包内的 `.yaml` 配置文件

## 使用

- 将 __文件夹形式的任务包__ 放置在 `episodes` 目录下
- 在 `episodes` 目录下创建 `current-working.txt` 文件，在其中写入要执行的任务配置文件的相对路径 (如 `example\CM0001.yaml`)
- 运行 `media.bat` 启动任务流程并按提示操作
