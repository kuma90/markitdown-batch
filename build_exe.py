#!/usr/bin/env python3
"""打包脚本 — 将 MarkItDown 批量转换工具打包成独立可执行文件"""

import subprocess
import sys
from pathlib import Path

# Windows console UTF-8 fix
if sys.platform == "win32" and sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).parent
GUI_SCRIPT = HERE / "batch_convert_gui.py"
CLI_SCRIPT = HERE / "batch_convert.py"
DIST = HERE / "dist"
NAME = "MarkItDown批量转换"

BASE_FLAGS = [
    "--clean",
    "--distpath", str(DIST),
    "--workpath", str(HERE / "build"),
    "--specpath", str(HERE),
    "--hidden-import", "requests",
    "--hidden-import", "urllib3",
    "--hidden-import", "charset_normalizer",
    "--hidden-import", "certifi",
    "--hidden-import", "idna",
    "--hidden-import", "concurrent.futures",
]


def build_one(script: Path, name: str, console: bool = True):
    """打包单个版本"""
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--console" if console else "--windowed",
        "--name", name,
        *BASE_FLAGS,
        str(script),
    ]
    print(f"  打包 {name} (console={console})...")
    result = subprocess.run(cmd, cwd=str(HERE), capture_output=False)

    if result.returncode != 0:
        print(f"  ❌ {name} 打包失败")
        return False
    return True


def build():
    DIST.mkdir(exist_ok=True)
    ext = ".exe" if sys.platform == "win32" else ""

    print(f"🔨 开始打包...")
    print(f"   输出目录: {DIST}")

    # ── GUI 版（双击即用，无控制台窗口）──────────────────
    gui_name = NAME
    if not build_one(GUI_SCRIPT, gui_name, console=False):
        return 1

    gui_path = DIST / f"{gui_name}{ext}"
    size_mb = gui_path.stat().st_size / 1024 / 1024 if gui_path.exists() else 0
    print(f"   ✅ GUI 版: {gui_path}  ({size_mb:.1f} MB)")

    # ── CLI 版（命令行用）─────────────────────────────────
    cli_name = f"{NAME}-CLI"
    if not build_one(CLI_SCRIPT, cli_name, console=True):
        return 1

    cli_path = DIST / f"{cli_name}{ext}"
    size_mb = cli_path.stat().st_size / 1024 / 1024 if cli_path.exists() else 0
    print(f"   ✅ CLI 版: {cli_path}  ({size_mb:.1f} MB)")

    print(f"\n✅ 打包完成!")
    print(f"")
    print(f"   GUI 版（双击运行，图形界面）:")
    print(f"   {gui_path}")
    print(f"")
    print(f"   CLI 版（命令行使用）:")
    print(f"   {cli_path} /path/to/folder")
    return 0


if __name__ == "__main__":
    sys.exit(build())
