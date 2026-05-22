#!/usr/bin/env python3
"""
MarkItDown 批量转换工具 — GUI 版

图形界面版本，支持选择输入/输出文件夹，实时显示转换进度。
"""

import argparse
import os
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import requests

# ── Windows 控制台 UTF-8 ──────────────────────────────────────
if sys.platform == "win32" and sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ── 支持的文件类型 ──────────────────────────────────────────────
SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".pptx", ".xlsx", ".xls", ".ppt", ".doc",
    ".html", ".htm", ".epub",
    ".csv", ".json", ".xml", ".txt", ".md", ".rst",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp",
    ".wav", ".mp3", ".zip",
}

SKIP_PATTERNS = {".git", "__pycache__", "node_modules", ".venv", "venv", "output"}


def collect_files(source_dir: Path) -> list[Path]:
    """递归收集所有支持的文件"""
    files = []
    for root, dirs, filenames in os.walk(source_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_PATTERNS and not d.startswith(".")]
        for f in filenames:
            fp = Path(root) / f
            if fp.suffix.lower() in SUPPORTED_EXTENSIONS:
                files.append(fp)
    return sorted(files)


def make_report(results, source_dir, output_dir, api_url, total_duration):
    """生成转换报告"""
    source_dir = Path(source_dir)
    output_dir = Path(output_dir)
    success = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "failed"]

    lines = [
        f"# MarkItDown 批量转换报告",
        f"",
        f"**转换时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**源目录:** `{source_dir}`",
        f"**输出目录:** `{output_dir}`",
        f"**API 地址:** `{api_url}`",
        f"**总耗时:** {total_duration:.1f}s",
        f"",
        f"## 统计",
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
            lines.append(f"| {r['rel_path']} | {r['size_kb']:.1f} KB | {r['duration_s']:.1f}s |")

    if failed:
        lines.append("")
        lines.append("## ❌ 转换失败")
        lines.append("")
        lines.append("| 文件 | 大小 | 错误信息 |")
        lines.append("|------|------|----------|")
        for r in failed:
            err = r["error"].replace("|", "\\|").replace("\n", " ")[:100]
            lines.append(f"| {r['rel_path']} | {r['size_kb']:.1f} KB | {err} |")

    return "\n".join(lines) + "\n"


class MarkItDownGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("MarkItDown 批量转换工具")
        self.root.geometry("740x620")
        self.root.minsize(600, 500)

        # 设置图标/样式
        self.root.configure(bg="#f0f2f5")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", font=("Microsoft YaHei", 10), padding=6)
        style.configure("TLabel", font=("Microsoft YaHei", 10), background="#f0f2f5")
        style.configure("TEntry", font=("Microsoft YaHei", 10))
        style.configure("TLabelframe", font=("Microsoft YaHei", 10, "bold"), background="#f0f2f5")
        style.configure("TLabelframe.Label", font=("Microsoft YaHei", 10, "bold"), background="#f0f2f5")
        style.configure("Green.Horizontal.TProgressbar", troughcolor="#e0e0e0", background="#4caf50")
        style.configure("Red.Horizontal.TProgressbar", troughcolor="#e0e0e0", background="#f44336")

        self.cancel_flag = False
        self.results = []
        self.build_ui()

        # 居中
        self.root.update_idletasks()
        w, h = self.root.winfo_width(), self.root.winfo_height()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"+{(sw-w)//2}+{(sh-h)//2}")

    def build_ui(self):
        # ── 标题 ──────────────────────────────────────────
        header = tk.Frame(self.root, bg="#1976d2", height=50)
        header.pack(fill="x")
        tk.Label(
            header, text="📄 MarkItDown 批量转换", font=("Microsoft YaHei", 14, "bold"),
            fg="white", bg="#1976d2"
        ).pack(pady=10)

        main = tk.Frame(self.root, bg="#f0f2f5")
        main.pack(fill="both", expand=True, padx=16, pady=12)

        # ── 文件夹选择 ────────────────────────────────────
        folder_frame = ttk.LabelFrame(main, text="文件夹设置", padding=12)
        folder_frame.pack(fill="x", pady=(0, 10))

        # 输入目录
        tk.Label(folder_frame, text="输入目录:", font=("Microsoft YaHei", 10),
                 bg="#f0f2f5").grid(row=0, column=0, sticky="e", padx=(0, 8))
        self.input_var = tk.StringVar(value=str(Path.home() / "Documents"))
        self.input_entry = ttk.Entry(folder_frame, textvariable=self.input_var, width=50)
        self.input_entry.grid(row=0, column=1, sticky="ew", padx=(0, 4))
        ttk.Button(folder_frame, text="浏览...", command=self.browse_input,
                   width=8).grid(row=0, column=2)

        # 输出目录
        tk.Label(folder_frame, text="输出目录:", font=("Microsoft YaHei", 10),
                 bg="#f0f2f5").grid(row=1, column=0, sticky="e", padx=(0, 8), pady=(8, 0))
        self.output_var = tk.StringVar(value="")
        self.output_entry = ttk.Entry(folder_frame, textvariable=self.output_var, width=50)
        self.output_entry.grid(row=1, column=1, sticky="ew", padx=(0, 4), pady=(8, 0))
        ttk.Button(folder_frame, text="浏览...", command=self.browse_output,
                   width=8).grid(row=1, column=2, pady=(8, 0))
        tk.Label(folder_frame, text="（留空则在输入目录下创建 output 文件夹）",
                 font=("Microsoft YaHei", 8), fg="#888", bg="#f0f2f5").grid(
            row=2, column=1, sticky="w", pady=(2, 0))

        folder_frame.columnconfigure(1, weight=1)

        # ── API 设置 ──────────────────────────────────────
        api_frame = ttk.LabelFrame(main, text="API 设置", padding=12)
        api_frame.pack(fill="x", pady=(0, 10))

        tk.Label(api_frame, text="API 地址:", font=("Microsoft YaHei", 10),
                 bg="#f0f2f5").grid(row=0, column=0, sticky="e", padx=(0, 8))
        self.api_var = tk.StringVar(value="http://192.168.154.129:8765")
        self.api_entry = ttk.Entry(api_frame, textvariable=self.api_var, width=40)
        self.api_entry.grid(row=0, column=1, sticky="ew", padx=(0, 4))

        tk.Label(api_frame, text="并行数:", font=("Microsoft YaHei", 10),
                 bg="#f0f2f5").grid(row=0, column=2, sticky="e", padx=(12, 8))
        self.workers_var = tk.IntVar(value=3)
        workers_spin = ttk.Spinbox(api_frame, from_=1, to=20, textvariable=self.workers_var,
                                   width=5, font=("Microsoft YaHei", 10))
        workers_spin.grid(row=0, column=3, sticky="w")

        ttk.Button(api_frame, text="测试连接", command=self.test_api,
                   width=10).grid(row=0, column=4, padx=(12, 0))

        api_frame.columnconfigure(1, weight=1)

        # ── 控制按钮 ──────────────────────────────────────
        btn_frame = tk.Frame(main, bg="#f0f2f5")
        btn_frame.pack(fill="x", pady=(0, 8))

        self.start_btn = tk.Button(
            btn_frame, text="🚀 开始扫描并转换", font=("Microsoft YaHei", 11, "bold"),
            bg="#4caf50", fg="white", activebackground="#43a047",
            relief="flat", padx=20, pady=6, cursor="hand2",
            command=self.start_scan
        )
        self.start_btn.pack(side="left", padx=(0, 8))

        self.cancel_btn = tk.Button(
            btn_frame, text="⏹ 取消", font=("Microsoft YaHei", 10),
            bg="#f44336", fg="white", activebackground="#e53935",
            relief="flat", padx=14, pady=6, cursor="hand2",
            command=self.cancel, state="disabled"
        )
        self.cancel_btn.pack(side="left")

        # ── 进度条 ────────────────────────────────────────
        progress_frame = tk.Frame(main, bg="#f0f2f5")
        progress_frame.pack(fill="x", pady=(0, 6))

        self.progress_var = tk.StringVar(value="就绪")
        self.progress_bar = ttk.Progressbar(
            progress_frame, mode="determinate", style="Green.Horizontal.TProgressbar"
        )
        self.progress_bar.pack(fill="x")

        self.progress_label = tk.Label(
            progress_frame, textvariable=self.progress_var,
            font=("Microsoft YaHei", 9), fg="#666", bg="#f0f2f5"
        )
        self.progress_label.pack(anchor="w", pady=(2, 0))

        # 统计
        self.stats_var = tk.StringVar(value="")
        self.stats_label = tk.Label(
            main, textvariable=self.stats_var,
            font=("Microsoft YaHei", 10, "bold"), fg="#333", bg="#f0f2f5"
        )
        self.stats_label.pack(anchor="w", pady=(0, 4))

        # ── 日志区域 ──────────────────────────────────────
        log_frame = ttk.LabelFrame(main, text="转换日志", padding=8)
        log_frame.pack(fill="both", expand=True)

        self.log_text = tk.Text(
            log_frame, font=("Consolas", 9), wrap="word",
            bg="#1e1e1e", fg="#d4d4d4", insertbackground="white",
            relief="flat", borderwidth=0
        )
        self.log_text.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=scrollbar.set)

        # 颜色标签
        self.log_text.tag_configure("success", foreground="#4caf50")
        self.log_text.tag_configure("error", foreground="#f44336")
        self.log_text.tag_configure("info", foreground="#64b5f6")
        self.log_text.tag_configure("warn", foreground="#ff9800")

    def log(self, msg, tag=""):
        self.log_text.insert("end", msg + "\n", tag)
        self.log_text.see("end")
        self.root.update_idletasks()

    def browse_input(self):
        path = filedialog.askdirectory(title="选择输入文件夹")
        if path:
            self.input_var.set(path)

    def browse_output(self):
        path = filedialog.askdirectory(title="选择输出文件夹")
        if path:
            self.output_var.set(path)

    def test_api(self):
        api_url = self.api_var.get().strip().rstrip("/")
        try:
            r = requests.get(f"{api_url}/health", timeout=5)
            if r.status_code == 200:
                messagebox.showinfo("连接成功", f"✅ API 连接正常\n{api_url}")
                self.log(f"[OK] API 连接成功: {api_url}", "success")
            else:
                messagebox.showerror("连接失败", f"API 返回状态码: {r.status_code}")
        except Exception as e:
            self.log(f"[ERROR] 连接失败: {e}", "error")
            messagebox.showerror("连接失败",
                f"无法连接到 API:\n{api_url}\n\n请确保 MarkItDown API 服务已启动。")

    def cancel(self):
        self.cancel_flag = True
        self.cancel_btn.config(state="disabled")
        self.log("[WARN] ⏹ 正在取消...", "warn")

    def start_scan(self):
        """在新线程中执行扫描+转换，避免阻塞 UI"""
        if self.start_btn["state"] == "disabled":
            return
        self.cancel_flag = False
        self.results = []
        self.log_text.delete("1.0", "end")
        self.progress_bar["value"] = 0
        self.stats_var.set("")

        self.start_btn.config(state="disabled", bg="#aaa")
        self.cancel_btn.config(state="normal")

        t = threading.Thread(target=self._run_conversion, daemon=True)
        t.start()

    def _run_conversion(self):
        source_dir = Path(self.input_var.get().strip())
        if not source_dir.is_dir():
            self.root.after(0, lambda: messagebox.showerror("错误", f"输入目录不存在:\n{source_dir}"))
            self._reset_buttons()
            return

        output_dir = Path(self.output_var.get().strip()) if self.output_var.get().strip() else source_dir / "output"
        api_url = self.api_var.get().strip().rstrip("/")
        workers = self.workers_var.get()

        # 扫描
        self.log("─" * 50, "info")
        self.log(f"[SCAN] 正在扫描: {source_dir}", "info")
        self.root.after(0, lambda: self.progress_var.set("正在扫描文件..."))

        try:
            files = collect_files(source_dir)
        except Exception as e:
            self.log(f"[ERROR] 扫描失败: {e}", "error")
            self._reset_buttons()
            return

        if not files:
            self.log("[WARN] 未发现支持的文件", "warn")
            self.root.after(0, lambda: self.progress_var.set("未发现支持的文件"))
            self._reset_buttons()
            return

        self.log(f"[SCAN] 发现 {len(files)} 个文件", "info")
        self.root.after(0, lambda: self.progress_bar.configure(maximum=len(files)))
        self.root.after(0, lambda: self.progress_var.set(f"0/{len(files)}"))

        # 检查 API
        try:
            r = requests.get(f"{api_url}/health", timeout=5)
            self.log(f"[OK] API 连接正常", "success")
        except Exception:
            self.log(f"[ERROR] 无法连接 API: {api_url}", "error")
            self.root.after(0, lambda: messagebox.showerror(
                "连接失败", f"无法连接到 API:\n{api_url}\n\n请确保服务已启动。"))
            self._reset_buttons()
            return

        # 转换
        t_start = time.time()
        from concurrent.futures import ThreadPoolExecutor, as_completed

        self.log(f"[CONVERT] 开始转换 (并行数: {workers})", "info")
        self.log("─" * 50, "info")

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {}
            for fp in files:
                futures[pool.submit(self._convert_one, fp, source_dir, output_dir, api_url)] = fp

            for i, future in enumerate(as_completed(futures), 1):
                if self.cancel_flag:
                    break
                r = future.result()
                self.results.append(r)
                icon = "OK" if r["status"] == "success" else "FAIL"
                self.log(f"  [{icon}] {r['rel_path']}", "success" if r["status"] == "success" else "error")
                self.root.after(0, lambda i=i: self._update_progress(i, len(files)))

        total_duration = time.time() - t_start

        # 报告
        if self.results:
            self.results.sort(key=lambda x: x["rel_path"])
            report = make_report(self.results, str(source_dir), str(output_dir), api_url, total_duration)
            output_dir.mkdir(parents=True, exist_ok=True)
            report_path = output_dir / "转换报告.md"
            report_path.write_text(report, encoding="utf-8")

            ok = sum(1 for r in self.results if r["status"] == "success")
            fail = sum(1 for r in self.results if r["status"] == "failed")

            self.log("─" * 50, "info")
            self.log(f"[DONE] ✅ {ok} 成功  ❌ {fail} 失败  ⏱ {total_duration:.1f}s", "info")
            self.log(f"[DONE] 报告: {report_path}", "info")
            self.log(f"[DONE] 输出: {output_dir}", "info")

            stats = f"✅ {ok} 成功   ❌ {fail} 失败   ⏱ {total_duration:.1f}s"
            self.root.after(0, lambda s=stats: self.stats_var.set(s))

        self._reset_buttons()

    def _convert_one(self, file_path, source_dir, output_dir, api_url):
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
                return {"rel_path": str(rel), "status": "success", "size_kb": size_kb,
                        "duration_s": duration, "error": ""}
            else:
                return {"rel_path": str(rel), "status": "failed", "size_kb": size_kb,
                        "duration_s": duration, "error": resp.text[:200]}
        except Exception as e:
            duration = time.time() - start
            return {"rel_path": str(rel), "status": "failed", "size_kb": size_kb,
                    "duration_s": duration, "error": str(e)}

    def _update_progress(self, current, total):
        self.progress_bar["value"] = current
        self.progress_var.set(f"{current}/{total}")

    def _reset_buttons(self):
        self.root.after(0, lambda: self.start_btn.config(state="normal", bg="#4caf50"))
        self.root.after(0, lambda: self.cancel_btn.config(state="disabled"))

    def run(self):
        self.root.mainloop()


def main():
    parser = argparse.ArgumentParser(description="MarkItDown 批量转换 — GUI 版")
    parser.add_argument("--cli", action="store_true", help="命令行模式（默认 GUI）")
    args = parser.parse_args()

    if args.cli:
        # 命令行模式：委托给 batch_convert.py
        sys.argv = [sys.argv[0]] + [a for a in sys.argv[1:] if a != "--cli"]
        from batch_convert import main as cli_main
        cli_main()
    else:
        app = MarkItDownGUI()
        app.run()


if __name__ == "__main__":
    main()
