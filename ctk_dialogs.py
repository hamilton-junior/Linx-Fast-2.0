import customtkinter as ctk
from typing import Optional


def ctk_message(parent, title: str, message: str, kind: str = "info"):
    dlg = ctk.CTkToplevel(parent)
    dlg.title(title)
    dlg.transient(parent)
    dlg.grab_set()
    # register with theme manager if parent exposes one so theme changes propagate
    try:
        if parent and hasattr(parent, "theme_manager"):
            try:
                parent.theme_manager.register_window(dlg)
            except Exception:
                pass
    except Exception:
        pass
    frm = ctk.CTkFrame(dlg)
    frm.pack(padx=12, pady=12, fill="both", expand=True)
    txt = ctk.CTkLabel(frm, text=message, anchor="center", justify="center", wraplength=420)
    txt.pack(fill="both", expand=True, pady=(0, 12))
    btn = ctk.CTkButton(frm, text="OK", width=80, command=dlg.destroy)
    try:
        # Prefer theme-managed button colours when available; fall back to
        # semantic hard-coded colours only if ThemeManager is not present.
        color = None
        try:
            if parent and hasattr(parent, "theme_manager"):
                color = parent.theme_manager.get_theme_default_color(
                    ctk.CTkButton, "fg_color"
                )
        except Exception:
            color = None

        if not color:
            if kind == "error":
                color = "#D32F2F"
            elif kind == "warning":
                color = "#C08A00"
            elif kind == "success":
                color = "#388E3C"

        if color:
            try:
                btn.configure(fg_color=color)
            except Exception:
                pass
    except Exception:
        pass
    btn.pack()
    dlg.update_idletasks()
    try:
        dlg.minsize(dlg.winfo_reqwidth(), dlg.winfo_reqheight())
    except Exception:
        pass
    dlg.wait_window()


def ctk_ask_yes_no(parent, title: str, message: str) -> bool:
    dlg = ctk.CTkToplevel(parent)
    dlg.title(title)
    dlg.transient(parent)
    dlg.grab_set()
    try:
        if parent and hasattr(parent, "theme_manager"):
            try:
                parent.theme_manager.register_window(dlg)
            except Exception:
                pass
    except Exception:
        pass
    frm = ctk.CTkFrame(dlg)
    frm.pack(padx=12, pady=12, fill="both", expand=True)
    ctk.CTkLabel(frm, text=message, wraplength=420, anchor="center", justify="center").pack(
        fill="both", expand=True, pady=(0, 12)
    )
    res = {"value": False}

    def on_yes():
        res["value"] = True
        dlg.destroy()

    def on_no():
        res["value"] = False
        dlg.destroy()

    btns = ctk.CTkFrame(frm)
    btns.pack(pady=6)
    # Use theme defaults when the parent exposes a ThemeManager; otherwise
    # fall back to the previous semantic colours for confirm/cancel.
    try:
        success_color = None
        cancel_color = None
        if parent and hasattr(parent, "theme_manager"):
            try:
                success_color = parent.theme_manager.get_theme_default_color(
                    ctk.CTkButton, "fg_color"
                )
                cancel_color = success_color
            except Exception:
                success_color = None
                cancel_color = None
        if not success_color:
            success_color = "#388E3C"
        if not cancel_color:
            cancel_color = "#A94444"
    except Exception:
        success_color = "#388E3C"
        cancel_color = "#A94444"

    ctk.CTkButton(btns, text="Confirmar", fg_color=success_color, command=on_yes).pack(
        side="left", padx=6
    )
    ctk.CTkButton(btns, text="Cancelar", fg_color=cancel_color, command=on_no).pack(
        side="left", padx=6
    )
    dlg.update_idletasks()
    try:
        dlg.minsize(dlg.winfo_reqwidth(), dlg.winfo_reqheight())
    except Exception:
        pass
    dlg.wait_window()
    return bool(res.get("value"))


def ctk_ask_string(
    parent, title: str, prompt: str, initial: Optional[str] = None
) -> Optional[str]:
    dlg = ctk.CTkToplevel(parent)
    dlg.title(title)
    dlg.transient(parent)
    dlg.grab_set()
    try:
        if parent and hasattr(parent, "theme_manager"):
            try:
                parent.theme_manager.register_window(dlg)
            except Exception:
                pass
    except Exception:
        pass
    frm = ctk.CTkFrame(dlg)
    frm.pack(padx=12, pady=12, fill="both", expand=True)
    ctk.CTkLabel(frm, text=prompt, anchor="center", justify="center").pack(fill="x", pady=(0, 6))
    var = ctk.StringVar(value=initial or "")
    entry = ctk.CTkEntry(frm, textvariable=var)
    entry.pack(fill="x", pady=(0, 8))
    entry.focus()
    result = {"value": None}

    def on_ok():
        result["value"] = var.get()
        dlg.destroy()

    def on_cancel():
        result["value"] = None
        dlg.destroy()

    btns = ctk.CTkFrame(frm)
    btns.pack(pady=6)
    ctk.CTkButton(btns, text="OK", command=on_ok).pack(side="left", padx=6)
    ctk.CTkButton(btns, text="Cancelar", command=on_cancel).pack(side="left", padx=6)
    dlg.update_idletasks()
    try:
        dlg.minsize(dlg.winfo_reqwidth(), dlg.winfo_reqheight())
    except Exception:
        pass
    dlg.wait_window()
    return result["value"]
