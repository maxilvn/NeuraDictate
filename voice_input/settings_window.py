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
        import json
        import pathlib
        import subprocess
        import sys
        import threading
        import tkinter as tk
        from tkinter import scrolledtext

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

        # ── Clean dark palette ──
        BG       = "#1C1C1E"
        FG       = "#F5F5F7"
        FG2      = "#8E8E93"
        ACCENT   = "#0A84FF"
        GREEN    = "#30D158"
        RED      = "#FF453A"
        ORANGE   = "#FF9F0A"
        SEP      = "#38383A"
        CTRL_BG  = "#39393D"

        FONT     = "SF Pro Display" if is_mac else "Segoe UI"
        MONO     = "SF Mono" if is_mac else "Consolas"

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

        # ── Helpers ──
        def read_json(path, default):
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return default

        def read_text(path, default=""):
            try:
                return path.read_text(encoding="utf-8")
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

        def separator(parent):
            tk.Frame(parent, bg=SEP, height=1).pack(fill="x", padx=20, pady=8)

        # ── Tab bar ──
        tab_bar = tk.Frame(root, bg=BG)
        tab_bar.pack(fill="x", padx=20, pady=(16, 0))

        current_tab = tk.StringVar(value="settings")
        tab_frames = {{}}
        tab_buttons = {{}}

        def switch_tab(name):
            current_tab.set(name)
            for n, f in tab_frames.items():
                f.pack_forget()
            tab_frames[name].pack(fill="both", expand=True, padx=0, pady=(12, 16))
            for n, b in tab_buttons.items():
                if n == name:
                    b.config(fg=FG, font=(FONT, 12, "bold"))
                else:
                    b.config(fg=FG2, font=(FONT, 12))

        for tab_name, tab_label in [("settings", "Settings"), ("models", "Models"), ("history", "History")]:
            btn = tk.Button(
                tab_bar, text=tab_label, font=(FONT, 12),
                bg=BG, fg=FG2, relief="flat", bd=0, padx=14, pady=4,
                activebackground=BG, activeforeground=FG,
                command=lambda n=tab_name: switch_tab(n),
                cursor="hand2",
            )
            btn.pack(side="left", padx=(0, 6))
            tab_buttons[tab_name] = btn

        # ── Status line ──
        status_line = tk.Frame(root, bg=BG)
        status_line.pack(fill="x", padx=20, pady=(8, 0))

        status_dot = tk.Label(status_line, text="\\u25CF", font=(FONT, 7), bg=BG, fg=GREEN)
        status_dot.pack(side="left")
        status_text = tk.Label(status_line, text="Ready", font=(FONT, 10), bg=BG, fg=FG2)
        status_text.pack(side="left", padx=(5, 0))
        hotkey_text = tk.Label(status_line, text="", font=(MONO, 10), bg=BG, fg=FG2)
        hotkey_text.pack(side="right")

        tk.Frame(root, bg=SEP, height=1).pack(fill="x", padx=20, pady=(8, 0))

        # ════════════════════════════════════════
        # TAB: Settings
        # ════════════════════════════════════════
        settings_frame = tk.Frame(root, bg=BG)
        tab_frames["settings"] = settings_frame

        def field_label(parent, text):
            tk.Label(parent, text=text, font=(FONT, 10), bg=BG, fg=FG2).pack(
                anchor="w", padx=20, pady=(10, 4))

        _save_scheduled = [False]
        _init_done = [False]
        def schedule_autosave(*_args):
            if not _init_done[0]:
                return
            if not _save_scheduled[0]:
                _save_scheduled[0] = True
                root.after(300, do_autosave)

        def do_autosave():
            _save_scheduled[0] = False
            result = dict(cfg)
            reverse_hotkey = {{v: k for k, v in hotkeys.items()}}
            result["hotkey"] = reverse_hotkey.get(hotkey_var[0].get(), hotkey_var[0].get())
            result["model"] = model_var[0].get()
            reverse_lang = {{v: k for k, v in lang_names.items()}}
            result["language"] = reverse_lang.get(lang_var[0].get(), lang_var[0].get())
            result["auto_paste"] = paste_var.get()
            result["gpu_enabled"] = gpu_var.get()
            cfg.update(result)
            # Flash saved indicator
            status_text.config(text="Saved", fg=GREEN)
            root.after(1000, lambda: status_text.config(fg=FG2))

        def make_dropdown(parent, values, display_map, current):
            display_values = [display_map.get(v, v) if display_map else v for v in values]
            current_display = display_map.get(current, current) if display_map else current
            if current_display not in display_values and display_values:
                current_display = display_values[0]
            var = tk.StringVar(value=current_display)
            var.trace_add("write", schedule_autosave)
            menu = tk.OptionMenu(parent, var, *display_values)
            menu.config(
                bg=CTRL_BG, fg=FG, font=(FONT, 12),
                highlightthickness=0, relief="flat", width=26,
                activebackground="#4A4A4E", activeforeground=FG, bd=0,
                padx=8, pady=4,
            )
            menu["menu"].config(
                bg=CTRL_BG, fg=FG, font=(FONT, 12),
                activebackground=ACCENT, activeforeground="white",
                borderwidth=0, relief="flat",
            )
            menu.pack(anchor="w", padx=20, pady=(0, 2))
            return var, display_map

        def make_toggle(parent, label, current):
            var = tk.BooleanVar(value=current)
            var.trace_add("write", schedule_autosave)
            cb = tk.Checkbutton(
                parent, text=label, variable=var,
                font=(FONT, 12), bg=BG, fg=FG,
                selectcolor=CTRL_BG, activebackground=BG, activeforeground=FG,
                highlightthickness=0, bd=0,
            )
            cb.pack(anchor="w", padx=16, pady=3)
            return var

        # Hotkey
        field_label(settings_frame, "HOTKEY")
        hotkey_var = make_dropdown(settings_frame, list(hotkeys.keys()), hotkeys,
                                   cfg.get("hotkey", "fn" if is_mac else "Key.alt_r"))

        separator(settings_frame)

        # Model (only downloaded)
        field_label(settings_frame, "MODEL")
        downloaded = get_downloaded()
        available = [m for m in models if m in downloaded]
        if not available:
            available = models[:1]
        current_model = cfg.get("model", "small")
        if current_model not in available:
            current_model = available[0]
        model_var = make_dropdown(settings_frame, available, {{}}, current_model)
        if len(downloaded) == 0:
            tk.Label(settings_frame, text="No models yet \\u2014 download in Models tab",
                     font=(FONT, 10), bg=BG, fg=ORANGE).pack(anchor="w", padx=20, pady=(2, 0))

        separator(settings_frame)

        # Language
        field_label(settings_frame, "LANGUAGE")
        lang_var = make_dropdown(settings_frame, langs, lang_names, cfg.get("language", "auto"))

        separator(settings_frame)

        # Toggles
        paste_var = make_toggle(settings_frame, "Auto-paste after transcription", cfg.get("auto_paste", True))
        gpu_var = make_toggle(settings_frame, "Use GPU (CUDA)", cfg.get("gpu_enabled", True))

        # Output config on window close (autosave picks up changes live)
        def on_close():
            do_autosave()
            result = dict(cfg)
            reverse_hotkey = {{v: k for k, v in hotkeys.items()}}
            result["hotkey"] = reverse_hotkey.get(hotkey_var[0].get(), hotkey_var[0].get())
            result["model"] = model_var[0].get()
            reverse_lang = {{v: k for k, v in lang_names.items()}}
            result["language"] = reverse_lang.get(lang_var[0].get(), lang_var[0].get())
            result["auto_paste"] = paste_var.get()
            result["gpu_enabled"] = gpu_var.get()
            print(json.dumps(result))
            root.destroy()

        root.protocol("WM_DELETE_WINDOW", on_close)

        # ════════════════════════════════════════
        # TAB: Models
        # ════════════════════════════════════════
        models_frame = tk.Frame(root, bg=BG)
        tab_frames["models"] = models_frame

        models_scroll = tk.Canvas(models_frame, bg=BG, highlightthickness=0, bd=0)
        models_inner = tk.Frame(models_scroll, bg=BG)
        models_inner.bind("<Configure>", lambda e: models_scroll.configure(scrollregion=models_scroll.bbox("all")))
        models_scroll.create_window((0, 0), window=models_inner, anchor="nw")
        models_scroll.pack(fill="both", expand=True)

        def build_model_cards():
            for w in models_inner.winfo_children():
                w.destroy()

            dl = get_downloaded()

            for i, name in enumerate(models):
                info = model_info.get(name, {{}})
                is_dl = name in dl

                row = tk.Frame(models_inner, bg=BG)
                row.pack(fill="x", padx=20, pady=(0, 0))

                # Left side: name + info
                left = tk.Frame(row, bg=BG)
                left.pack(side="left", fill="x", expand=True, pady=10)

                title = name
                if info.get("recommended"):
                    title += "  \\u2605"
                tk.Label(left, text=title, font=(FONT, 13, "bold"), bg=BG, fg=FG).pack(anchor="w")

                speed = info.get("speed", 0)
                quality = info.get("quality", 0)
                size = info.get("size", "")
                meta = f"{{size}}  \\u00B7  Speed {{speed}}/5  \\u00B7  Quality {{quality}}/5"
                tk.Label(left, text=meta, font=(FONT, 10), bg=BG, fg=FG2).pack(anchor="w", pady=(1, 0))

                # Right side: status + button
                right = tk.Frame(row, bg=BG)
                right.pack(side="right", pady=10)

                if is_dl:
                    tk.Label(right, text="\\u2713", font=(FONT, 12), bg=BG, fg=GREEN).pack(side="left", padx=(0, 8))

                    def make_delete(m):
                        def do_delete():
                            subprocess.Popen([
                                sys.executable, "-c",
                                f"import sys; sys.path.insert(0, str(r'{{project_dir.parent}}')); "
                                f"from voice_input.transcriber import delete_model; delete_model('{{m}}')"
                            ])
                            root.after(600, build_model_cards)
                        return do_delete

                    tk.Button(
                        right, text="Remove", command=make_delete(name),
                        bg=BG, fg=RED, font=(FONT, 10),
                        relief="flat", padx=8, pady=2, bd=0,
                        activebackground=BG, activeforeground=RED,
                        cursor="hand2",
                    ).pack(side="left")
                else:
                    def make_download(m, btn_ref):
                        def do_download():
                            btn_ref[0].config(text="Downloading...", state="disabled", fg=ORANGE)
                            def run():
                                subprocess.run([
                                    sys.executable, "-c",
                                    f"import sys; sys.path.insert(0, str(r'{{project_dir.parent}}')); "
                                    f"from voice_input.transcriber import download_model; download_model('{{m}}')"
                                ])
                                root.after(0, build_model_cards)
                            threading.Thread(target=run, daemon=True).start()
                        return do_download

                    btn_holder = [None]
                    dl_btn = tk.Button(
                        right, text="Download",
                        bg=ACCENT, fg="white", font=(FONT, 10, "bold"),
                        relief="flat", padx=12, pady=4, bd=0,
                        activebackground="#0070E0", activeforeground="white",
                        cursor="hand2",
                    )
                    btn_holder[0] = dl_btn
                    dl_btn.config(command=make_download(name, btn_holder))
                    dl_btn.pack(side="left")

                # Separator between rows
                if i < len(models) - 1:
                    tk.Frame(models_inner, bg=SEP, height=1).pack(fill="x", padx=20)

        build_model_cards()

        # ════════════════════════════════════════
        # TAB: History
        # ════════════════════════════════════════
        history_frame = tk.Frame(root, bg=BG)
        tab_frames["history"] = history_frame

        canvas = tk.Canvas(history_frame, bg=BG, highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(history_frame, orient="vertical", command=canvas.yview,
                                  bg=BG, troughcolor=BG)
        scroll_inner = tk.Frame(canvas, bg=BG)

        scroll_inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def _on_mousewheel(event):
            canvas.yview_scroll(-1 * (event.delta // 120 or (1 if event.delta > 0 else -1)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        def build_history_cards():
            for w in scroll_inner.winfo_children():
                w.destroy()

            history = read_json(history_path, [])
            if not history:
                tk.Label(scroll_inner, text="No transcripts yet.",
                         font=(FONT, 12), bg=BG, fg=FG2).pack(anchor="w", padx=20, pady=20)
                return

            for i, entry in enumerate(history[:20]):
                stamp = entry.get("timestamp", "")
                text = entry.get("text", "")

                row = tk.Frame(scroll_inner, bg=BG)
                row.pack(fill="x", padx=20, pady=(10, 0))

                header = tk.Frame(row, bg=BG)
                header.pack(fill="x")

                time_str = stamp.split(" ")[-1] if " " in stamp else stamp
                date_str = stamp.split(" ")[0] if " " in stamp else ""
                tk.Label(header, text=time_str, font=(MONO, 10), bg=BG, fg=FG2).pack(side="left")
                tk.Label(header, text=date_str, font=(FONT, 10), bg=BG, fg=SEP).pack(side="left", padx=(8, 0))

                def make_copy(t, btn):
                    def do_copy():
                        if is_mac:
                            p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
                            p.communicate(t.encode("utf-8"))
                        else:
                            root.clipboard_clear()
                            root.clipboard_append(t)
                        btn.config(text="\\u2713 Copied", fg=GREEN)
                        root.after(1000, lambda: btn.config(text="Copy", fg=FG2))
                    return do_copy

                copy_btn = tk.Button(
                    header, text="Copy", font=(FONT, 10),
                    bg=BG, fg=FG2, relief="flat", padx=6, pady=0, bd=0,
                    activebackground=BG, activeforeground=FG,
                    cursor="hand2",
                )
                copy_btn.pack(side="right")
                copy_btn.config(command=make_copy(text, copy_btn))

                tk.Label(row, text=text, font=(FONT, 12), bg=BG, fg=FG,
                         anchor="w", justify="left", wraplength=480).pack(
                    fill="x", pady=(4, 0))

                if i < min(len(history), 20) - 1:
                    tk.Frame(scroll_inner, bg=SEP, height=1).pack(fill="x", padx=20, pady=(10, 0))

            canvas.update_idletasks()
            canvas.configure(scrollregion=canvas.bbox("all"))

        # ── Status polling ──
        def refresh_status(schedule=True):
            status = read_json(status_path, {{}})
            state = status.get("state", "hidden")
            detail = status.get("detail", "Ready")
            hk = status.get("hotkey", "")

            if not status.get("active", True):
                label, dot = "Paused", ORANGE
            elif state == "downloading":
                label, dot = detail, ORANGE
            elif state == "loading":
                label, dot = detail, ACCENT
            elif state == "listening":
                label, dot = "Listening", RED
            elif state == "transcribing":
                label, dot = "Transcribing", ORANGE
            elif state in ("done", "hidden"):
                label = "Ready" if detail in ("Ready", "Settings saved", "Starting", "") else detail
                dot = GREEN
            else:
                label, dot = detail or "Ready", FG2

            status_dot.config(fg=dot)
            status_text.config(text=label)
            hotkey_text.config(text=hk)

            if current_tab.get() == "history":
                build_history_cards()

            if schedule:
                root.after(1200, refresh_status)

        # ── Init ──
        _init_done[0] = True
        switch_tab("settings")
        refresh_status()
        root.mainloop()
        """
    )
