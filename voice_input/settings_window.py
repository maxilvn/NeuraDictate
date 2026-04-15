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
    history_path_json = json.dumps(str(config.TRANSCRIPT_HISTORY_PATH))
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
history_path = pathlib.Path(json.loads({history_path_json!r}))
is_mac = {is_mac_json}
model_info = json.loads({model_info_json!r})
model_dir = pathlib.Path(json.loads({model_dir_json!r}))
project_dir = pathlib.Path(json.loads({project_dir_json!r}))

# ── Dark palette ──
BG      = "#1C1C1E"
FG      = "#E5E5EA"
FG2     = "#8E8E93"
FG3     = "#48484A"
ACCENT  = "#0A84FF"
GREEN   = "#32D74B"
RED     = "#FF453A"
ORANGE  = "#FF9F0A"
CTRL    = "#2C2C2E"
CTRL_HL = "#3A3A3C"
SEP     = "#38383A"

FONT = "SF Pro Text" if is_mac else "Segoe UI"
MONO = "SF Mono" if is_mac else "Consolas"
RAD  = 10  # corner radius

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

# ── ttk clam theme (allows color control on macOS) ──
sty = ttk.Style()
sty.theme_use("clam")
sty.configure(".", background=BG, foreground=FG, font=(FONT, 12), borderwidth=0, focuscolor=BG)
sty.configure("TFrame", background=BG)
sty.configure("TLabel", background=BG, foreground=FG, font=(FONT, 12))
sty.configure("Dim.TLabel", background=BG, foreground=FG2, font=(FONT, 10))
sty.configure("TCombobox", fieldbackground=CTRL, background=CTRL, foreground=FG,
              arrowcolor=FG2, padding=(10, 7), selectbackground=CTRL, selectforeground=FG)
sty.map("TCombobox",
        fieldbackground=[("readonly", CTRL), ("focus", CTRL)],
        selectbackground=[("readonly", CTRL)],
        selectforeground=[("readonly", FG)])
root.option_add("*TCombobox*Listbox.background", CTRL)
root.option_add("*TCombobox*Listbox.foreground", FG)
root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
root.option_add("*TCombobox*Listbox.selectForeground", "white")
root.option_add("*TCombobox*Listbox.font", (FONT, 12))
sty.configure("TCheckbutton", background=BG, foreground=FG, font=(FONT, 12), indicatorsize=16)
sty.map("TCheckbutton", background=[("active", BG)], foreground=[("active", FG)],
        indicatorcolor=[("selected", ACCENT), ("!selected", CTRL)])

# ── Rounded rect drawing ──
def rr(canvas, x1, y1, x2, y2, r, **kw):
    pts = [x1+r,y1, x2-r,y1, x2,y1, x2,y1+r,
           x2,y2-r, x2,y2, x2-r,y2, x1+r,y2,
           x1,y2, x1,y2-r, x1,y1+r, x1,y1]
    return canvas.create_polygon(pts, smooth=True, **kw)

class RBtn:
    \"\"\"Canvas-based rounded button.\"\"\"
    def __init__(self, parent, text, cmd, bg_color=CTRL, fg_color=FG,
                 hover=CTRL_HL, w=90, h=30, r=RAD, font_t=(FONT, 11), parent_bg=BG):
        self.c = tk.Canvas(parent, width=w, height=h, bg=parent_bg,
                           highlightthickness=0, bd=0, cursor="hand2")
        self._bg = bg_color
        self._fg = fg_color
        self._hover = hover
        self._w, self._h, self._r = w, h, r
        self._text = text
        self._font = font_t
        self._cmd = cmd
        self._draw(bg_color)
        self.c.bind("<Button-1>", lambda e: self._cmd())
        self.c.bind("<Enter>", lambda e: self._draw(self._hover))
        self.c.bind("<Leave>", lambda e: self._draw(self._bg))

    def _draw(self, bg):
        self.c.delete("all")
        rr(self.c, 1, 1, self._w-1, self._h-1, self._r, fill=bg, outline="")
        self.c.create_text(self._w//2, self._h//2, text=self._text,
                           fill=self._fg, font=self._font)

    def pack(self, **kw):
        self.c.pack(**kw)

    def config_text(self, text=None, fg=None):
        self._text = text if text else self._text
        self._fg = fg if fg else self._fg
        self._draw(self._bg)

    def disable(self):
        self.c.unbind("<Button-1>")
        self.c.config(cursor="")

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

