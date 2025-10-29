import customtkinter as ctk
import logging
import tkinter as tk
from typing import Optional

from logger_config import auto_log_functions

# Get the module logger
logger = logging.getLogger(__name__)


@auto_log_functions
class TemplateEditor(ctk.CTkToplevel):
    """A simple template editor dialog with a CTk-only placeholder picker.

    This file provides a lightweight, robust implementation of the editor used
    by the main window. It intentionally keeps the UI minimal while providing
    the placeholder picker (CTkScrollableFrame + CTkButton items), an
    autocomplete popup, and methods the rest of the app expects
    (load_template, save_template, refresh_placeholder_list, etc.).
    """

    def __init__(
        self,
        master,
        manager,
        get_placeholders_callback,
        current_template="Template Padrão",
    ):
        super().__init__(master)
        self.title("Editor de Templates")
        self._after_ids = set()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.geometry("860x540")
        self.transient(master)
        self.grab_set()

        # optional theme manager registration
        if hasattr(master, "theme_manager"):
            self.theme_manager = master.theme_manager
            try:
                self.theme_manager.register_window(self)
            except Exception:
                pass

        self.manager = manager
        self.get_placeholders = get_placeholders_callback
        self.template_names = self.manager.get_template_names()

        self.original_name = current_template
        self.template_var = ctk.StringVar(
            value=self.manager.meta.get_display_name(current_template)
        )

        # Top frame: template selector + controls
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(fill="x", padx=12, pady=8)

        ctk.CTkLabel(top_frame, text="Template:").pack(side="left", padx=(0, 8))
        display_names = self.manager.get_display_names()
        # calculate width to fit the longest template name (approx. 8px per char + padding)
        max_len = max((len(s) for s in display_names), default=20)
        dropdown_width = min(max_len * 8 + 80, 900)
        # keep colors/theme default so the selector follows the active theme
        self.dropdown = ctk.CTkComboBox(
            top_frame,
            values=display_names,
            variable=self.template_var,
            width=dropdown_width,
            command=self._on_dropdown_change,
        )
        self.dropdown.pack(side="left", padx=(0, 8))

        # action buttons: Save, Rename, Delete, Import (NocoDB)
        ctk.CTkButton(top_frame, text="Salvar", command=self.save_template).pack(
            side="right", padx=6
        )
        ctk.CTkButton(top_frame, text="Renomear", command=self.rename_template).pack(
            side="right", padx=6
        )
        ctk.CTkButton(top_frame, text="Excluir", command=self.delete_template).pack(
            side="right", padx=6
        )
        ctk.CTkButton(
            top_frame, text="Importar (NocoDB)", command=self.import_from_nocodb
        ).pack(side="right", padx=6)

        # Main paned area: editor and placeholder box
        paned = ctk.CTkFrame(self)
        paned.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # Editor (content box) - prefer CTkTextbox, fallback to tk.Text
        try:
            self.content_box = ctk.CTkTextbox(paned, width=600, height=380)
            self.content_box.pack(side="left", fill="both", expand=True, padx=(0, 8))
        except Exception:
            self.content_box = tk.Text(paned, width=60, height=24)
            self.content_box.pack(side="left", fill="both", expand=True, padx=(0, 8))

        # right side: placeholders + buttons (buttons anchored at bottom)
        right_frame = ctk.CTkFrame(paned, width=260)
        right_frame.pack(side="right", fill="both", expand=False)
        right_frame.grid_rowconfigure(0, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)

        # Label above the search box (user requested label above the search entry)
        ctk.CTkLabel(right_frame, text="Placeholders").grid(
            row=0, column=0, columnspan=2, sticky="nw", padx=8, pady=(4, 2)
        )

        # Filter/search entry for placeholders (immediately below the label)
        self._ph_search_var = ctk.StringVar()
        ph_search = ctk.CTkEntry(
            right_frame, placeholder_text="Filtrar...", textvariable=self._ph_search_var
        )
        ph_search.grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 4))
        ph_search.bind(
            "<KeyRelease>", lambda e: self.refresh_placeholder_list(self.get_content())
        )

        # placeholder container (scrollable) should expand and occupy all vertical space above the buttons
        # placeholder container (scrollable) should expand and occupy all vertical space above the buttons
        try:
            self.placeholder_container = ctk.CTkScrollableFrame(
                right_frame, width=240, height=320
            )
            self.placeholder_container.grid(
                row=2, column=0, columnspan=2, sticky="nsew", padx=8, pady=(0, 8)
            )
        except Exception:
            # fallback to a simple frame if CTkScrollableFrame isn't available
            self.placeholder_container = ctk.CTkFrame(right_frame)
            self.placeholder_container.grid(
                row=2, column=0, columnspan=2, sticky="nsew", padx=8, pady=(0, 8)
            )

        # make the placeholder area expand to use available vertical space so the list starts at the top
        try:
            right_frame.grid_rowconfigure(2, weight=1)
        except Exception:
            pass

        # internal state for interactive list
        self._placeholder_buttons = {}
        self.selected_placeholder = None

        # Buttons frame anchored at bottom
        btns = ctk.CTkFrame(right_frame)
        btns.grid(row=3, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 8))
        # left-aligned buttons for actions (these remain at the bottom)
        ctk.CTkButton(
            btns, text="Inserir Campo...", command=self.open_placeholder_picker
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btns, text="Autocomplete", command=self.show_autocomplete).pack(
            side="left"
        )

        # keyboard shortcuts (global within this toplevel)
        try:
            self.bind_all("<Control-s>", lambda e: self.save_template())
            self.bind_all("<Control-S>", lambda e: self.save_template())
            self.bind_all("<Control-r>", lambda e: self._rename_selected_placeholder())
            self.bind_all("<Control-R>", lambda e: self._rename_selected_placeholder())
            self.bind_all("<Control-space>", lambda e: self.show_autocomplete())
        except Exception:
            pass

    # --- CTk modal dialogs (replace tkinter.messagebox / simpledialog) ---
    def _ctk_message(self, title: str, message: str, kind: str = "info"):
        dlg = ctk.CTkToplevel(self)
        dlg.title(title)
        dlg.transient(self)
        dlg.grab_set()
        # simple layout
        frm = ctk.CTkFrame(dlg)
        frm.pack(padx=12, pady=12, fill="both", expand=True)
        txt = ctk.CTkLabel(
            frm, text=message, anchor="w", justify="left", wraplength=420
        )
        txt.pack(fill="both", expand=True, pady=(0, 12))
        btn = ctk.CTkButton(frm, text="OK", width=80, command=dlg.destroy)
        # visual hint for kind
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

    def _ctk_ask_yes_no(self, title: str, message: str) -> bool:
        dlg = ctk.CTkToplevel(self)
        dlg.title(title)
        dlg.transient(self)
        dlg.grab_set()
        frm = ctk.CTkFrame(dlg)
        frm.pack(padx=12, pady=12)
        ctk.CTkLabel(
            frm, text=message, wraplength=420, anchor="w", justify="left"
        ).pack(fill="both", expand=True, pady=(0, 12))
        res = {"value": False}

        def on_yes():
            res["value"] = True
            dlg.destroy()

        def on_no():
            res["value"] = False
            dlg.destroy()

        btns = ctk.CTkFrame(frm)
        btns.pack()
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

    def _ctk_ask_string(
        self, title: str, prompt: str, initial: Optional[str] = None
    ) -> Optional[str]:
        dlg = ctk.CTkToplevel(self)
        dlg.title(title)
        dlg.transient(self)
        dlg.grab_set()
        frm = ctk.CTkFrame(dlg)
        frm.pack(padx=12, pady=12, fill="both", expand=True)
        ctk.CTkLabel(frm, text=prompt, anchor="w").pack(fill="x", pady=(0, 6))
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
        btns.pack()
        ctk.CTkButton(btns, text="OK", command=on_ok).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Cancelar", command=on_cancel).pack(
            side="left", padx=6
        )
        dlg.update_idletasks()
        try:
            dlg.minsize(dlg.winfo_reqwidth(), dlg.winfo_reqheight())
        except Exception:
            pass
        dlg.wait_window()
        return result["value"]

        # Bindings
        try:
            # CTkTextbox has a widget-like bind
            self.content_box.bind(
                "<KeyRelease>",
                lambda e: self.refresh_placeholder_list(self.get_content()),
            )
        except Exception:
            # tk.Text binding
            self.content_box.bind(
                "<KeyRelease>",
                lambda e: self.refresh_placeholder_list(self.get_content()),
            )

        # ensure window has a reasonable minimum size and is resizable
        self.update_idletasks()
        try:
            self.minsize(self.winfo_reqwidth(), self.winfo_reqheight())
        except Exception:
            pass

        # be resizable
        try:
            self.resizable(True, True)
        except Exception:
            pass

        # load initial template
        self.load_template(self.original_name)

    def get_content(self):
        try:
            return self.content_box.get("1.0", "end")
        except Exception:
            # CTkTextbox uses same interface, but keep safe
            return self.content_box.get("1.0", "end")

    def get_real_name(self):
        return self.manager.meta.get_real_name(self.template_var.get())

    def load_template(self, name):
        content = self.manager.get_template(name)
        self.last_saved_content = content
        try:
            self.content_box.delete("1.0", "end")
            self.content_box.insert("1.0", content)
        except Exception:
            # generic fallback
            self.content_box.delete("1.0", "end")
            self.content_box.insert("1.0", content)
        self.refresh_placeholder_list(content)

    def refresh_placeholder_list(self, content):
        # build interactive placeholder list inside placeholder_container
        _ = self.manager.extract_placeholders(content)
        phs = self.get_placeholders()
        fixed = phs.get("fixed", [])
        dynamic = sorted(phs.get("dynamic", []))

        # helper: parse placeholder name into (raw_name, label, type)
        def parse_placeholder(raw):
            name = raw or ""
            # strip surrounding $ if any
            if name.startswith("$") and name.endswith("$"):
                name = name[1:-1]
            ptype = None
            label = name
            if name.startswith("[") and "]" in name:
                ptype = name[1 : name.index("]")].strip()
                label = name[name.index("]") + 1 :].strip() or ptype
            return (raw, label, ptype)

        # clear existing items
        try:
            for w in list(self.placeholder_container.winfo_children()):
                w.destroy()
        except Exception:
            pass
        self._placeholder_buttons.clear()

        # filter query
        q = (
            (self._ph_search_var.get() if hasattr(self, "_ph_search_var") else "")
            .strip()
            .lower()
        )

        # small icon mapping
        icon_map = {
            "checkbox": "☑️",
            "radio": "◉",
            "text": "🔤",
            "date": "📅",
        }

        def make_display(label, ptype):
            icon = icon_map.get((ptype or "").lower(), "🔸")
            if ptype:
                return f"{icon} {label} - {ptype.capitalize()}"
            return f"{icon} {label}"

        # add fixed then dynamic
        for section_name, items in (("Padrões", fixed), ("Personalizados", dynamic)):
            try:
                hdr = ctk.CTkLabel(
                    self.placeholder_container,
                    text=f"--- {section_name} ---",
                    anchor="w",
                )
                hdr.pack(fill="x", padx=2, pady=(6, 2))
            except Exception:
                pass
            for p in items:
                raw, label, ptype = parse_placeholder(p)
                display = make_display(label, ptype)
                if q and q not in display.lower() and q not in (label or "").lower():
                    continue
                try:
                    btn = ctk.CTkButton(
                        self.placeholder_container,
                        text=display,
                        width=220,
                        height=28,
                        anchor="w",
                        fg_color="transparent",
                        command=lambda name=raw: self._select_placeholder(name),
                    )
                    btn.pack(fill="x", padx=2, pady=1)
                    try:
                        btn.bind(
                            "<Double-Button-1>",
                            lambda e, name=raw: self.content_box.insert(
                                "insert", f"${name}$"
                            ),
                        )
                        btn.bind(
                            "<Button-3>",
                            lambda e, name=raw: self._rename_placeholder(name),
                        )
                    except Exception:
                        pass
                    self._placeholder_buttons[raw] = btn
                except Exception:
                    try:
                        lbl = ctk.CTkLabel(
                            self.placeholder_container, text=display, anchor="w"
                        )
                        lbl.pack(fill="x", padx=2, pady=1)
                    except Exception:
                        pass

        # re-apply selection highlight
        try:
            sel = self.selected_placeholder
            if sel and sel in self._placeholder_buttons:
                try:
                    self._placeholder_buttons[sel].configure(
                        fg_color=self.theme_manager.get_lighter_color(
                            self.theme_manager.get_theme_default_color(
                                ctk.CTkButton, "fg_color"
                            ),
                            0.15,
                        )
                    )
                except Exception:
                    pass
        except Exception:
            pass

    def save_template(self):
        name = self.get_real_name()
        content = self.get_content().strip()

        if not name:
            self._ctk_message(
                "Erro", "O nome do template não pode ser vazio.", kind="error"
            )
            return

        self.manager.save_template(self.original_name, name, content)
        self.original_name = name
        self.template_var.set(self.manager.meta.get_display_name(name))
        self.refresh_templates()
        self.last_saved_content = content
        self.refresh_placeholder_list(content)

    def delete_template(self):
        name = self.get_real_name()
        meta = self.manager.meta

        if (
            name == "Geral / Template Padrão"
            or meta.is_protected(name)
            or meta.is_favorite(name)
        ):
            self._ctk_message(
                "Protegido",
                "Este template está protegido ou favoritado e não pode ser excluído.",
                kind="warning",
            )
            return

        confirm = self._ctk_ask_yes_no(
            "Confirmação", f"Deseja excluir o template '{name}'?"
        )
        if confirm:
            self.manager.delete_template(name)

            all_templates = self.manager.get_template_names()
            if all_templates:
                next_template = all_templates[0]
            else:
                next_template = "Geral / Template Padrão"

            self.original_name = next_template
            self.template_var.set(self.manager.meta.get_display_name(next_template))
            self.load_template(next_template)
            self.refresh_templates()

    def refresh_templates(self):
        self.template_names = self.manager.get_template_names()
        display_names = self.manager.get_display_names()
        try:
            # update dropdown values and adjust width to fit longest name
            max_len = max((len(s) for s in display_names), default=20)
            dropdown_width = min(max_len * 8 + 80, 900)
            self.dropdown.configure(values=display_names, width=dropdown_width)
        except Exception:
            # some older widgets may not support configure; ignore safely
            try:
                self.dropdown.configure(values=display_names)
            except Exception:
                pass

        if self.original_name in self.template_names:
            self.template_var.set(
                self.manager.meta.get_display_name(self.original_name)
            )

    def _select_placeholder(self, name):
        """Mark a placeholder as selected (left-click)."""
        # clear previous
        try:
            prev = self.selected_placeholder
            if prev and prev in self._placeholder_buttons:
                try:
                    self._placeholder_buttons[prev].configure(fg_color="transparent")
                except Exception:
                    pass
        except Exception:
            pass
        self.selected_placeholder = name
        try:
            if name in self._placeholder_buttons:
                try:
                    self._placeholder_buttons[name].configure(
                        fg_color=self.theme_manager.get_lighter_color(
                            self.theme_manager.get_theme_default_color(
                                ctk.CTkButton, "fg_color"
                            ),
                            0.15,
                        )
                    )
                except Exception:
                    pass
        except Exception:
            pass

    def _rename_selected_placeholder(self):
        """Rename currently selected placeholder (shortcut)."""
        if not self.selected_placeholder:
            return
        self._rename_placeholder(self.selected_placeholder)

    def _rename_placeholder(self, name):
        """Prompt to rename the given placeholder and delegate to manager/master if possible."""
        if not name:
            return
        # prompt
        new_name = self._ctk_ask_string(
            "Renomear Campo", f"Novo nome para '{name}':", initial=name
        )
        if not new_name or new_name.strip() == name:
            return
        new_name = new_name.strip()
        # try manager methods first
        try:
            if hasattr(self.manager, "rename_placeholder"):
                self.manager.rename_placeholder(name, new_name)
            elif hasattr(self.manager, "rename_field"):
                self.manager.rename_field(name, new_name)
            else:
                # fallback: try to add the new dynamic field via master and remove old
                parent = getattr(self, "master", None)
                if parent:
                    if hasattr(parent, "add_dynamic_field_from_placeholder"):
                        try:
                            parent.add_dynamic_field_from_placeholder(new_name)
                        except Exception:
                            pass
                    # attempt to remove old if possible
                    if hasattr(parent, "remove_dynamic_field"):
                        try:
                            parent.remove_dynamic_field(name)
                        except Exception:
                            pass
        except Exception as e:
            self._ctk_message("Erro", f"Falha ao renomear campo: {e}", kind="error")
            return
        # refresh placeholder list to reflect changes
        try:
            self.refresh_placeholder_list(self.get_content())
        except Exception:
            pass

    def _on_dropdown_change(self, display_name):
        """Called when the user selects a template from the dropdown.

        We load the selected template (by real/internal name) and update state.
        """
        try:
            real = self.manager.meta.get_real_name(display_name)
            if real:
                self.original_name = real
                self.load_template(real)
        except Exception:
            # fallback: try to load by display name
            try:
                self.load_template(display_name)
            except Exception:
                pass

    def rename_template(self):
        """Prompt the user for a new display name and attempt to rename the current template.

        This uses `manager.rename_template` if available; otherwise it tries a
        save-as (create with new name, delete old) as a fallback.
        """
        real = self.get_real_name()
        if not real:
            return
        new_display = self._ctk_ask_string(
            "Renomear",
            "Novo nome do template:",
            initial=self.manager.meta.get_display_name(real),
        )
        if not new_display:
            return
        # Try manager.rename_template if it exists
        try:
            if hasattr(self.manager, "rename_template"):
                self.manager.rename_template(real, new_display)
            else:
                # fallback: save under new name and delete old
                content = self.manager.get_template(real)
                try:
                    self.manager.save_template(real, new_display, content)
                except Exception:
                    # some managers may raise; try again or surface error
                    self.manager.save_template(real, new_display, content)
                try:
                    self.manager.delete_template(real)
                except Exception:
                    pass
        except Exception as e:
            self._ctk_message("Erro", f"Falha ao renomear template: {e}", kind="error")
            return
        # refresh UI
        self.refresh_templates()

    def import_from_nocodb(self):
        """Trigger import from NocoDB via the manager if available."""
        try:
            # Prefer to call the main window's NocoDB UI (it implements the picker and import flow)
            if hasattr(self.master, "show_nocodb_templates"):
                try:
                    self.master.show_nocodb_templates()
                    # main window will handle the import flow; refresh selectors afterward
                    self.refresh_templates()
                except Exception as e:
                    self._ctk_message(
                        "Erro", f"Falha ao abrir NocoDB: {e}", kind="error"
                    )
            elif hasattr(self.manager, "import_from_nocodb"):
                self.manager.import_from_nocodb()
                self._ctk_message(
                    "Importado", "Importação via NocoDB concluída.", kind="success"
                )
                self.refresh_templates()
            else:
                self._ctk_message(
                    "Não disponível",
                    "Importação NocoDB não está configurada.",
                    kind="warning",
                )
        except Exception as e:
            self._ctk_message("Erro", f"Falha na importação: {e}", kind="error")

    def toggle_favorite(self):
        real = self.get_real_name()
        self.manager.meta.toggle_favorite(real)
        self.refresh_templates()

    def toggle_protected(self):
        real = self.get_real_name()
        if self.manager.meta.is_favorite(real):
            self._ctk_message(
                "Aviso",
                "Templates favoritos já são protegidos automaticamente.",
                kind="info",
            )
            return
        self.manager.meta.toggle_protected(real)
        self.refresh_templates()

    def show_autocomplete(self, event=None):
        placeholders = self.manager.extract_placeholders(self.get_content())
        all_ph = list(
            set(
                self.get_placeholders().get("fixed", [])
                + self.get_placeholders().get("dynamic", [])
                + placeholders
            )
        )
        sorted_ph = sorted(set(all_ph))

        popup = ctk.CTkToplevel(self)
        popup.transient(self)
        popup.grab_set()
        popup.geometry("+%d+%d" % (self.winfo_rootx() + 200, self.winfo_rooty() + 200))
        popup.overrideredirect(True)

        frame = ctk.CTkFrame(popup)
        frame.pack(padx=5, pady=5)

        for ph in sorted_ph:

            def insert(ph_inner=ph):
                self.content_box.insert("insert", f"${ph_inner}$")
                popup.destroy()

            btn = ctk.CTkButton(
                frame,
                text=f"${ph}$",
                width=180,
                height=26,
                font=ctk.CTkFont(size=11),
                command=insert,
            )
            btn.pack(pady=1, anchor="w")

    def open_placeholder_picker(self):
        phs = sorted(
            set(
                self.get_placeholders().get("fixed", [])
                + self.get_placeholders().get("dynamic", [])
            )
        )

        dlg = ctk.CTkToplevel(self)
        dlg.title("Inserir Campo")
        dlg.geometry("420x320")
        dlg.transient(self)
        dlg.grab_set()

        dlg.grid_columnconfigure(0, weight=1)

        search = ctk.CTkEntry(dlg, placeholder_text="Pesquisar...")
        search.grid(row=0, column=0, padx=12, pady=(12, 6), sticky="ew")

        list_frame = ctk.CTkFrame(dlg)
        list_frame.grid(row=1, column=0, padx=12, pady=(0, 6), sticky="nsew")
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        # Use a CTkScrollableFrame with CTkButton items so we stay 100% CustomTkinter
        try:
            scroll = ctk.CTkScrollableFrame(list_frame, width=1, height=200)
        except Exception:
            # fallback if older CTk doesn't have CTkScrollableFrame
            scroll = ctk.CTkFrame(list_frame)
        scroll.grid(row=0, column=0, sticky="nsew")

        # container for item widgets and quick lookup
        item_buttons = {}
        selected_name = {"value": None}

        def build_items(items):
            # Clear existing
            for w in scroll.winfo_children():
                w.destroy()
            item_buttons.clear()
            for p in items:
                btn = ctk.CTkButton(
                    scroll,
                    text=p,
                    width=200,
                    height=28,
                    anchor="w",
                    fg_color="transparent",
                    command=lambda pp=p: select_item(pp),
                )
                btn.pack(fill="x", padx=2, pady=1)
                item_buttons[p] = btn

        def select_item(name):
            # toggle selection visual
            prev = selected_name["value"]
            if prev and prev in item_buttons:
                try:
                    item_buttons[prev].configure(fg_color="transparent")
                except Exception:
                    pass
            selected_name["value"] = name
            if name in item_buttons:
                try:
                    # subtle highlight for selected item
                    item_buttons[name].configure(
                        fg_color=self.theme_manager.get_lighter_color(
                            self.theme_manager.get_theme_default_color(
                                ctk.CTkButton, "fg_color"
                            ),
                            0.15,
                        )
                    )
                except Exception:
                    pass

        # initial build
        build_items(phs)

        default_lbl = ctk.CTkLabel(dlg, text="Valor padrão (opcional):")
        default_lbl.grid(row=2, column=0, padx=12, pady=(6, 0), sticky="w")
        default_entry = ctk.CTkEntry(dlg)
        default_entry.grid(row=3, column=0, padx=12, pady=(2, 6), sticky="ew")

        args_lbl = ctk.CTkLabel(dlg, text="Argumentos (opcional):")
        args_lbl.grid(row=4, column=0, padx=12, pady=(6, 0), sticky="w")
        args_entry = ctk.CTkEntry(dlg, placeholder_text='ex: "João, Silva", 3')
        args_entry.grid(row=5, column=0, padx=12, pady=(2, 6), sticky="ew")

        # Inline indicator for creating a new placeholder when search text has no matches
        new_indicator = ctk.CTkLabel(
            dlg, text="", font=ctk.CTkFont(size=11), text_color="#999999"
        )
        new_indicator.grid(row=6, column=0, padx=12, pady=(4, 2), sticky="w")

        def filter_list(event=None):
            q = search.get().strip()
            ql = q.lower()
            matched = [p for p in phs if ql in p.lower()]
            build_items(matched)
            # update inline indicator
            if q and not matched:
                new_indicator.configure(
                    text=f"{q} será adicionado como novo placeholder"
                )
            else:
                new_indicator.configure(text="")

        def insert_selected():
            # Determine chosen name: selected button or search text (if no matches)
            sel = selected_name.get("value")
            typed_search = search.get().strip()
            line = None
            if sel:
                line = sel
            elif typed_search:
                # treat search text as new placeholder
                line = typed_search
            if not line:
                return

            default = default_entry.get().strip()
            args_val = args_entry.get().strip()

            insert_text = f"${line}"
            if args_val:
                insert_text = f"${line}({args_val})"
                if default:
                    insert_text = f"{insert_text}|{default}$"
                else:
                    insert_text = f"{insert_text}$"
            else:
                if default:
                    insert_text = f"${line}|{default}$"
                else:
                    insert_text = f"${line}$"

            # If new, delegate registration to parent so sanitization/persistence is applied
            try:
                parent = self.master
                if typed_search and (typed_search not in phs):
                    try:
                        parent.add_dynamic_field_from_placeholder(typed_search)
                    except Exception:
                        pass
            except Exception:
                pass

            try:
                self.content_box.insert("insert", insert_text)
            except Exception:
                # fallback if CTkTextbox behaves differently
                try:
                    self.content_box.insert("insert", insert_text)
                except Exception:
                    pass

            # Refresh the placeholder list in this editor immediately
            try:
                self.refresh_placeholder_list(self.get_content())
            except Exception:
                pass
            dlg.update_idletasks()
            # Ensure dialog won't be smaller than its content
            try:
                dlg.minsize(dlg.winfo_reqwidth(), dlg.winfo_reqheight())
            except Exception:
                pass
            dlg.destroy()

        btn_frame = ctk.CTkFrame(dlg)
        btn_frame.grid(row=7, column=0, pady=8, padx=12, sticky="e")
        ctk.CTkButton(btn_frame, text="Inserir", command=insert_selected).pack(
            side="right", padx=6
        )
        ctk.CTkButton(btn_frame, text="Cancelar", command=dlg.destroy).pack(
            side="right", padx=6
        )

        search.bind("<KeyRelease>", filter_list)
        # ensure minimum size so content isn't clipped
        dlg.update_idletasks()
        try:
            dlg.minsize(dlg.winfo_reqwidth(), dlg.winfo_reqheight())
        except Exception:
            pass

    def _safe_after(self, delay, callback):
        after_id = self.after(delay, callback)
        self._after_ids.add(after_id)
        return after_id

    def _cancel_all_afters(self):
        for after_id in list(self._after_ids):
            try:
                self.after_cancel(after_id)
            except Exception:
                pass
            self._after_ids.discard(after_id)

    def on_close(self):
        self._cancel_all_afters()
        # Unregister from theme manager before destroying
        if hasattr(self, "theme_manager"):
            try:
                self.theme_manager.unregister_window(self)
            except Exception:
                pass
        self.destroy()
