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

        # ── Apple-like palette ──
        BG       = "#1C1C1E"
        SURFACE  = "#2C2C2E"
        SURFACE2 = "#3A3A3C"
        FG       = "#F5F5F7"
        FG2      = "#A1A1A6"
        ACCENT   = "#0A84FF"
        GREEN    = "#30D158"
        RED      = "#FF453A"
        ORANGE   = "#FF9F0A"
        BORDER   = "#38383A"
        HOVER    = "#48484A"

        FONT     = "SF Pro Display" if is_mac else "Segoe UI"
        MONO     = "SF Mono" if is_mac else "Consolas"

        root = tk.Tk()
        root.title(app_name)
        root.configure(bg=BG)
        root.resizable(True, True)
        root.minsize(520, 580)
        root.attributes("-topmost", True)
        root.geometry("600x720")

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

        # ── Tab bar ──
        tab_bar = tk.Frame(root, bg=BG)
        tab_bar.pack(fill="x", padx=24, pady=(20, 0))

        current_tab = tk.StringVar(value="settings")
        tab_frames = {{}}
        tab_buttons = {{}}

        def switch_tab(name):
            current_tab.set(name)
            for n, f in tab_frames.items():
                f.pack_forget()
            tab_frames[name].pack(fill="both", expand=True, padx=24, pady=(16, 20))
            for n, b in tab_buttons.items():
                if n == name:
                    b.config(fg=FG, bg=SURFACE2)
                else:
                    b.config(fg=FG2, bg=BG)

        for tab_name, tab_label in [("settings", "Settings"), ("models", "Models"), ("history", "History")]:
            btn = tk.Button(
                tab_bar, text=tab_label, font=(FONT, 12, "bold"),
                bg=BG, fg=FG2, relief="flat", bd=0, padx=16, pady=6,
                activebackground=SURFACE2, activeforeground=FG,
                command=lambda n=tab_name: switch_tab(n),
            )
            btn.pack(side="left", padx=(0, 4))
            tab_buttons[tab_name] = btn

        # Status line under tabs
        status_line = tk.Frame(root, bg=BG)
        status_line.pack(fill="x", padx=24, pady=(10, 0))

        status_dot = tk.Label(status_line, text="\\u25CF", font=(FONT, 8), bg=BG, fg=GREEN)
        status_dot.pack(side="left")
        status_text = tk.Label(status_line, text="Ready", font=(FONT, 11), bg=BG, fg=FG2)
        status_text.pack(side="left", padx=(6, 0))
        hotkey_text = tk.Label(status_line, text="", font=(FONT, 11), bg=BG, fg=FG2)
        hotkey_text.pack(side="right")

        # ════════════════════════════════════════
        # TAB: Settings
        # ════════════════════════════════════════
        settings_frame = tk.Frame(root, bg=BG)
        tab_frames["settings"] = settings_frame

        def make_section(parent, title):
            frame = tk.Frame(parent, bg=SURFACE)
            frame.pack(fill="x", pady=(0, 12))
            if title:
                tk.Label(frame, text=title, font=(FONT, 10), bg=SURFACE, fg=FG2).pack(
                    anchor="w", padx=16, pady=(12, 4))
            return frame

        def make_dropdown(parent, values, display_map, current):
            display_values = [display_map.get(v, v) if display_map else v for v in values]
            current_display = display_map.get(current, current) if display_map else current
            var = tk.StringVar(value=current_display)
            menu = tk.OptionMenu(parent, var, *display_values)
            menu.config(
                bg=SURFACE2, fg=FG, font=(FONT, 11),
                highlightthickness=0, relief="flat", width=22,
                activebackground=HOVER, activeforeground=FG, bd=0,
            )
            menu["menu"].config(
                bg=SURFACE2, fg=FG, font=(FONT, 11),
                activebackground=ACCENT, activeforeground="white",
                borderwidth=0,
            )
            menu.pack(anchor="w", padx=16, pady=(0, 12))
            return var, display_map

        def make_toggle(parent, label, current):
            var = tk.BooleanVar(value=current)
            cb = tk.Checkbutton(
                parent, text=label, variable=var,
                font=(FONT, 11), bg=SURFACE, fg=FG,
                selectcolor=SURFACE2, activebackground=SURFACE, activeforeground=FG,
                highlightthickness=0, bd=0,
            )
            cb.pack(anchor="w", padx=12, pady=4)
            return var

        # Hotkey section
        sec = make_section(settings_frame, "Hotkey")
        hotkey_var = make_dropdown(sec, list(hotkeys.keys()), hotkeys,
                                   cfg.get("hotkey", "fn" if is_mac else "Key.alt_r"))

        # Model section (only downloaded models)
        sec = make_section(settings_frame, "Model")
        downloaded = get_downloaded()
        available_for_use = [m for m in models if m in downloaded]
        if not available_for_use:
            available_for_use = ["small"]  # fallback
        model_var = make_dropdown(sec, available_for_use, {{}},
                                  cfg.get("model", "small") if cfg.get("model", "small") in available_for_use else available_for_use[0])
        no_models_label = None
        if len(downloaded) == 0:
            no_models_label = tk.Label(sec, text="No models downloaded. Go to Models tab.",
                                        font=(FONT, 10), bg=SURFACE, fg=ORANGE)
            no_models_label.pack(anchor="w", padx=16, pady=(0, 8))

        # Language section
        sec = make_section(settings_frame, "Language")
        lang_var = make_dropdown(sec, langs, lang_names, cfg.get("language", "auto"))

        # Toggles section
        sec = make_section(settings_frame, None)
        paste_var = make_toggle(sec, "Auto-paste after transcription", cfg.get("auto_paste", True))
        gpu_var = make_toggle(sec, "Use GPU (CUDA)", cfg.get("gpu_enabled", True))
        tk.Frame(sec, bg=SURFACE, height=8).pack()  # spacer

        # Save button
        btn_row = tk.Frame(settings_frame, bg=BG)
        btn_row.pack(fill="x", pady=(4, 0))

        def on_save():
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

        tk.Button(
            btn_row, text="Save", command=on_save,
            bg=ACCENT, fg="white", font=(FONT, 12, "bold"),
            relief="flat", padx=24, pady=8, bd=0,
            activebackground="#0070E0", activeforeground="white",
        ).pack(side="right")

        tk.Button(
            btn_row, text="Close", command=root.destroy,
            bg=SURFACE2, fg=FG, font=(FONT, 11),
            relief="flat", padx=16, pady=8, bd=0,
            activebackground=HOVER, activeforeground=FG,
        ).pack(side="right", padx=(0, 8))

        # ════════════════════════════════════════
        # TAB: Models
        # ════════════════════════════════════════
        models_frame = tk.Frame(root, bg=BG)
        tab_frames["models"] = models_frame

        models_list_frame = tk.Frame(models_frame, bg=BG)
        models_list_frame.pack(fill="both", expand=True)

        def build_model_cards():
            for w in models_list_frame.winfo_children():
                w.destroy()

            dl = get_downloaded()

            for name in models:
                info = model_info.get(name, {{}})
                is_dl = name in dl

                card = tk.Frame(models_list_frame, bg=SURFACE)
                card.pack(fill="x", pady=(0, 8))

                # Top row: name + size
                top = tk.Frame(card, bg=SURFACE)
                top.pack(fill="x", padx=16, pady=(12, 0))

                label = name
                if info.get("recommended"):
                    label += "  (recommended)"
                tk.Label(top, text=label, font=(FONT, 12, "bold"), bg=SURFACE, fg=FG).pack(side="left")
                tk.Label(top, text=info.get("size", ""), font=(FONT, 11), bg=SURFACE, fg=FG2).pack(side="right")

                # Bottom row: speed/quality + action button
                bot = tk.Frame(card, bg=SURFACE)
                bot.pack(fill="x", padx=16, pady=(4, 12))

                speed = info.get("speed", 0)
                quality = info.get("quality", 0)
                tk.Label(bot, text=f"Speed {{speed}}/5   Quality {{quality}}/5",
                         font=(FONT, 10), bg=SURFACE, fg=FG2).pack(side="left")

                if is_dl:
                    def make_delete(m):
                        def do_delete():
                            subprocess.Popen([
                                sys.executable, "-c",
                                f"import sys; sys.path.insert(0, str(r'{{project_dir.parent}}')); "
                                f"from voice_input.transcriber import delete_model; delete_model('{{m}}')"
                            ])
                            root.after(500, build_model_cards)
                        return do_delete
                    tk.Button(
                        bot, text="Delete", command=make_delete(name),
                        bg=SURFACE2, fg=RED, font=(FONT, 10),
                        relief="flat", padx=12, pady=2, bd=0,
                        activebackground=HOVER, activeforeground=RED,
                    ).pack(side="right")
                    tk.Label(bot, text="\\u2713 Downloaded", font=(FONT, 10), bg=SURFACE, fg=GREEN).pack(side="right", padx=(0, 12))
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
                        bot, text="Download",
                        bg=ACCENT, fg="white", font=(FONT, 10, "bold"),
                        relief="flat", padx=12, pady=2, bd=0,
                        activebackground="#0070E0", activeforeground="white",
                    )
                    btn_holder[0] = dl_btn
                    dl_btn.config(command=make_download(name, btn_holder))
                    dl_btn.pack(side="right")

        build_model_cards()

        # ════════════════════════════════════════
        # TAB: History
        # ════════════════════════════════════════
        history_frame = tk.Frame(root, bg=BG)
        tab_frames["history"] = history_frame

        canvas = tk.Canvas(history_frame, bg=BG, highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(history_frame, orient="vertical", command=canvas.yview)
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
                tk.Label(scroll_inner, text="No transcripts yet.", font=(FONT, 11),
                         bg=BG, fg=FG2).pack(anchor="w", pady=16)
                return

            for entry in history[:20]:
                stamp = entry.get("timestamp", "")
                text = entry.get("text", "")

                card = tk.Frame(scroll_inner, bg=SURFACE)
                card.pack(fill="x", pady=(0, 6))

                header = tk.Frame(card, bg=SURFACE)
                header.pack(fill="x", padx=14, pady=(10, 2))

                # Just time portion if available
                time_str = stamp.split(" ")[-1] if " " in stamp else stamp
                date_str = stamp.split(" ")[0] if " " in stamp else ""
                tk.Label(header, text=time_str, font=(MONO, 10), bg=SURFACE, fg=FG2).pack(side="left")
                tk.Label(header, text=date_str, font=(FONT, 9), bg=SURFACE, fg=SURFACE2).pack(side="left", padx=(8, 0))

                def make_copy(t, btn):
                    def do_copy():
                        if is_mac:
                            p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
                            p.communicate(t.encode("utf-8"))
                        else:
                            root.clipboard_clear()
                            root.clipboard_append(t)
                        btn.config(text="\\u2713", fg=GREEN)
                        root.after(1000, lambda: btn.config(text="Copy", fg=FG2))
                    return do_copy

                copy_btn = tk.Button(
                    header, text="Copy", font=(FONT, 9),
                    bg=SURFACE, fg=FG2, relief="flat", padx=8, pady=0, bd=0,
                    activebackground=HOVER, activeforeground=FG,
                )
                copy_btn.pack(side="right")
                copy_btn.config(command=make_copy(text, copy_btn))

                tk.Label(card, text=text, font=(FONT, 11), bg=SURFACE, fg=FG,
                         anchor="w", justify="left", wraplength=520).pack(
                    fill="x", padx=14, pady=(0, 10))

            canvas.update_idletasks()
            canvas.configure(scrollregion=canvas.bbox("all"))

        # ── Status polling ──
        def refresh_status(schedule=True):
            status = read_json(status_path, {{}})
            state = status.get("state", "hidden")
            detail = status.get("detail", "Ready")
            hotkey = status.get("hotkey", "")

            if not status.get("active", True):
                label = "Paused"
                dot_color = ORANGE
            elif state == "downloading":
                label = detail
                dot_color = ORANGE
            elif state == "loading":
                label = detail
                dot_color = ACCENT
            elif state == "listening":
                label = "Listening"
                dot_color = RED
            elif state == "transcribing":
                label = "Transcribing"
                dot_color = ORANGE
            elif state in ("done", "hidden"):
                label = "Ready" if detail in ("Ready", "Settings saved", "Starting") else detail
                dot_color = GREEN
            else:
                label = detail or state.replace("_", " ").title()
                dot_color = FG2

            status_dot.config(fg=dot_color)
            status_text.config(text=label)
            if hotkey:
                hotkey_text.config(text=f"\\u2318 {{hotkey}}" if is_mac else f"{{hotkey}}")

            # Refresh history if on that tab
            if current_tab.get() == "history":
                build_history_cards()

            if schedule:
                root.after(1200, refresh_status)

        # ── Init ──
        switch_tab("settings")
        refresh_status()
        root.mainloop()
        """
    )