def sep(parent):
    f = tk.Frame(parent, bg=SEP, height=1)
    f.pack(fill="x", padx=20, pady=8)

# ── Tab bar (rounded pill buttons) ──
tab_bar = tk.Frame(root, bg=BG)
tab_bar.pack(fill="x", padx=20, pady=(16, 0))

current_tab = tk.StringVar(value="settings")
tab_frames = {{}}
tab_canvases = {{}}
TAB_W, TAB_H = 100, 32

def draw_tab(name, active):
    c = tab_canvases[name]
    c.delete("all")
    bg = CTRL_HL if active else BG
    fg = FG if active else FG2
    rr(c, 1, 1, TAB_W-1, TAB_H-1, TAB_H//2, fill=bg, outline="")
    font = (FONT, 11, "bold") if active else (FONT, 11)
    c.create_text(TAB_W//2, TAB_H//2, text=name.title(), fill=fg, font=font)

def switch_tab(name):
    current_tab.set(name)
    for n, f in tab_frames.items():
        f.pack_forget()
    tab_frames[name].pack(fill="both", expand=True, padx=0, pady=(10, 16))
    for n in tab_canvases:
        draw_tab(n, n == name)
    # Refresh model dropdown when switching to settings (picks up new downloads)
    if name == "settings":
        refresh_model_dropdown()

for tname in ["settings", "models", "history"]:
    c = tk.Canvas(tab_bar, width=TAB_W, height=TAB_H, bg=BG, highlightthickness=0, bd=0, cursor="hand2")
    c.pack(side="left", padx=(0, 4))
    c.bind("<Button-1>", lambda e, n=tname: switch_tab(n))
    tab_canvases[tname] = c

# ── Status line ──
sep(root)
status_row = tk.Frame(root, bg=BG)
status_row.pack(fill="x", padx=20)

status_dot = tk.Label(status_row, text="\\u25CF", font=(FONT, 8), bg=BG, fg=GREEN)
status_dot.pack(side="left")
status_lbl = tk.Label(status_row, text="Ready", font=(FONT, 10), bg=BG, fg=FG2)
status_lbl.pack(side="left", padx=(5, 0))
hotkey_lbl = tk.Label(status_row, text="", font=(MONO, 10), bg=BG, fg=FG3)
hotkey_lbl.pack(side="right")

sep(root)

# ════════════════════════════════════════
# AUTOSAVE
# ════════════════════════════════════════
_init = [False]

def schedule_save(*_a):
    if _init[0]:
        status_lbl.config(text="Saved", fg=GREEN)
        root.after(1500, lambda: status_lbl.config(fg=FG2))

# ════════════════════════════════════════
# TAB: Settings
# ════════════════════════════════════════
sf = tk.Frame(root, bg=BG)
tab_frames["settings"] = sf

def field_label(parent, text):
    tk.Label(parent, text=text, font=(FONT, 10), bg=BG, fg=FG2).pack(
        anchor="w", padx=22, pady=(12, 4))

def make_combo(parent, values, display_map, current):
    display_vals = [display_map.get(v, v) if display_map else v for v in values]
    cur = display_map.get(current, current) if display_map else current
    if cur not in display_vals and display_vals:
        cur = display_vals[0]
    var = tk.StringVar(value=cur)
    var.trace_add("write", schedule_save)
    cb = ttk.Combobox(parent, textvariable=var, values=display_vals,
                       state="readonly", width=28, font=(FONT, 12))
    cb.pack(anchor="w", padx=20, pady=(0, 4))
    return var, display_map, cb

# Hotkey
field_label(sf, "Hotkey")
hotkey_var, hotkey_map, _ = make_combo(
    sf, list(hotkeys.keys()), hotkeys,
    cfg.get("hotkey", "fn" if is_mac else "Key.alt_r"))
sep(sf)

# Model (only downloaded models)
field_label(sf, "Model")
model_frame = tk.Frame(sf, bg=BG)
model_frame.pack(fill="x")
downloaded = get_downloaded()
available = [m for m in models if m in downloaded] or models[:1]
cur_model = cfg.get("model", "small")
if cur_model not in available:
    cur_model = available[0]
model_var, _, model_cb = make_combo(model_frame, available, {{}}, cur_model)
no_models_lbl = None
if not downloaded:
    no_models_lbl = tk.Label(sf, text="No models yet. Go to Models tab to download.",
                              font=(FONT, 10), bg=BG, fg=ORANGE)
    no_models_lbl.pack(anchor="w", padx=22, pady=(2, 0))
sep(sf)

def refresh_model_dropdown():
    \"\"\"Rebuild model dropdown to reflect newly downloaded models.\"\"\"
    global no_models_lbl
    dl = get_downloaded()
    avail = [m for m in models if m in dl] or models[:1]
    cur = model_var[0].get()
    if cur not in avail:
        cur = avail[0]
    model_cb.config(values=avail)
    model_var[0].set(cur)
    if no_models_lbl:
        if dl:
            no_models_lbl.pack_forget()
        else:
            no_models_lbl.pack(anchor="w", padx=22, pady=(2, 0))

# Language
field_label(sf, "Language")
lang_var, lang_map, _ = make_combo(sf, langs, lang_names, cfg.get("language", "auto"))
sep(sf)

# Toggles
paste_var = tk.BooleanVar(value=cfg.get("auto_paste", True))
paste_var.trace_add("write", schedule_save)
ttk.Checkbutton(sf, text="Auto-paste after transcription", variable=paste_var).pack(
    anchor="w", padx=18, pady=3)

gpu_var = tk.BooleanVar(value=cfg.get("gpu_enabled", True))
gpu_var.trace_add("write", schedule_save)
ttk.Checkbutton(sf, text="Use GPU (CUDA)", variable=gpu_var).pack(
    anchor="w", padx=18, pady=3)

# Output config on window close
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
mf = tk.Frame(root, bg=BG)
tab_frames["models"] = mf

m_canvas = tk.Canvas(mf, bg=BG, highlightthickness=0, bd=0)
m_inner = tk.Frame(m_canvas, bg=BG)
m_inner.bind("<Configure>", lambda e: m_canvas.configure(scrollregion=m_canvas.bbox("all")))
m_canvas.create_window((0, 0), window=m_inner, anchor="nw")
m_canvas.pack(fill="both", expand=True)

def _mw_models(event):
    m_canvas.yview_scroll(-1 * (event.delta // 120 or (1 if event.delta > 0 else -1)), "units")

def build_models():
    for w in m_inner.winfo_children():
        w.destroy()
    dl = get_downloaded()
    for i, name in enumerate(models):
        info = model_info.get(name, {{}})
        is_dl = name in dl

        row = tk.Frame(m_inner, bg=BG)
        row.pack(fill="x", padx=20, pady=(10, 0))

        left = tk.Frame(row, bg=BG)
        left.pack(side="left", fill="x", expand=True)

        title = name
        if info.get("recommended"):
            title += "  (recommended)"
        tk.Label(left, text=title, font=(FONT, 13, "bold"), bg=BG, fg=FG).pack(anchor="w")

        sp = info.get("speed", 0)
        qu = info.get("quality", 0)
        sz = info.get("size", "")
        meta = f"{{sz}}   Speed {{sp}}/5   Quality {{qu}}/5"
        tk.Label(left, text=meta, font=(FONT, 10), bg=BG, fg=FG2).pack(anchor="w", pady=(2, 0))

        right = tk.Frame(row, bg=BG)
        right.pack(side="right")

        if is_dl:
            tk.Label(right, text="Downloaded", font=(FONT, 10), bg=BG, fg=GREEN).pack(side="left", padx=(0, 10))
            def mk_del(m):
                def do_del():
                    subprocess.Popen([
                        sys.executable, "-c",
                        f"import sys; sys.path.insert(0, str(r'{{project_dir.parent}}')); "
                        f"from voice_input.transcriber import delete_model; delete_model('{{m}}')"
                    ])
                    root.after(600, build_models)
                return do_del
            RBtn(right, "Remove", mk_del(name), bg_color=CTRL, fg_color=RED,
                 hover=CTRL_HL, w=80, h=28, font_t=(FONT, 10)).pack(side="left")
        else:
            def mk_dl(m, btn_ref):
                def do_dl():
                    btn_ref[0].disable()
                    btn_ref[0].config_text("Loading...", fg=ORANGE)
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
            b = RBtn(right, "Download", lambda: None, bg_color=ACCENT, fg_color="white",
                     hover="#0070E0", w=100, h=28, font_t=(FONT, 10, "bold"))
            bref[0] = b
            b._cmd = mk_dl(name, bref)
            b.pack(side="left")

        if i < len(models) - 1:
            tk.Frame(m_inner, bg=SEP, height=1).pack(fill="x", padx=20, pady=(10, 0))

build_models()

# ════════════════════════════════════════
# TAB: History
# ════════════════════════════════════════
hf = tk.Frame(root, bg=BG)
tab_frames["history"] = hf

h_canvas = tk.Canvas(hf, bg=BG, highlightthickness=0, bd=0)
h_inner = tk.Frame(h_canvas, bg=BG)
h_inner.bind("<Configure>", lambda e: h_canvas.configure(scrollregion=h_canvas.bbox("all")))
h_canvas.create_window((0, 0), window=h_inner, anchor="nw")
h_canvas.pack(fill="both", expand=True)

def _mw_hist(event):
    h_canvas.yview_scroll(-1 * (event.delta // 120 or (1 if event.delta > 0 else -1)), "units")

def build_history():
    for w in h_inner.winfo_children():
        w.destroy()
    history = read_json(history_path, [])
    if not history:
        tk.Label(h_inner, text="No transcripts yet.", font=(FONT, 11),
                 bg=BG, fg=FG2).pack(anchor="w", padx=20, pady=20)
        return
    for i, entry in enumerate(history[:20]):
        stamp = entry.get("timestamp", "")
        text = entry.get("text", "")

        row = tk.Frame(h_inner, bg=BG)
        row.pack(fill="x", padx=20, pady=(10, 0))

        hdr = tk.Frame(row, bg=BG)
        hdr.pack(fill="x")

        time_s = stamp.split(" ")[-1] if " " in stamp else stamp
        date_s = stamp.split(" ")[0] if " " in stamp else ""
        tk.Label(hdr, text=time_s, font=(MONO, 10), bg=BG, fg=FG2).pack(side="left")
        tk.Label(hdr, text=date_s, font=(FONT, 9), bg=BG, fg=FG3).pack(side="left", padx=(8, 0))

        def mk_copy(t, btn_ref):
            def do_copy():
                if is_mac:
                    p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
                    p.communicate(t.encode("utf-8"))
                else:
                    root.clipboard_clear()
                    root.clipboard_append(t)
                btn_ref[0].config_text("Copied", fg=GREEN)
                root.after(1000, lambda: btn_ref[0].config_text("Copy", fg=FG2))
            return do_copy

        bref = [None]
        b = RBtn(hdr, "Copy", lambda: None, bg_color=CTRL, fg_color=FG2,
                 hover=CTRL_HL, w=65, h=24, r=7, font_t=(FONT, 10))
        bref[0] = b
        b._cmd = mk_copy(text, bref)
        b.pack(side="right")

        tk.Label(row, text=text, font=(FONT, 12), bg=BG, fg=FG,
                 anchor="w", justify="left", wraplength=480).pack(fill="x", pady=(4, 0))

        if i < min(len(history), 20) - 1:
            tk.Frame(h_inner, bg=SEP, height=1).pack(fill="x", padx=20, pady=(10, 0))

    h_canvas.update_idletasks()
    h_canvas.configure(scrollregion=h_canvas.bbox("all"))

# ── Mousewheel binding ──
def _mw_global(event):
    tab = current_tab.get()
    if tab == "history":
        h_canvas.yview_scroll(-1 * (event.delta // 120 or (1 if event.delta > 0 else -1)), "units")
    elif tab == "models":
        m_canvas.yview_scroll(-1 * (event.delta // 120 or (1 if event.delta > 0 else -1)), "units")
root.bind_all("<MouseWheel>", _mw_global)

# ── Status polling ──
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
        lbl, dot = "Listening", RED
    elif state == "transcribing":
        lbl, dot = "Transcribing...", ORANGE
    elif state in ("done", "hidden"):
        lbl = "Ready" if detail in ("Ready", "Settings saved", "Starting", "") else detail
        dot = GREEN
    else:
        lbl, dot = detail or "Ready", FG2

    status_dot.config(fg=dot)
    status_lbl.config(text=lbl)
    hotkey_lbl.config(text=hk)

    if current_tab.get() == "history":
        build_history()

    if sched:
        root.after(1500, refresh)

# ── Init ──
_init[0] = True
switch_tab("settings")
refresh()
root.mainloop()
"""
    )
