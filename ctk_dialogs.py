import customtkinter as ctk
from typing import Optional


def ctk_message(parent, title: str, message: str, kind: str = "info"):
    dlg = ctk.CTkToplevel(parent)
    dlg.title(title)
    dlg.transient(parent)
    dlg.grab_set()
    frm = ctk.CTkFrame(dlg)
    frm.pack(padx=12, pady=12, fill="both", expand=True)
    txt = ctk.CTkLabel(frm, text=message, anchor="center", justify="center", wraplength=420)
    txt.pack(fill="both", expand=True, pady=(0, 12))
    btn = ctk.CTkButton(frm, text="OK", width=80, command=dlg.destroy)
    try:
        if kind == "error":
            btn.configure(fg_color="#D32F2F")
        elif kind == "warning":
            btn.configure(fg_color="#D4A326")
        elif kind == "success":
            btn.configure(fg_color="#388E3C")
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
    ctk.CTkButton(btns, text="Confirmar", fg_color="#388E3C", command=on_yes).pack(
        side="left", padx=6
    )
    ctk.CTkButton(btns, text="Cancelar", fg_color="#A94444", command=on_no).pack(
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
