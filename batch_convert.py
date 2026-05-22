#!/usr/bin/env python3
"""
MarkItDown 批量转换工具

遍历指定文件夹（含所有子文件夹），将所有支持的文件通过局域网 MarkItDown API
转换为 Markdown，保存在 output 文件夹中，并生成转换报告。

用法:
    python batch_convert.py                          # 转换当前目录
    python batch_convert.py /path/to/folder          # 转换指定目录
    python batch_convert.py . --api http://IP:8765   # 指定 API 地址
    python batch_convert.py . --output ./results     # 指定输出目录
"""

import argparse
import json
import os
import sys
import time

# Windows console UTF-8 fix
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import NamedTuple

import requests

# ── 支持的文件类型 ──────────────────────────────────────────────
SUPPORTED_EXTENSIONS = {
    # Office 文档
    ".pdf", ".docx", ".pptx", ".xlsx", ".xls", ".ppt", ".doc",
    # 网页
    ".html", ".htm",
    # 电子书
    ".epub",
    # 纯文本/数据
    ".csv", ".json", ".xml", ".txt", ".md", ".rst",
    # 图片（OCR）
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp",
    # 音频（转录）
    ".wav", ".mp3",
    # 压缩包
    ".zip",
}

SKIP_PATTERNS = {".git", "__pycache__", "node_modules", ".venv", "venv", "output"}

# ── 数据结构 ────────────────────────────────────────────────────

class ConvertResult(NamedTuple):
    rel_path: str
    status: str       # "✅ 成功" / "❌ 失败" / "⏭ 跳过"
    size_kb: float
    duration_s: float
    error: str


def collect_files(source_dir: Path) -> list[Path]:
    """递归收集所有支持的文件"""
    files = []
    for root, dirs, filenames in os.walk(source_dir):
        # 跳过不需要的目录
        dirs[:] = [d for d in dirs if d not in SKIP_PATTERNS and not d.startswith(".")]
        for f in filenames:
            fp = Path(root) / f
            if fp.suffix.lower() in SUPPORTED_EXTENSIONS:
                files.append(fp)
    return sorted(files)


def convert_one(file_path: Path, source_dir: Path, output_dir: Path, api_url: str) -> ConvertResult:
    """转换单个文件"""
    rel = file_path.relative_to(source_dir)
    out_file = output_dir / rel.with_suffix(rel.suffix + ".md")
    size_kb = file_path.stat().st_size / 1024

    start = time.time()
    try:
        with open(file_path, "rb") as f:
            resp = requests.post(
                f"{api_url}/convert",
                files={"file": (file_path.name, f)},
                timeout=300,
            )
        duration = time.time() - start

        if resp.status_code == 200:
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(resp.text, encoding="utf-8")
            return ConvertResult(str(rel), "✅ 成功", size_kb, duration, "")
        else:
            detail = resp.text[:200]
            return ConvertResult(str(rel), "❌ 失败", size_kb, duration, detail)
    except requests.ConnectionError:
        duration = time.time() - start
        return ConvertResult(str(rel), "❌ 失败", size_kb, duration, "无法连接 API 服务")
    except Exception as e:
        duration = time.time() - start
        return ConvertResult(str(rel), "❌ 失败", size_kb, duration, str(e))


def generate_report(results: list[ConvertResult], source_dir: Path, output_dir: Path,
                    api_url: str, total_duration: float) -> str:
    """生成转换报告 Markdown"""
    success = [r for r in results if r.status == "✅ 成功"]
    failed = [r for r in results if r.status == "❌ 失败"]
    skipped = [r for r in results if r.status == "⏭ 跳过"]

    lines = [
        f"# 📄 MarkItDown 批量转换报告",
        f"",
        f"**转换时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**源目录:** `{source_dir}`",
        f"**输出目录:** `{output_dir}`",
        f"**API 地址:** `{api_url}`",
        f"**总耗时:** {total_duration:.1f}s",
        f"",
        f"## 📊 统计",
        f"",
        f"| 状态 | 数量 |",
        f"|------|------|",
        f"| ✅ 成功 | {len(success)} |",
        f"| ❌ 失败 | {len(failed)} |",
        f"| 📁 总计 | {len(results)} |",
        f"",
    ]

    if success:
        lines.append("## ✅ 转换成功")
        lines.append("")
        lines.append("| 文件 | 大小 | 耗时 |")
        lines.append("|------|------|------|")
        for r in success:
            lines.append(f"| {r.rel_path} | {r.size_kb:.1f} KB | {r.duration_s:.1f}s |")

    if failed:
        lines.append("")
        lines.append("## ❌ 转换失败")
        lines.append("")
        lines.append("| 文件 | 大小 | 错误信息 |")
        lines.append("|------|------|----------|")
        for r in failed:
            err = r.error.replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {r.rel_path} | {r.size_kb:.1f} KB | {err[:100]} |")

    return "\n".join(lines) + "\n"


