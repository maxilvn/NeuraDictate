"""Lightweight control panel window running in a separate Python process."""

import json
import subprocess
import sys
import textwrap
from typing import Callable

from . import config


class SettingsWindow:
    def __init__(self, current_config: dict, on_save: Callable[[dict], None]):
        self._cfg = dict(current_config)
        self._on_save = on_save

    def show(self, blocking: bool = False) -> None:
        """Launch control panel as a separate Python process."""
        def _run():
            script = _build_settings_script(self._cfg)
            result = subprocess.run(
                [sys.executable, "-c", script],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0 and result.stdout.strip():
                try:
                    new_cfg = json.loads(result.stdout.strip())
                    self._cfg.update(new_cfg)
                    self._on_save(self._cfg)
                except json.JSONDecodeError:
                    pass

        if blocking:
            _run()
            return

        import threading
        threading.Thread(target=_run, daemon=True).start()


def _build_settings_script(cfg: dict) -> str:
    cfg_json = json.dumps(cfg)
    models_json = json.dumps(config.AVAILABLE_MODELS)
    langs_json = json.dumps(list(config.AVAILABLE_LANGUAGES.keys()))
    lang_names_json = json.dumps(config.AVAILABLE_LANGUAGES)
    hotkeys_json = json.dumps(config.HOTKEY_OPTIONS)
    app_name_json = json.dumps(config.APP_NAME)
    status_path_json = json.dumps(str(config.STATUS_PATH))
    log_path_json = json.dumps(str(config.LOG_PATH))
    history_path_json = json.dumps(str(config.TRANSCRIPT_HISTORY_PATH))
    last_path_json = json.dumps(str(config.LAST_TRANSCRIPT_PATH))
    is_mac_json = "True" if sys.platform == "darwin" else "False"
    model_info_json = json.dumps(config.MODEL_INFO)
    model_dir_json = json.dumps(str(config.MODEL_DIR))
    project_dir_json = json.dumps(str(config.MODULE_DIR))

    return textwrap.dedent(
        f"""\
import json, pathlib, subprocess, sys, threading
import tkinter as tk
from tkinter import ttk

cfg = json.loads({cfg_json!r})
models = json.loads({models_json!r})
langs = json.loads({langs_json!r})
lang_names = json.loads({lang_names_json!r})
hotkeys = json.loads({hotkeys_json!r})
app_name = json.loads({app_name_json!r})
status_path = pathlib.Path(json.loads({status_path_json!r}))
log_path = pathlib.Path(json.loads({log_path_json!r}))
history_path = pathlib.Path(json.loads({history_path_json!r}))
last_path = pathlib.Path(json.loads({last_path_json!r}))
is_mac = {is_mac_json}
model_info = json.loads({model_info_json!r})
model_dir = pathlib.Path(json.loads({model_dir_json!r}))
project_dir = pathlib.Path(json.loads({project_dir_json!r}))

# ── Palette ──
BG      = "#2B2B2D"
FG      = "#E5E5EA"
FG2     = "#98989D"
FG3     = "#636366"
ACCENT  = "#0A84FF"
GREEN   = "#32D74B"
RED     = "#FF453A"
ORANGE  = "#FF9F0A"
CTRL    = "#3A3A3C"
CTRL_HL = "#48484A"
SEP     = "#3A3A3C"

FONT = "SF Pro Text" if is_mac else "Segoe UI"
MONO = "SF Mono" if is_mac else "Consolas"

root = tk.Tk()
root.title(app_name)
root.configure(bg=BG)
root.resizable(True, True)
root.minsize(480, 540)
root.attributes("-topmost", True)
root.geometry("560x660")
root.update_idletasks()
w, h = root.winfo_width(), root.winfo_height()
x = (root.winfo_screenwidth() - w) // 2
y = (root.winfo_screenheight() - h) // 2
root.geometry(f"{{w}}x{{h}}+{{x}}+{{y}}")

# ── ttk theme ──
style = ttk.Style()
style.theme_use("clam")

style.configure(".", background=BG, foreground=FG, font=(FONT, 12),
                borderwidth=0, focuscolor=BG)
style.configure("TFrame", background=BG)
style.configure("TLabel", background=BG, foreground=FG, font=(FONT, 12))
style.configure("Dim.TLabel", foreground=FG2, font=(FONT, 10))
style.configure("Tiny.TLabel", foreground=FG3, font=(FONT, 9))

# Rounded-feel buttons via padding and field background
style.configure("Accent.TButton", background=ACCENT, foreground="white",
                font=(FONT, 11, "bold"), padding=(16, 6))
style.map("Accent.TButton",
          background=[("active", "#0070E0"), ("pressed", "#005BBB")])

style.configure("Ctrl.TButton", background=CTRL, foreground=FG,
                font=(FONT, 11), padding=(12, 6))
style.map("Ctrl.TButton",
          background=[("active", CTRL_HL), ("pressed", "#555558")])

style.configure("Small.TButton", background=CTRL, foreground=FG2,
                font=(FONT, 10), padding=(8, 3))
style.map("Small.TButton",
          background=[("active", CTRL_HL)])

style.configure("Danger.TButton", background=BG, foreground=RED,
                font=(FONT, 10), padding=(8, 3))
style.map("Danger.TButton",
          background=[("active", CTRL)])

style.configure("Download.TButton", background=ACCENT, foreground="white",
                font=(FONT, 10, "bold"), padding=(10, 3))
style.map("Download.TButton",
          background=[("active", "#0070E0"), ("disabled", FG3)])

# Combobox styling
style.configure("TCombobox", fieldbackground=CTRL, background=CTRL,
                foreground=FG, arrowcolor=FG2, padding=(8, 6),
                selectbackground=CTRL, selectforeground=FG)
style.map("TCombobox",
          fieldbackground=[("readonly", CTRL), ("focus", CTRL)],
          selectbackground=[("readonly", CTRL)],
          selectforeground=[("readonly", FG)])
root.option_add("*TCombobox*Listbox.background", CTRL)
root.option_add("*TCombobox*Listbox.foreground", FG)
root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
root.option_add("*TCombobox*Listbox.selectForeground", "white")
root.option_add("*TCombobox*Listbox.font", (FONT, 12))

# Checkbutton styling
style.configure("TCheckbutton", background=BG, foreground=FG, font=(FONT, 12),
                indicatorsize=16)
style.map("TCheckbutton",
          background=[("active", BG)],
          foreground=[("active", FG)],
          indicatorcolor=[("selected", ACCENT), ("!selected", CTRL)])

# ── Helpers ──
def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def get_downloaded():
    dl = []
    if model_dir.exists():
        for name in models:
            for entry in model_dir.iterdir():
                if entry.is_dir() and name in entry.name:
                    dl.append(name)
                    break
    return dl

# ── Tab system ──
tab_bar = ttk.Frame(root)
tab_bar.pack(fill="x", padx=20, pady=(16, 0))

current_tab = tk.StringVar(value="settings")
tab_frames = {{}}
tab_btns = {{}}

style.configure("Tab.TButton", background=BG, foreground=FG2,
                font=(FONT, 12), padding=(14, 5))
style.map("Tab.TButton", background=[("active", CTRL)])
style.configure("TabActive.TButton", background=CTRL, foreground=FG,
                font=(FONT, 12, "bold"), padding=(14, 5))
style.map("TabActive.TButton", background=[("active", CTRL_HL)])

def switch_tab(name):
    current_tab.set(name)
    for n, f in tab_frames.items():
        f.pack_forget()
    tab_frames[name].pack(fill="both", expand=True, padx=0, pady=(12, 16))
    for n, b in tab_btns.items():
        b.configure(style="TabActive.TButton" if n == name else "Tab.TButton")

for tname, tlabel, ticon in [("settings", "Settings", "\\u2699"), ("models", "Models", "\\u25BC"), ("history", "History", "\\u23F0")]:
    b = ttk.Button(tab_bar, text=f"{{ticon}}  {{tlabel}}", style="Tab.TButton",
                   command=lambda n=tname: switch_tab(n))
    b.pack(side="left", padx=(0, 4))
    tab_btns[tname] = b

# ── Status ──
sep0 = ttk.Frame(root, height=1)
sep0.pack(fill="x", padx=20, pady=(10, 0))
tk.Frame(sep0, bg=SEP, height=1).pack(fill="x")

status_row = ttk.Frame(root)
status_row.pack(fill="x", padx=20, pady=(6, 0))

status_dot = tk.Label(status_row, text="\\u25CF", font=(FONT, 7), bg=BG, fg=GREEN)
status_dot.pack(side="left")
status_lbl = ttk.Label(status_row, text="Ready", style="Dim.TLabel")
status_lbl.pack(side="left", padx=(5, 0))
hotkey_lbl = tk.Label(status_row, text="", font=(MONO, 10), bg=BG, fg=FG3)
hotkey_lbl.pack(side="right")

sep1 = ttk.Frame(root, height=1)
sep1.pack(fill="x", padx=20, pady=(6, 0))
tk.Frame(sep1, bg=SEP, height=1).pack(fill="x")

# ════════════════════════════════════════
# AUTOSAVE
# ════════════════════════════════════════
_init_done = [False]
_save_pending = [False]

def schedule_save(*_a):
    if not _init_done[0]:
        return
    if not _save_pending[0]:
        _save_pending[0] = True
        root.after(250, do_save)

def do_save():
    _save_pending[0] = False
    status_lbl.config(text="Saved", foreground=GREEN)
    root.after(1200, lambda: status_lbl.config(foreground=FG2))

# ════════════════════════════════════════
# TAB: Settings
# ════════════════════════════════════════
sf = ttk.Frame(root)
tab_frames["settings"] = sf

def field_label(parent, text):
    ttk.Label(parent, text=text, style="Dim.TLabel").pack(anchor="w", padx=20, pady=(12, 4))

def make_combo(parent, values, display_map, current):
    display_vals = [display_map.get(v, v) if display_map else v for v in values]
    cur = display_map.get(current, current) if display_map else current
    if cur not in display_vals and display_vals:
        cur = display_vals[0]
    var = tk.StringVar(value=cur)
    var.trace_add("write", schedule_save)
    cb = ttk.Combobox(parent, textvariable=var, values=display_vals,
                       state="readonly", width=30, font=(FONT, 12))
    cb.pack(anchor="w", padx=20, pady=(0, 4))
    return var, display_map

def make_sep(parent):
    f = ttk.Frame(parent, height=1)
    f.pack(fill="x", padx=20, pady=6)
    tk.Frame(f, bg=SEP, height=1).pack(fill="x")

def make_check(parent, text, current):
    var = tk.BooleanVar(value=current)
    var.trace_add("write", schedule_save)
    ttk.Checkbutton(parent, text=text, variable=var).pack(anchor="w", padx=18, pady=3)
    return var

field_label(sf, "\\u2328  Hotkey")
hotkey_var = make_combo(sf, list(hotkeys.keys()), hotkeys,
                         cfg.get("hotkey", "fn" if is_mac else "Key.alt_r"))
make_sep(sf)

field_label(sf, "\\U0001F9E0  Model")
downloaded = get_downloaded()
available = [m for m in models if m in downloaded]
if not available:
    available = models[:1]
cur_model = cfg.get("model", "small")
if cur_model not in available:
    cur_model = available[0]
model_var = make_combo(sf, available, {{}}, cur_model)
if not downloaded:
    ttk.Label(sf, text="No models yet \\u2014 download in Models tab",
              foreground=ORANGE, font=(FONT, 10)).pack(anchor="w", padx=20, pady=(2, 0))
make_sep(sf)

field_label(sf, "\\U0001F310  Language")
lang_var = make_combo(sf, langs, lang_names, cfg.get("language", "auto"))
make_sep(sf)

paste_var = make_check(sf, "  Auto-paste after transcription", cfg.get("auto_paste", True))
gpu_var = make_check(sf, "  Use GPU (CUDA)", cfg.get("gpu_enabled", True))

# On close: output final config
def on_close():
    result = dict(cfg)
    rev_hk = {{v: k for k, v in hotkeys.items()}}
    result["hotkey"] = rev_hk.get(hotkey_var[0].get(), hotkey_var[0].get())
    result["model"] = model_var[0].get()
    rev_lang = {{v: k for k, v in lang_names.items()}}
    result["language"] = rev_lang.get(lang_var[0].get(), lang_var[0].get())
    result["auto_paste"] = paste_var.get()
    result["gpu_enabled"] = gpu_var.get()
    print(json.dumps(result))
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)

# ════════════════════════════════════════
# TAB: Models
# ════════════════════════════════════════
mf = ttk.Frame(root)
tab_frames["models"] = mf

m_canvas = tk.Canvas(mf, bg=BG, highlightthickness=0, bd=0)
m_inner = ttk.Frame(m_canvas)
m_inner.bind("<Configure>", lambda e: m_canvas.configure(scrollregion=m_canvas.bbox("all")))
m_canvas.create_window((0, 0), window=m_inner, anchor="nw")
m_canvas.pack(fill="both", expand=True)

def build_models():
    for w in m_inner.winfo_children():
        w.destroy()
    dl = get_downloaded()
    for i, name in enumerate(models):
        info = model_info.get(name, {{}})
        is_dl = name in dl
        row = ttk.Frame(m_inner)
        row.pack(fill="x", padx=20, pady=(8, 0))

        left = ttk.Frame(row)
        left.pack(side="left", fill="x", expand=True)

        title = name
        if info.get("recommended"):
            title += "  \\u2B50"
        ttk.Label(left, text=title, font=(FONT, 13, "bold")).pack(anchor="w")

        sp = info.get("speed", 0)
        qu = info.get("quality", 0)
        sz = info.get("size", "")
        meta = f"{{sz}}  \\u00B7  Speed {{sp}}/5  \\u00B7  Quality {{qu}}/5"
        ttk.Label(left, text=meta, style="Dim.TLabel").pack(anchor="w", pady=(1, 0))

        right = ttk.Frame(row)
        right.pack(side="right")

        if is_dl:
            ttk.Label(right, text="\\u2713", foreground=GREEN, font=(FONT, 14)).pack(side="left", padx=(0, 8))
            def mk_del(m):
                def do_del():
                    subprocess.Popen([
                        sys.executable, "-c",
                        f"import sys; sys.path.insert(0, str(r'{{project_dir.parent}}')); "
                        f"from voice_input.transcriber import delete_model; delete_model('{{m}}')"
                    ])
                    root.after(600, build_models)
                return do_del
            ttk.Button(right, text="Remove", style="Danger.TButton",
                       command=mk_del(name)).pack(side="left")
        else:
            def mk_dl(m, bref):
                def do_dl():
                    bref[0].config(text="Downloading...")
                    bref[0].state(["disabled"])
                    def run():
                        subprocess.run([
                            sys.executable, "-c",
                            f"import sys; sys.path.insert(0, str(r'{{project_dir.parent}}')); "
                            f"from voice_input.transcriber import download_model; download_model('{{m}}')"
                        ])
                        root.after(0, build_models)
                    threading.Thread(target=run, daemon=True).start()
                return do_dl
            bref = [None]
            b = ttk.Button(right, text="\\u2913  Download", style="Download.TButton")
            bref[0] = b
            b.config(command=mk_dl(name, bref))
            b.pack(side="left")

        if i < len(models) - 1:
            f = ttk.Frame(m_inner, height=1)
            f.pack(fill="x", padx=20, pady=(8, 0))
            tk.Frame(f, bg=SEP, height=1).pack(fill="x")

build_models()

# ════════════════════════════════════════
# TAB: History
# ════════════════════════════════════════
hf = ttk.Frame(root)
tab_frames["history"] = hf

h_canvas = tk.Canvas(hf, bg=BG, highlightthickness=0, bd=0)
h_scroll = ttk.Scrollbar(hf, orient="vertical", command=h_canvas.yview)
h_inner = ttk.Frame(h_canvas)
h_inner.bind("<Configure>", lambda e: h_canvas.configure(scrollregion=h_canvas.bbox("all")))
h_canvas.create_window((0, 0), window=h_inner, anchor="nw")
h_canvas.configure(yscrollcommand=h_scroll.set)

def _mw(event):
    h_canvas.yview_scroll(-1 * (event.delta // 120 or (1 if event.delta > 0 else -1)), "units")
h_canvas.bind_all("<MouseWheel>", _mw)
h_scroll.pack(side="right", fill="y")
h_canvas.pack(side="left", fill="both", expand=True)

def build_history():
    for w in h_inner.winfo_children():
        w.destroy()
    history = read_json(history_path, [])
    if not history:
        ttk.Label(h_inner, text="No transcripts yet.", style="Dim.TLabel").pack(
            anchor="w", padx=20, pady=20)
        return
    for i, entry in enumerate(history[:20]):
        stamp = entry.get("timestamp", "")
        text = entry.get("text", "")
        row = ttk.Frame(h_inner)
        row.pack(fill="x", padx=20, pady=(10, 0))
        hdr = ttk.Frame(row)
        hdr.pack(fill="x")
        time_s = stamp.split(" ")[-1] if " " in stamp else stamp
        date_s = stamp.split(" ")[0] if " " in stamp else ""
        ttk.Label(hdr, text=f"\\u23F0 {{time_s}}", font=(MONO, 10), foreground=FG2).pack(side="left")
        ttk.Label(hdr, text=date_s, style="Tiny.TLabel").pack(side="left", padx=(8, 0))

        def mk_copy(t, btn):
            def do_copy():
                if is_mac:
                    p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
                    p.communicate(t.encode("utf-8"))
                else:
                    root.clipboard_clear()
                    root.clipboard_append(t)
                btn.config(text="\\u2713 Copied")
                root.after(1000, lambda: btn.config(text="\\u2398 Copy"))
            return do_copy

        cb = ttk.Button(hdr, text="\\u2398 Copy", style="Small.TButton")
        cb.pack(side="right")
        cb.config(command=mk_copy(text, cb))

        ttk.Label(row, text=text, wraplength=480, justify="left",
                  font=(FONT, 12)).pack(fill="x", pady=(4, 0))

        if i < min(len(history), 20) - 1:
            sf2 = ttk.Frame(h_inner, height=1)
            sf2.pack(fill="x", padx=20, pady=(10, 0))
            tk.Frame(sf2, bg=SEP, height=1).pack(fill="x")

    h_canvas.update_idletasks()
    h_canvas.configure(scrollregion=h_canvas.bbox("all"))

# ── Polling ──
def refresh(sched=True):
    status = read_json(status_path, {{}})
    state = status.get("state", "hidden")
    detail = status.get("detail", "Ready")
    hk = status.get("hotkey", "")

    if not status.get("active", True):
        lbl, dot = "Paused", ORANGE
    elif state == "downloading":
        lbl, dot = detail, ORANGE
    elif state == "loading":
        lbl, dot = detail, ACCENT
    elif state == "listening":
        lbl, dot = "\\u25CF  Listening", RED
    elif state == "transcribing":
        lbl, dot = "Transcribing...", ORANGE
    elif state in ("done", "hidden"):
        lbl = "Ready" if detail in ("Ready", "Settings saved", "Starting", "") else detail
        dot = GREEN
    else:
        lbl, dot = detail or "Ready", FG2

    status_dot.config(fg=dot)
    if not _save_pending[0]:
        status_lbl.config(text=lbl)
    hotkey_lbl.config(text=hk)

    if current_tab.get() == "history":
        build_history()

    if sched:
        root.after(1200, refresh)

# ── Init ──
_init_done[0] = True
switch_tab("settings")
refresh()
root.mainloop()
"""
    )
