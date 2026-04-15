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

    return textwrap.dedent(
        f"""\
        import json
        import pathlib
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

        BG = "#161616"
        PANEL = "#1E1E1E"
        PANEL_ALT = "#252525"
        FIELD_BG = "#2B2B2B"
        FG = "#ECECEC"
        MUTED = "#9A9A9A"
        ACCENT = "#43A047"
        BORDER = "#363636"

        root = tk.Tk()
        root.title(app_name)
        root.configure(bg=BG)
        root.resizable(True, True)
        root.minsize(560, 620)
        root.attributes("-topmost", True)
        root.geometry("680x820")

        root.update_idletasks()
        w = root.winfo_width()
        h = root.winfo_height()
        x = (root.winfo_screenwidth() - w) // 2
        y = (root.winfo_screenheight() - h) // 2
        root.geometry(f"{{w}}x{{h}}+{{x}}+{{y}}")

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

        def set_text(widget, value):
            widget.config(state="normal")
            widget.delete("1.0", "end")
            widget.insert("1.0", value.strip())
            widget.config(state="disabled")

        def get_downloaded():
            downloaded = []
            if model_dir.exists():
                for name in models:
                    for entry in model_dir.iterdir():
                        if entry.is_dir() and name in entry.name:
                            downloaded.append(name)
                            break
            return downloaded

        downloaded = get_downloaded()

        model_display = {{}}
        for m in models:
            label = m
            if m in downloaded:
                label += "  [downloaded]"
            if model_info.get(m, {{}}).get("recommended"):
                label += "  (recommended)"
            model_display[m] = label

        title = tk.Label(
            root,
            text=app_name,
            font=("Helvetica", 20, "bold"),
            bg=BG,
            fg=FG,
        )
        title.pack(anchor="w", padx=20, pady=(18, 4))

        subtitle = tk.Label(
            root,
            text="Background dictation control panel",
            font=("Helvetica", 10),
            bg=BG,
            fg=MUTED,
        )
        subtitle.pack(anchor="w", padx=20, pady=(0, 14))

        status_card = tk.Frame(root, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        status_card.pack(fill="x", padx=20)

        status_title = tk.Label(status_card, text="Status", font=("Helvetica", 11, "bold"), bg=PANEL, fg=FG)
        status_title.grid(row=0, column=0, sticky="w", padx=16, pady=(14, 4))

        status_var = tk.StringVar(value="Starting")
        status_label = tk.Label(status_card, textvariable=status_var, font=("Helvetica", 15, "bold"), bg=PANEL, fg=FG)
        status_label.grid(row=1, column=0, sticky="w", padx=16)

        detail_var = tk.StringVar(value="")
        detail_label = tk.Label(status_card, textvariable=detail_var, font=("Helvetica", 11), bg=PANEL, fg=MUTED)
        detail_label.grid(row=2, column=0, sticky="w", padx=16, pady=(4, 2))

        updated_var = tk.StringVar(value="")
        updated_label = tk.Label(status_card, textvariable=updated_var, font=("Helvetica", 9), bg=PANEL, fg=MUTED)
        updated_label.grid(row=3, column=0, sticky="w", padx=16, pady=(0, 14))

        settings_card = tk.Frame(root, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        settings_card.pack(fill="x", padx=20, pady=(14, 0))

        tk.Label(settings_card, text="Settings", font=("Helvetica", 11, "bold"), bg=PANEL, fg=FG).grid(
            row=0, column=0, sticky="w", padx=16, pady=(14, 8), columnspan=2
        )

        def add_dropdown(parent, label, values, display_map, current, row):
            tk.Label(parent, text=label, font=("Helvetica", 10), bg=PANEL, fg=MUTED).grid(
                row=row, column=0, sticky="w", padx=16, pady=(8, 2), columnspan=2
            )
            display_values = [display_map.get(v, v) if display_map else v for v in values]
            current_display = display_map.get(current, current) if display_map else current
            var = tk.StringVar(value=current_display)
            menu = tk.OptionMenu(parent, var, *display_values)
            menu.config(
                bg=FIELD_BG,
                fg=FG,
                font=("Helvetica", 10),
                highlightthickness=0,
                relief="flat",
                width=24,
                activebackground="#3D3D3D",
                activeforeground=FG,
            )
            menu["menu"].config(bg=FIELD_BG, fg=FG, font=("Helvetica", 10), activebackground=ACCENT, activeforeground="white")
            menu.grid(row=row + 1, column=0, sticky="w", padx=16, pady=(0, 4), columnspan=2)
            return var, display_map

        def add_checkbox(parent, label, current, row):
            var = tk.BooleanVar(value=current)
            cb = tk.Checkbutton(
                parent,
                text=label,
                variable=var,
                font=("Helvetica", 10),
                bg=PANEL,
                fg=FG,
                selectcolor=FIELD_BG,
                activebackground=PANEL,
                activeforeground=FG,
                highlightthickness=0,
            )
            cb.grid(row=row, column=0, sticky="w", padx=12, pady=4, columnspan=2)
            return var

        row = 1
        hotkey_var = add_dropdown(settings_card, "Hotkey", list(hotkeys.keys()), hotkeys, cfg.get("hotkey", "fn" if is_mac else "Key.alt_r"), row)
        row += 2

        model_var = add_dropdown(settings_card, "Model", models, model_display, cfg.get("model", "small"), row)
        model_row = row
        row += 2

        def show_model_info():
            popup = tk.Toplevel(root)
            popup.title("Model Comparison")
            popup.configure(bg=BG)
            popup.attributes("-topmost", True)
            popup.geometry("560x320")
            popup.resizable(False, False)

            popup.update_idletasks()
            pw = popup.winfo_width()
            ph = popup.winfo_height()
            px = (popup.winfo_screenwidth() - pw) // 2
            py = (popup.winfo_screenheight() - ph) // 2
            popup.geometry(f"{{pw}}x{{ph}}+{{px}}+{{py}}")

            header_frame = tk.Frame(popup, bg=PANEL)
            header_frame.pack(fill="x", padx=12, pady=(12, 0))
            headers = ["Model", "Size", "Speed", "Quality", "Status"]
            col_widths = [16, 8, 10, 10, 12]
            for ci, (htext, cw) in enumerate(zip(headers, col_widths)):
                tk.Label(
                    header_frame, text=htext, font=("Helvetica", 10, "bold"),
                    bg=PANEL, fg=ACCENT, width=cw, anchor="w"
                ).grid(row=0, column=ci, padx=4, pady=6)

            table_frame = tk.Frame(popup, bg=BG)
            table_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

            for ri, name in enumerate(models):
                info = model_info.get(name, {{}})
                speed = info.get("speed", 0)
                quality = info.get("quality", 0)
                speed_stars = "\u2605" * speed + "\u2606" * (5 - speed)
                quality_stars = "\u2605" * quality + "\u2606" * (5 - quality)
                status = "Downloaded" if name in downloaded else "\u2014"
                row_bg = PANEL if ri % 2 == 0 else PANEL_ALT
                values = [name, info.get("size", "?"), speed_stars, quality_stars, status]
                for ci, (val, cw) in enumerate(zip(values, col_widths)):
                    fg_color = ACCENT if val == "Downloaded" else FG
                    tk.Label(
                        table_frame, text=val, font=("Helvetica", 10),
                        bg=row_bg, fg=fg_color, width=cw, anchor="w"
                    ).grid(row=ri, column=ci, padx=4, pady=3)

            tk.Button(
                popup, text="Close", command=popup.destroy,
                bg=FIELD_BG, fg=FG, font=("Helvetica", 10),
                relief="flat", padx=14, pady=4,
                activebackground="#3D3D3D", activeforeground=FG,
            ).pack(pady=(0, 12))

        info_btn = tk.Button(
            settings_card, text="i", command=show_model_info,
            bg=FIELD_BG, fg=ACCENT, font=("Helvetica", 10, "bold"),
            relief="flat", width=3, height=1,
            activebackground="#3D3D3D", activeforeground=ACCENT,
        )
        info_btn.grid(row=model_row + 1, column=1, sticky="e", padx=(0, 16))

        lang_var = add_dropdown(settings_card, "Language", langs, lang_names, cfg.get("language", "auto"), row)
        row += 2

        paste_var = add_checkbox(settings_card, "Auto-paste", cfg.get("auto_paste", True), row)
        row += 1
        gpu_var = add_checkbox(settings_card, "Use GPU (CUDA)", cfg.get("gpu_enabled", True), row)
        row += 1

        tk.Label(
            settings_card,
            text="Changes apply immediately after Save.",
            font=("Helvetica", 9),
            bg=PANEL,
            fg=MUTED,
        ).grid(row=row, column=0, sticky="w", padx=16, pady=(8, 14), columnspan=2)

        transcripts_card = tk.Frame(root, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        transcripts_card.pack(fill="both", expand=True, padx=20, pady=(14, 0))

        tk.Label(transcripts_card, text="Transcripts", font=("Helvetica", 11, "bold"), bg=PANEL, fg=FG).pack(
            anchor="w", padx=16, pady=(14, 6)
        )

        # Scrollable container using Canvas + Frame
        canvas = tk.Canvas(transcripts_card, bg=PANEL, highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(transcripts_card, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=PANEL)

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Mouse wheel scrolling for all platforms
        def _on_mousewheel(event):
            canvas.yview_scroll(-1 * (event.delta // 120 or (1 if event.delta > 0 else -1)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=(0, 14))

        def build_transcript_cards():
            for widget in scroll_frame.winfo_children():
                widget.destroy()

            history = read_json(history_path, [])
            if not history:
                tk.Label(scroll_frame, text="No transcripts yet.", font=("Helvetica", 10), bg=PANEL, fg=MUTED).pack(
                    anchor="w", padx=8, pady=8
                )
                return

            for entry in history[:20]:
                stamp = entry.get("timestamp", "")
                text = entry.get("text", "")

                card = tk.Frame(scroll_frame, bg=FIELD_BG, highlightbackground=BORDER, highlightthickness=1)
                card.pack(fill="x", padx=4, pady=(0, 6))

                header = tk.Frame(card, bg=FIELD_BG)
                header.pack(fill="x", padx=10, pady=(8, 2))

                tk.Label(header, text=stamp, font=("Helvetica", 9), bg=FIELD_BG, fg=MUTED).pack(side="left")

                def make_copy_fn(t, btn):
                    def copy_fn():
                        import subprocess as sp
                        if is_mac:
                            p = sp.Popen(["pbcopy"], stdin=sp.PIPE)
                            p.communicate(t.encode("utf-8"))
                        else:
                            root.clipboard_clear()
                            root.clipboard_append(t)
                        btn.config(text="Copied!", fg=ACCENT)
                        root.after(1200, lambda: btn.config(text="Copy", fg=MUTED))
                    return copy_fn

                copy_btn = tk.Button(
                    header,
                    text="Copy",
                    font=("Helvetica", 9),
                    bg=FIELD_BG,
                    fg=MUTED,
                    relief="flat",
                    padx=6,
                    pady=0,
                    activebackground="#3D3D3D",
                    activeforeground=FG,
                )
                copy_btn.pack(side="right")
                copy_btn.config(command=make_copy_fn(text, copy_btn))

                tk.Label(card, text=text, font=("Helvetica", 10), bg=FIELD_BG, fg=FG, anchor="w", justify="left", wraplength=580).pack(
                    fill="x", padx=10, pady=(0, 8)
                )

            canvas.update_idletasks()
            canvas.configure(scrollregion=canvas.bbox("all"))

        logs_card = tk.Frame(root, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        logs_card.pack(fill="both", expand=True, padx=20, pady=(14, 20))

        tk.Label(logs_card, text="Live Log", font=("Helvetica", 11, "bold"), bg=PANEL, fg=FG).pack(
            anchor="w", padx=16, pady=(14, 6)
        )
        log_box = scrolledtext.ScrolledText(
            logs_card,
            width=68,
            height=12,
            wrap="word",
            bg=FIELD_BG,
            fg=FG,
            insertbackground=FG,
            relief="flat",
            font=("Menlo", 10) if is_mac else ("Consolas", 10),
        )
        log_box.pack(fill="both", expand=True, padx=16)
        log_box.config(state="disabled")

        btn_frame = tk.Frame(logs_card, bg=PANEL)
        btn_frame.pack(anchor="e", pady=(10, 14), padx=16)

        def on_refresh():
            refresh_runtime(False)

        def on_save():
            result = dict(cfg)
            if hotkey_var is not None:
                reverse = {{v: k for k, v in hotkeys.items()}}
                result["hotkey"] = reverse.get(hotkey_var[0].get(), hotkey_var[0].get())
            raw_model = model_var[0].get()
            for m in models:
                if raw_model.startswith(m):
                    raw_model = m
                    break
            result["model"] = raw_model
            reverse_lang = {{v: k for k, v in lang_names.items()}}
            result["language"] = reverse_lang.get(lang_var[0].get(), lang_var[0].get())
            result["auto_paste"] = paste_var.get()
            result["gpu_enabled"] = gpu_var.get()
            print(json.dumps(result))
            root.destroy()

        tk.Button(
            btn_frame,
            text="Refresh",
            command=on_refresh,
            bg=FIELD_BG,
            fg=FG,
            font=("Helvetica", 10),
            relief="flat",
            padx=14,
            pady=6,
            activebackground="#3D3D3D",
            activeforeground=FG,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            btn_frame,
            text="Close",
            command=root.destroy,
            bg=FIELD_BG,
            fg=FG,
            font=("Helvetica", 10),
            relief="flat",
            padx=14,
            pady=6,
            activebackground="#3D3D3D",
            activeforeground=FG,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            btn_frame,
            text="Save",
            command=on_save,
            bg=ACCENT,
            fg="white",
            font=("Helvetica", 10, "bold"),
            relief="flat",
            padx=20,
            pady=6,
            activebackground="#388E3C",
            activeforeground="white",
        ).pack(side="left")

        def refresh_runtime(schedule_next=True):
            status = read_json(status_path, {{}})
            state = status.get("state", "hidden").replace("_", " ").title()
            if not status.get("active", True):
                state = "Paused"
            status_var.set(state)
            if status.get("state") == "downloading":
                status_label.config(fg="#FFA726")  # Orange
            elif status.get("state") == "loading":
                status_label.config(fg="#42A5F5")  # Blue
            else:
                status_label.config(fg=FG)
            detail_var.set(status.get("detail", ""))
            updated = status.get("updated_at", "")
            hotkey = status.get("hotkey", "")
            updated_var.set(f"Updated: {{updated}}    Hotkey: {{hotkey}}")

            build_transcript_cards()

            log_text = read_text(log_path, "")
            lines = log_text.splitlines()
            set_text(log_box, "\\n".join(lines[-80:]) if lines else "No log output yet.")

            if schedule_next:
                root.after(1200, refresh_runtime)

        refresh_runtime()
        root.mainloop()
        """
    )