def print_progress(current: int, total: int, filename: str, status: str):
    """终端进度显示"""
    bar_len = 36
    filled = int(bar_len * current / total) if total else 0
    bar = "█" * filled + "░" * (bar_len - filled)
    name = filename[-50:] if len(filename) > 50 else filename
    print(f"\r[{bar}] {current}/{total}  {status}  {name}", end="", flush=True)


def main():
    parser = argparse.ArgumentParser(
        description="MarkItDown 批量转换工具 — 将文件夹内所有文件转为 Markdown"
    )
    parser.add_argument(
        "source", nargs="?", default=".",
        help="源文件夹路径（默认: 当前目录）"
    )
    parser.add_argument(
        "--api", default=os.environ.get("MARKITDOWN_API", "http://192.168.154.129:8765"),
        help="MarkItDown API 地址 (默认: http://192.168.154.129:8765)"
    )
    parser.add_argument(
        "--output", "-o", default=None,
        help="输出目录 (默认: 源目录下的 output 文件夹)"
    )
    parser.add_argument(
        "--workers", "-w", type=int, default=3,
        help="并行转换数 (默认: 3)"
    )
    parser.add_argument(
        "--no-parallel", action="store_true",
        help="禁用并行，逐个转换"
    )
    args = parser.parse_args()

    source_dir = Path(args.source).resolve()
    if not source_dir.is_dir():
        print(f"❌ 错误: 目录不存在 — {source_dir}")
        sys.exit(1)

    output_dir = Path(args.output) if args.output else source_dir / "output"
    api_url = args.api.rstrip("/")

    # ── 收集文件 ──────────────────────────────────────────────
    print(f"🔍 正在扫描: {source_dir}")
    files = collect_files(source_dir)
    if not files:
        print("⚠ 未发现支持的文件，退出。")
        print(f"   支持的格式: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
        return

    print(f"📁 发现 {len(files)} 个文件")
    print(f"🌐 API: {api_url}")
    print(f"📤 输出: {output_dir}")
    print(f"⚡ 并行数: {1 if args.no_parallel else args.workers}")
    print()

    # ── 检查 API 连通性 ──────────────────────────────────────
    try:
        r = requests.get(f"{api_url}/health", timeout=5)
        if r.status_code != 200:
            print(f"❌ API 无响应: {r.status_code}")
            sys.exit(1)
        print(f"✅ API 连接正常\n")
    except requests.ConnectionError:
        print(f"❌ 无法连接到 API: {api_url}")
        print(f"   请确保 MarkItDown API 已启动")
        sys.exit(1)

    # ── 转换 ──────────────────────────────────────────────────
    results: list[ConvertResult] = []
    total = len(files)
    t_start = time.time()

    if args.no_parallel:
        for i, fp in enumerate(files, 1):
            r = convert_one(fp, source_dir, output_dir, api_url)
            results.append(r)
            icon = "✅" if r.status == "✅ 成功" else "❌"
            print_progress(i, total, fp.name, icon)
    else:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {
                pool.submit(convert_one, fp, source_dir, output_dir, api_url): fp
                for fp in files
            }
            for i, future in enumerate(as_completed(futures), 1):
                r = future.result()
                results.append(r)
                icon = "✅" if r.status == "✅ 成功" else "❌"
                print_progress(i, total, futures[future].name, icon)

    total_duration = time.time() - t_start
    print("\n")

    # ── 报告 ──────────────────────────────────────────────────
    results.sort(key=lambda x: x.rel_path)
    report = generate_report(results, source_dir, output_dir, api_url, total_duration)
    report_path = output_dir / "转换报告.md"
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")

    # ── 汇总 ──────────────────────────────────────────────────
    ok = sum(1 for r in results if r.status == "✅ 成功")
    fail = sum(1 for r in results if r.status == "❌ 失败")
    print(f"完成! ✅ {ok} 成功  ❌ {fail} 失败  ⏱ {total_duration:.1f}s")
    print(f"📄 报告: {report_path}")
    print(f"📂 输出: {output_dir}")

    return 0


if __name__ == "__main__":
    main()
