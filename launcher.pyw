"""Double-click graphical launcher for installation, repair and startup."""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText

ROOT = Path(__file__).resolve().parent


class Launcher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Haruka 2.0 Setup")
        self.geometry("720x500")
        self.minsize(560, 420)
        self.configure(bg="#191919")
        self.process = None
        tk.Label(
            self,
            text="✦ HARUKA 2.0",
            bg="#191919",
            fg="#5e9fe8",
            font=("Arial", 13, "bold"),
        ).pack(anchor="w", padx=24, pady=(22, 4))
        tk.Label(
            self,
            text="Install, repair and open",
            bg="#191919",
            fg="white",
            font=("Arial", 26, "bold"),
        ).pack(anchor="w", padx=24)
        tk.Label(
            self,
            text="No configuration files or terminal commands are required.",
            bg="#191919",
            fg="#aaaaa6",
            font=("Arial", 11),
        ).pack(anchor="w", padx=24, pady=(6, 18))
        buttons = tk.Frame(self, bg="#191919")
        buttons.pack(fill="x", padx=24)
        self.install_button = tk.Button(
            buttons,
            text="Install / Repair and Open",
            command=self.install,
            bg="#5e9fe8",
            fg="#101820",
            activebackground="#75aceb",
            relief="flat",
            padx=16,
            pady=11,
            font=("Arial", 11, "bold"),
        )
        self.install_button.pack(side="left")
        tk.Button(
            buttons,
            text="Run diagnostics",
            command=lambda: self.start_process(["--doctor"]),
            bg="#383836",
            fg="white",
            activebackground="#4a4a47",
            relief="flat",
            padx=16,
            pady=11,
            font=("Arial", 11),
        ).pack(side="left", padx=10)
        self.output = ScrolledText(
            self,
            bg="#202020",
            fg="#e8e8e4",
            insertbackground="white",
            relief="flat",
            font=("Courier New", 10),
            wrap="word",
        )
        self.output.pack(fill="both", expand=True, padx=24, pady=20)
        self.protocol("WM_DELETE_WINDOW", self.close)

    def install(self):
        self.start_process([])

    def start_process(self, arguments):
        if self.process and self.process.poll() is None:
            return
        self.install_button.configure(state="disabled")
        self.output.delete("1.0", "end")
        thread = threading.Thread(target=self.worker, args=(arguments,), daemon=True)
        thread.start()

    def worker(self, arguments):
        try:
            self.process = subprocess.Popen(
                [sys.executable, str(ROOT / "bootstrap.py"), *arguments],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            for line in self.process.stdout:
                self.after(0, self.append, line)
            code = self.process.wait()
            if code:
                self.after(0, messagebox.showerror, "Haruka", "Setup could not finish. The log contains the reason.")
        except Exception as exc:
            self.after(0, messagebox.showerror, "Haruka", str(exc))
        finally:
            self.after(0, self.install_button.configure, {"state": "normal"})

    def append(self, line):
        self.output.insert("end", line)
        self.output.see("end")

    def close(self):
        if self.process and self.process.poll() is None:
            if not messagebox.askyesno("Haruka", "Setup is still running. Close anyway?"):
                return
            self.process.terminate()
        self.destroy()


if __name__ == "__main__":
    Launcher().mainloop()
