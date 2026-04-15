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
        root.geometry("680x760")

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

        model_var = add_dropdown(settings_card, "Model", models, {{}}, cfg.get("model", "large-v3-turbo"), row)
        row += 2
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
        transcripts_card.pack(fill="both", expand=False, padx=20, pady=(14, 0))

        tk.Label(transcripts_card, text="Last Transcript", font=("Helvetica", 11, "bold"), bg=PANEL, fg=FG).pack(
            anchor="w", padx=16, pady=(14, 6)
        )
        last_box = scrolledtext.ScrolledText(
            transcripts_card,
            width=68,
            height=4,
            wrap="word",
            bg=FIELD_BG,
            fg=FG,
            insertbackground=FG,
            relief="flat",
            font=("Helvetica", 10),
        )
        last_box.pack(fill="x", padx=16)
        last_box.config(state="disabled")

        tk.Label(transcripts_card, text="Recent History", font=("Helvetica", 11, "bold"), bg=PANEL, fg=FG).pack(
            anchor="w", padx=16, pady=(12, 6)
        )
        history_box = scrolledtext.ScrolledText(
            transcripts_card,
            width=68,
            height=6,
            wrap="word",
            bg=FIELD_BG,
            fg=FG,
            insertbackground=FG,
            relief="flat",
            font=("Helvetica", 10),
        )
        history_box.pack(fill="x", padx=16, pady=(0, 14))
        history_box.config(state="disabled")

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
            result["model"] = model_var[0].get()
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
            detail_var.set(status.get("detail", ""))
            updated = status.get("updated_at", "")
            hotkey = status.get("hotkey", "")
            updated_var.set(f"Updated: {{updated}}    Hotkey: {{hotkey}}")

            last_text = read_text(last_path, "No transcript yet.")
            set_text(last_box, last_text or "No transcript yet.")

            history = read_json(history_path, [])
            history_lines = []
            for entry in history[:8]:
                stamp = entry.get("timestamp", "")
                text = entry.get("text", "")
                history_lines.append(f"[{{stamp}}]\\n{{text}}")
            set_text(history_box, "\\n\\n".join(history_lines) if history_lines else "No history yet.")

            log_text = read_text(log_path, "")
            lines = log_text.splitlines()
            set_text(log_box, "\\n".join(lines[-80:]) if lines else "No log output yet.")

            if schedule_next:
                root.after(1200, refresh_runtime)

        refresh_runtime()
        root.mainloop()
        """
    )
