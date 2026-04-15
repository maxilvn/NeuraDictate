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
    config_path_json = json.dumps(str(config.CONFIG_PATH))
    logo_path_json = json.dumps(str(config.MODULE_DIR.parent / "logo.png"))

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
config_path = pathlib.Path(json.loads({config_path_json!r}))
logo_path = pathlib.Path(json.loads({logo_path_json!r}))

# ── Light palette ──
BG      = "#FFFFFF"
FG      = "#1C1C1E"
FG2     = "#6E6E73"
FG3     = "#AEAEB2"
ACCENT  = "#007AFF"
GREEN   = "#34C759"
RED     = "#FF3B30"
ORANGE  = "#FF9500"
CTRL    = "#F2F2F7"
CTRL_HL = "#E5E5EA"
SEP     = "#D1D1D6"

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
CARD    = "#F2F2F7"

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
                           highlightthickness=0, bd=0, cursor="")
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

# ── Logo header ──
header = tk.Frame(root, bg=BG)
header.pack(fill="x")
try:
    _logo_img = tk.PhotoImage(file=str(logo_path))
    sw = max(1, _logo_img.width() // 120)
    if sw > 1:
        _logo_img = _logo_img.subsample(sw, sw)
    logo_label = tk.Label(header, image=_logo_img, bg=BG)
    logo_label.image = _logo_img
    logo_label.pack(side="left", padx=(20, 2), pady=12)
except Exception:
    pass
tk.Label(header, text="Dictate", font=(FONT, 14), bg=BG, fg=FG).pack(
    side="left", pady=12)

# ── Tab bar (rounded pill buttons) ──
tab_bar = tk.Frame(root, bg=BG)
tab_bar.pack(fill="x", padx=20, pady=(12, 0))

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
    tab_frames[name].tkraise()
    for n in tab_canvases:
        draw_tab(n, n == name)
    if name == "settings":
        refresh_model_dropdown()

for tname in ["settings", "history", "models"]:
    c = tk.Canvas(tab_bar, width=TAB_W, height=TAB_H, bg=BG, highlightthickness=0, bd=0, cursor="")
    c.pack(side="left", padx=(0, 4))
    c.bind("<Button-1>", lambda e, n=tname: switch_tab(n))
    tab_canvases[tname] = c

# ── Status line (under tabs) ──
status_row = tk.Frame(root, bg=BG)
status_row.pack(fill="x", padx=20, pady=(6, 0))

status_dot = tk.Label(status_row, text="\\u25CF", font=(FONT, 8), bg=BG, fg=GREEN)
status_dot.pack(side="left")
status_lbl = tk.Label(status_row, text="Ready", font=(FONT, 10), bg=BG, fg=FG2)
status_lbl.pack(side="left", padx=(5, 0))
hotkey_lbl = tk.Label(status_row, text="", font=(MONO, 10), bg=BG, fg=FG3)
hotkey_lbl.pack(side="right")

# Start button (shown when backend is not running)
def _start_backend():
    start_script = str(project_dir.parent / "start.py")
    env = dict(__import__("os").environ, NEURADICTATE_HEADLESS="1")
    subprocess.Popen([sys.executable, start_script], env=env,
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                      start_new_session=True)
    start_btn.c.pack_forget()
    status_lbl.config(text="Starting...")

start_btn = RBtn(status_row, "\\u25B6  Start", _start_backend,
                  bg_color=ACCENT, fg_color="white", hover="#0070E0",
                  w=80, h=22, r=11, font_t=(FONT, 9))

sep(root)

content_area = tk.Frame(root, bg=BG)
content_area.pack(fill="both", expand=True, padx=0, pady=(6, 16))

# ════════════════════════════════════════
# AUTOSAVE
# ════════════════════════════════════════
_init = [False]

def build_cfg():
    rev_lg = dict(zip(lg_display, lg_keys))
    return {{
        "hotkey": _hk_value[0],
        "model": md_pill.get(),
        "language": rev_lg.get(lg_pill.get(), "auto"),
        "auto_paste": paste_toggle.get(),
    }}

def schedule_save(*_a):
    if not _init[0]:
        return
    try:
        new_cfg = build_cfg()
        config_path.write_text(json.dumps(new_cfg, indent=2, ensure_ascii=False), encoding="utf-8")
        status_lbl.config(text="Saved", fg=GREEN)
        root.after(1500, lambda: status_lbl.config(fg=FG2))
    except Exception:
        pass

# ════════════════════════════════════════
# TAB: Settings
# ════════════════════════════════════════
sf = tk.Frame(content_area, bg=BG)
sf.place(relx=0, rely=0, relwidth=1, relheight=1)
tab_frames["settings"] = sf

def field_label(parent, text):
    tk.Label(parent, text=text, font=(FONT, 10), bg=BG, fg=FG2).pack(
        anchor="w", padx=22, pady=(12, 4))

class PillSelect:
    \"\"\"Canvas pill with popup menu on click.\"\"\"
    PW, PH = 180, 26

    def __init__(self, parent, values, current, on_change=None):
        self._values = list(values)
        self._idx = self._values.index(current) if current in self._values else 0
        self._on_change = on_change
        self._parent = parent
        self.c = tk.Canvas(parent, width=self.PW, height=self.PH,
                           bg=BG, highlightthickness=0, bd=0, cursor="")
        self._draw()
        self.c.bind("<Button-1>", self._open_menu)

    def _draw(self):
        self.c.delete("all")
        rr(self.c, 0, 0, self.PW, self.PH, self.PH//2, fill=CTRL, outline="")
        self.c.create_text(14, self.PH//2, text=self._values[self._idx],
                           fill=FG, font=(FONT, 10), anchor="w")
        self.c.create_text(self.PW-14, self.PH//2, text="\\u25BE", fill=FG2, font=(FONT, 9))

    def _open_menu(self, event):
        menu = tk.Menu(self.c, tearoff=0, bg=CTRL, fg=FG, font=(FONT, 11),
                       activebackground=CTRL_HL, activeforeground=FG,
                       borderwidth=0, relief="flat")
        for i, val in enumerate(self._values):
            menu.add_command(label=val, command=lambda idx=i: self._select(idx))
        menu.tk_popup(self.c.winfo_rootx(), self.c.winfo_rooty() + self.PH)

    def _select(self, idx):
        self._idx = idx
        self._draw()
        if self._on_change:
            self._on_change()

    def get(self):
        return self._values[self._idx]

    def set_values(self, values):
        cur = self.get()
        self._values = list(values)
        self._idx = self._values.index(cur) if cur in self._values else 0
        self._draw()

    def pack(self, **kw):
        self.c.pack(**kw)

class Toggle:
    \"\"\"Canvas-based oval toggle switch using ovals for perfect roundness.\"\"\"
    W, H = 40, 22
    R = 11  # half height = perfect circle ends

    def __init__(self, parent, label, current, on_change=None):
        self._on = current
        self._on_change = on_change
        self.frame = tk.Frame(parent, bg=BG)
        self.c = tk.Canvas(self.frame, width=self.W, height=self.H,
                           bg=BG, highlightthickness=0, bd=0, cursor="")
        self.c.pack(side="left")
        tk.Label(self.frame, text=label, font=(FONT, 11), bg=BG, fg=FG).pack(side="left", padx=(8, 0))
        self._draw()
        self.c.bind("<Button-1>", self._toggle)

    def _draw(self):
        self.c.delete("all")
        bg = FG2 if self._on else SEP
        r = self.R
        # Left cap (semicircle)
        self.c.create_oval(0, 0, r*2, r*2, fill=bg, outline="")
        # Right cap (semicircle)
        self.c.create_oval(self.W-r*2, 0, self.W, r*2, fill=bg, outline="")
        # Middle rect
        self.c.create_rectangle(r, 0, self.W-r, self.H, fill=bg, outline="")
        # Thumb circle
        cx = self.W - r if self._on else r
        self.c.create_oval(cx-8, 3, cx+8, self.H-3, fill="white", outline="")

    def _toggle(self, _e=None):
        self._on = not self._on
        self._draw()
        if self._on_change:
            self._on_change()

    def get(self):
        return self._on

    def pack(self, **kw):
        self.frame.pack(**kw)

# Hotkey
field_label(sf, "Hotkey")
_hk_value = [cfg.get("hotkey", "fn" if is_mac else "Key.alt_r")]
_hk_name = [hotkeys.get(_hk_value[0], _hk_value[0])]

hk_row = tk.Frame(sf, bg=BG)
hk_row.pack(anchor="w", padx=20, pady=(0, 4))

# Current hotkey display pill
HK_W, HK_H = 120, 26
hk_canvas = tk.Canvas(hk_row, width=HK_W, height=HK_H, bg=BG, highlightthickness=0, bd=0)
hk_canvas.pack(side="left")

def _draw_hk():
    hk_canvas.delete("all")
    rr(hk_canvas, 0, 0, HK_W, HK_H, HK_H//2, fill=CTRL, outline="")
    hk_canvas.create_text(HK_W//2, HK_H//2, text=_hk_name[0], fill=FG, font=(FONT, 10))
_draw_hk()

# "Record" button — uses Quartz on macOS for correct key detection
def _start_record():
    hk_canvas.delete("all")
    rr(hk_canvas, 0, 0, HK_W, HK_H, HK_H//2, fill=ACCENT, outline="")
    hk_canvas.create_text(HK_W//2, HK_H//2, text="Press a key...", fill="white", font=(FONT, 10))

    def _record_thread():
        if is_mac:
            import Quartz
            # Reverse map: keycode -> (key_id, display_name)
            _CODE_MAP = {{
                63: ("fn", "Fn"),
                58: ("Key.alt_l", "Left Option"), 61: ("Key.alt_r", "Right Option"),
                55: ("Key.cmd_l", "Left Command"), 54: ("Key.cmd_r", "Right Command"),
                59: ("Key.ctrl_l", "Left Control"), 62: ("Key.ctrl_r", "Right Control"),
                56: ("Key.shift_l", "Left Shift"), 60: ("Key.shift_r", "Right Shift"),
                57: ("Key.caps_lock", "Caps Lock"),
                53: ("Key.esc", "Escape"),
                122: ("Key.f1","F1"), 120: ("Key.f2","F2"), 99: ("Key.f3","F3"),
                118: ("Key.f4","F4"), 96: ("Key.f5","F5"), 97: ("Key.f6","F6"),
                98: ("Key.f7","F7"), 100: ("Key.f8","F8"), 101: ("Key.f9","F9"),
                109: ("Key.f10","F10"), 103: ("Key.f11","F11"), 111: ("Key.f12","F12"),
                # Letters
                0: ("a","A"), 11: ("b","B"), 8: ("c","C"), 2: ("d","D"),
                14: ("e","E"), 3: ("f","F"), 5: ("g","G"), 4: ("h","H"),
                34: ("i","I"), 38: ("j","J"), 40: ("k","K"), 37: ("l","L"),
                46: ("m","M"), 45: ("n","N"), 31: ("o","O"), 35: ("p","P"),
                12: ("q","Q"), 15: ("r","R"), 1: ("s","S"), 17: ("t","T"),
                32: ("u","U"), 9: ("v","V"), 13: ("w","W"), 7: ("x","X"),
                16: ("y","Y"), 6: ("z","Z"),
                # Numbers
                18: ("1","1"), 19: ("2","2"), 20: ("3","3"), 21: ("4","4"),
                23: ("5","5"), 22: ("6","6"), 26: ("7","7"), 28: ("8","8"),
                25: ("9","9"), 29: ("0","0"),
                # Special
                49: ("space","Space"), 36: ("return","Return"), 48: ("tab","Tab"),
                51: ("delete","Delete"), 117: ("forward_delete","Fwd Delete"),
                123: ("left","Left"), 124: ("right","Right"),
                125: ("down","Down"), 126: ("up","Up"),
            }}
            detected = [None]
            def tap_callback(proxy, event_type, event, refcon):
                kc = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
                if kc in _CODE_MAP:
                    detected[0] = _CODE_MAP[kc]
                else:
                    detected[0] = (str(kc), f"Key {{kc}}")
                Quartz.CFRunLoopStop(Quartz.CFRunLoopGetCurrent())
                return event

            mask = (Quartz.CGEventMaskBit(Quartz.kCGEventFlagsChanged)
                    | Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown))
            tap = Quartz.CGEventTapCreate(
                Quartz.kCGSessionEventTap, Quartz.kCGHeadInsertEventTap,
                Quartz.kCGEventTapOptionListenOnly, mask, tap_callback, None)
            if tap:
                src = Quartz.CFMachPortCreateRunLoopSource(None, tap, 0)
                loop = Quartz.CFRunLoopGetCurrent()
                Quartz.CFRunLoopAddSource(loop, src, Quartz.kCFRunLoopDefaultMode)
                Quartz.CGEventTapEnable(tap, True)
                Quartz.CFRunLoopRun()
                Quartz.CGEventTapEnable(tap, False)

            if detected[0]:
                key_id, display = detected[0]
                root.after(0, lambda: _apply_key(key_id, display))
        else:
            # Windows: use pynput
            from pynput import keyboard
            _KEY_NAMES = {{
                keyboard.Key.alt_l: ("Key.alt_l", "Left Alt"),
                keyboard.Key.alt_r: ("Key.alt_r", "Right Alt"),
                keyboard.Key.ctrl_l: ("Key.ctrl_l", "Left Ctrl"),
                keyboard.Key.ctrl_r: ("Key.ctrl_r", "Right Ctrl"),
                keyboard.Key.shift_l: ("Key.shift_l", "Left Shift"),
                keyboard.Key.shift_r: ("Key.shift_r", "Right Shift"),
                keyboard.Key.caps_lock: ("Key.caps_lock", "Caps Lock"),
                keyboard.Key.esc: ("Key.esc", "Escape"),
                keyboard.Key.space: ("space", "Space"),
                keyboard.Key.enter: ("return", "Return"),
                keyboard.Key.tab: ("tab", "Tab"),
                keyboard.Key.backspace: ("delete", "Delete"),
                keyboard.Key.f1: ("Key.f1","F1"), keyboard.Key.f2: ("Key.f2","F2"),
                keyboard.Key.f3: ("Key.f3","F3"), keyboard.Key.f4: ("Key.f4","F4"),
                keyboard.Key.f5: ("Key.f5","F5"), keyboard.Key.f6: ("Key.f6","F6"),
                keyboard.Key.f7: ("Key.f7","F7"), keyboard.Key.f8: ("Key.f8","F8"),
                keyboard.Key.f9: ("Key.f9","F9"), keyboard.Key.f10: ("Key.f10","F10"),
                keyboard.Key.f11: ("Key.f11","F11"), keyboard.Key.f12: ("Key.f12","F12"),
            }}
            detected = [None]
            def on_press(key):
                if key in _KEY_NAMES:
                    detected[0] = _KEY_NAMES[key]
                elif hasattr(key, 'char') and key.char:
                    detected[0] = (key.char, key.char.upper())
                else:
                    s = str(key).replace("Key.", "")
                    detected[0] = (str(key), s.replace("_", " ").title())
                return False  # stops listener
            with keyboard.Listener(on_press=on_press) as listener:
                listener.join()
            if detected[0]:
                key_id, display = detected[0]
                root.after(0, lambda: _apply_key(key_id, display))

    def _apply_key(key_id, display):
        if key_id not in hotkeys:
            hotkeys[key_id] = display
        _hk_value[0] = key_id
        _hk_name[0] = display
        _draw_hk()
        schedule_save()

    threading.Thread(target=_record_thread, daemon=True).start()

rec_btn = RBtn(hk_row, "Set new", _start_record, bg_color=CTRL, fg_color=FG2,
               hover=CTRL_HL, w=75, h=26, font_t=(FONT, 10))
rec_btn.pack(side="left", padx=(8, 0))
sep(sf)

# Model (only downloaded)
field_label(sf, "Model")
downloaded = get_downloaded()
available = [m for m in models if m in downloaded] or models[:1]
cur_model = cfg.get("model", "small")
if cur_model not in available:
    cur_model = available[0]
md_pill = PillSelect(sf, available, cur_model, on_change=schedule_save)
md_pill.pack(anchor="w", padx=20, pady=(0, 4))
no_models_lbl = None
if not downloaded:
    no_models_lbl = tk.Label(sf, text="No models yet. Go to Models tab to download.",
                              font=(FONT, 10), bg=BG, fg=ORANGE)
    no_models_lbl.pack(anchor="w", padx=22, pady=(2, 0))
sep(sf)

def refresh_model_dropdown():
    dl = get_downloaded()
    avail = [m for m in models if m in dl] or models[:1]
    md_pill.set_values(avail)
    if no_models_lbl:
        if dl:
            no_models_lbl.pack_forget()

# Language
field_label(sf, "Language")
lg_display = ["Auto", "Deutsch", "English (translate)", "Français", "Español"]
lg_keys = ["auto", "de", "en", "fr", "es"]
lg_map = dict(zip(lg_keys, lg_display))
lg_cur = lg_map.get(cfg.get("language", "auto"), "Auto (Deutsch)")
lg_pill = PillSelect(sf, lg_display, lg_cur, on_change=schedule_save)
lg_pill.pack(anchor="w", padx=20, pady=(0, 4))
sep(sf)

# Toggles
paste_toggle = Toggle(sf, "Auto-paste after transcription",
                       cfg.get("auto_paste", True), on_change=schedule_save)
paste_toggle.pack(anchor="w", padx=20, pady=6)

# Output config on window close
def on_close():
    result = build_cfg()
    print(json.dumps(result))
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)

# ════════════════════════════════════════
# TAB: Models
# ════════════════════════════════════════
mf = tk.Frame(content_area, bg=BG)
mf.place(relx=0, rely=0, relwidth=1, relheight=1)
tab_frames["models"] = mf

m_canvas = tk.Canvas(mf, bg=BG, highlightthickness=0, bd=0)
m_inner = tk.Frame(m_canvas, bg=BG)
m_inner.bind("<Configure>", lambda e: m_canvas.configure(scrollregion=m_canvas.bbox("all")))
m_canvas.create_window((0, 0), window=m_inner, anchor="nw")
m_canvas.pack(fill="both", expand=True)

def _mw_models(event):
    m_canvas.yview_scroll((-1 if event.delta > 0 else 1) if is_mac else (-event.delta // 120), "units")

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
            def mk_del(m):
                def do_del():
                    subprocess.Popen([
                        sys.executable, "-c",
                        f"import sys; sys.path.insert(0, str(r'{{project_dir.parent}}')); "
                        f"from voice_input.transcriber import delete_model; delete_model('{{m}}')"
                    ])
                    root.after(600, build_models)
                return do_del
            RBtn(right, "Remove", mk_del(name), bg_color=CTRL, fg_color=FG2,
                 hover=CTRL_HL, w=80, h=28, font_t=(FONT, 10)).pack(side="left")
        else:
            def mk_dl(m, btn_ref):
                def do_dl():
                    btn_ref[0].disable()
                    btn_ref[0].config_text("Downloading...", fg=ORANGE)
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
            b = RBtn(right, "Download", lambda: None, bg_color=CTRL, fg_color=FG,
                     hover=CTRL_HL, w=100, h=28, font_t=(FONT, 10))
            bref[0] = b
            b._cmd = mk_dl(name, bref)
            b.pack(side="left")

        if i < len(models) - 1:
            tk.Frame(m_inner, bg=SEP, height=1).pack(fill="x", padx=20, pady=(10, 0))

build_models()

# ════════════════════════════════════════
# TAB: History
# ════════════════════════════════════════
hf = tk.Frame(content_area, bg=BG)
hf.place(relx=0, rely=0, relwidth=1, relheight=1)
tab_frames["history"] = hf

h_canvas = tk.Canvas(hf, bg=BG, highlightthickness=0, bd=0)
h_inner = tk.Frame(h_canvas, bg=BG)
h_inner.bind("<Configure>", lambda e: h_canvas.configure(scrollregion=h_canvas.bbox("all")))
h_canvas.create_window((0, 0), window=h_inner, anchor="nw")
h_canvas.pack(fill="both", expand=True)

def _mw_hist(event):
    h_canvas.yview_scroll((-1 if event.delta > 0 else 1) if is_mac else (-event.delta // 120), "units")

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

        # Card with rounded background via Canvas
        card_w = 500
        text_font = (FONT, 12)
        # Estimate card height based on text
        approx_lines = max(1, len(text) // 50 + 1)
        card_h = 56 + approx_lines * 18

        card_canvas = tk.Canvas(h_inner, width=card_w, height=card_h,
                                 bg=BG, highlightthickness=0, bd=0)
        card_canvas.pack(anchor="w", padx=16, pady=(6, 0))

        rr(card_canvas, 0, 0, card_w, card_h, 16, fill=CARD, outline="")

        time_s = stamp.split(" ")[-1] if " " in stamp else stamp
        date_s = stamp.split(" ")[0] if " " in stamp else ""
        card_canvas.create_text(14, 14, text=f"{{time_s}}  {{date_s}}",
                                 fill=FG2, font=(MONO, 9), anchor="w")

        card_canvas.create_text(14, 36, text=text, fill=FG, font=text_font,
                                 anchor="nw", width=card_w - 90)

        # Copy button — pill shaped, vertically centered
        bw, bh = 52, 22
        bx = card_w - bw - 14
        by = (card_h - bh) // 2
        rr(card_canvas, bx, by, bx+bw, by+bh, bh//2, fill=CTRL_HL, outline="", tags="copybg")
        card_canvas.create_text(bx+bw//2, by+bh//2, text="Copy", fill=FG2,
                                 font=(FONT, 9), tags="copytxt")

        def mk_copy(t, cv):
            def do_copy(e=None):
                if is_mac:
                    p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
                    p.communicate(t.encode("utf-8"))
                else:
                    root.clipboard_clear()
                    root.clipboard_append(t)
                cv.delete("copytxt")
                # Recalc center since bx/by are closure-captured per card
                _bx, _bh2 = bx, by
                cv.create_text(_bx+bw//2, _bh2+bh//2, text="Copied", fill=GREEN,
                                font=(FONT, 9), tags="copytxt")
                root.after(1000, lambda: [cv.delete("copytxt"),
                    cv.create_text(_bx+bw//2, _bh2+bh//2, text="Copy", fill=FG2,
                                    font=(FONT, 9), tags="copytxt")])
            return do_copy

        card_canvas.tag_bind("copybg", "<Button-1>", mk_copy(text, card_canvas))
        card_canvas.tag_bind("copytxt", "<Button-1>", mk_copy(text, card_canvas))

    h_canvas.update_idletasks()
    h_canvas.configure(scrollregion=h_canvas.bbox("all"))

# ── Mousewheel binding ──
def _mw_global(event):
    tab = current_tab.get()
    if tab == "history":
        h_canvas.yview_scroll((-1 if event.delta > 0 else 1) if is_mac else (-event.delta // 120), "units")
    elif tab == "models":
        m_canvas.yview_scroll((-1 if event.delta > 0 else 1) if is_mac else (-event.delta // 120), "units")
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
        lbl, dot = "Listening", GREEN
    elif state == "transcribing":
        lbl, dot = "Transcribing...", FG
    elif state in ("done", "hidden"):
        lbl = "Ready" if detail in ("Ready", "Settings saved", "Starting", "") else detail
        dot = GREEN
    else:
        lbl, dot = detail or "Ready", FG2

    # Check if backend is running (status updated within last 10s)
    import time as _time
    backend_alive = False
    try:
        if status_path.exists():
            age = _time.time() - status_path.stat().st_mtime
            backend_alive = age < 10
    except Exception:
        pass

    if not backend_alive:
        status_dot.config(text="\\u25CF", fg=RED, font=(FONT, 8))
        status_lbl.config(text="Stopped")
        start_btn.c.pack(side="right")
        hotkey_lbl.config(text="")
    else:
        start_btn.c.pack_forget()
        if state == "transcribing":
            status_dot.config(text="N", fg=FG, font=(FONT, 9, "bold"))
        else:
            status_dot.config(text="\\u25CF", fg=dot, font=(FONT, 8))
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
