#!/usr/bin/env python3
"""打包脚本 — 将 batch_convert.py 打包成独立可执行文件"""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
SCRIPT = HERE / "batch_convert.py"
DIST = HERE / "dist"
NAME = "MarkItDown批量转换"

def build():
    print(f"🔨 正在打包 {SCRIPT} ...")
    print(f"   输出目录: {DIST}")

    DIST.mkdir(exist_ok=True)

    # 判断平台
    if sys.platform == "win32":
        ext = ".exe"
        icon_flag = []
    else:
        ext = ""
        icon_flag = []

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--console",
        "--clean",
        "--name", NAME,
        "--distpath", str(DIST),
        "--workpath", str(HERE / "build"),
        "--specpath", str(HERE),
        # 隐藏依赖
        "--hidden-import", "requests",
        "--hidden-import", "urllib3",
        "--hidden-import", "charset_normalizer",
        "--hidden-import", "certifi",
        "--hidden-import", "idna",
        *icon_flag,
        str(SCRIPT),
    ]

    result = subprocess.run(cmd, cwd=str(HERE))
    if result.returncode == 0:
        exe_path = DIST / f"{NAME}{ext}"
        print(f"\n✅ 打包成功!")
        print(f"   可执行文件: {exe_path}")
        if ext == ".exe":
            print(f"   大小: {exe_path.stat().st_size / 1024 / 1024:.1f} MB")
        print(f"\n   直接双击运行，或命令行:")
        print(f"   {exe_path} /path/to/folder")
    else:
        print(f"\n❌ 打包失败 (exit code: {result.returncode})")
        return result.returncode

    return 0

if __name__ == "__main__":
    sys.exit(build())
