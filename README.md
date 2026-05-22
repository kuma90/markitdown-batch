# MarkItDown 批量转换工具

将文件夹内所有文档（含子文件夹）批量转为 Markdown，通过局域网 API 完成。

## 🖥 图形界面版（推荐）

双击 `MarkItDown批量转换.exe` 启动 GUI：

- 点击「浏览...」选择输入文件夹
- 选择输出文件夹（留空则自动创建 `output/`）
- 设置 API 地址和并行数
- 点击「测试连接」确认 API 可用
- 点击「开始扫描并转换」
- 实时查看进度条和日志
- 完成后自动生成 `output/转换报告.md`

## ⌨ 命令行版

```
MarkItDown批量转换-CLI.exe C:\Your\Documents
MarkItDown批量转换-CLI.exe . --api http://192.168.1.100:8765 --workers 5
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `source` | 源文件夹路径 | 当前目录 |
| `--api` | API 地址 | `http://192.168.154.129:8765` |
| `--output, -o` | 输出目录 | 源目录下的 `output/` |
| `--workers, -w` | 并行转换数 | 3 |

## 输出

- `output/` — 按原目录结构保存的 `.md` 文件
- `output/转换报告.md` — 转换报告（含成功/失败统计表）

## 支持的格式

PDF · Word · Excel · PPT · HTML · EPUB · CSV · JSON · XML · 图片(OCR) · 音频(转录) · ZIP

## 开发 / 打包

```bash
pip install -r requirements.txt

# Linux
python build_exe.py

# Windows
build.bat
```
