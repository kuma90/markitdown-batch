@echo off
REM ═══════════════════════════════════════════════════════
REM  MarkItDown 批量转换 — Windows 打包脚本
REM  双击运行或命令行: build.bat
REM ═══════════════════════════════════════════════════════

echo 🔨 正在安装依赖...
pip install -r requirements.txt

echo.
echo 📦 正在打包...
python build_exe.py

echo.
echo ✅ 打包完成！可执行文件在 dist\ 目录下
pause
