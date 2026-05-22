# MarkItDown 批量转换工具

将文件夹内所有文档（含子文件夹）批量转为 Markdown，通过局域网 API 完成。

## 快速开始

### 1. 确保 API 服务已启动

在运行 MarkItDown API 的机器上：
```bash
python markitdown_api.py --port 8765
```

### 2. 运行批量转换

**Windows（exe 版本）:**
```
MarkItDown批量转换.exe C:\Your\Documents
MarkItDown批量转换.exe . --api http://192.168.1.100:8765
```

**Linux/Mac（Python 源码）:**
```bash
pip install requests
python batch_convert.py /path/to/folder
python batch_convert.py . --api http://192.168.154.129:8765 --workers 5
```

## 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `source` | 源文件夹路径 | 当前目录 |
| `--api` | API 地址 | `http://192.168.154.129:8765` |
| `--output, -o` | 输出目录 | 源目录下的 `output/` |
| `--workers, -w` | 并行转换数 | 3 |
| `--no-parallel` | 禁用并行 | 逐个转换 |

## 输出

- `output/` — 按原目录结构保存的 `.md` 文件
- `output/转换报告.md` — 转换报告（含成功/失败统计表）

## 支持的格式

PDF · Word · Excel · PPT · HTML · EPUB · CSV · JSON · XML · 图片(OCR) · 音频(转录) · ZIP

## 打包成 exe

```bash
# 安装依赖
pip install -r requirements.txt

# 打包
python build_exe.py

# 可执行文件在 dist/ 目录
```

Windows 用户直接双击 `build.bat` 即可完成打包。
