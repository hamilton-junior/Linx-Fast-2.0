import customtkinter as ctk


class FieldEntry(ctk.CTkFrame):
    def __init__(self, master, field_name=None, label_text=None, on_focus_out_callback=None):
        super().__init__(master, fg_color="transparent")

        self.field_name = field_name
        self.placeholder = label_text
        self.on_focus_out_callback = on_focus_out_callback

        self.label = ctk.CTkLabel(self, text=label_text, width=150, anchor="w")
        self.label.pack(side="left", padx=(0, 5))

        self.entry = ctk.CTkEntry(self, placeholder_text=label_text)
        self.entry.pack(side="left", fill="x", expand=True)

        # Cor original confiável
        border_color = self.entry.cget("border_color")
        if isinstance(border_color, (list, tuple)):
            border_color = border_color[0]
        self.entry.original_border_color = border_color or "#979da2"

        self.entry.was_invalid = False

        # Focus bindings
        self.entry.bind("<FocusOut>", lambda e: self._handle_focus_out())
        self.entry.bind("<FocusIn>", lambda e: self._handle_focus_in())

    def _handle_focus_out(self):
        self.on_focus_out_callback(self)

    def _handle_focus_in(self):
        if self.entry.was_invalid:
            self.reset_border()

    def get_value(self):
        return self.entry.get()

    def set_value(self, value):
        self.entry.delete(0, "end")
        self.entry.insert(0, value)

    def clear(self):
        self.entry.delete(0, "end")
        self.show_placeholder()
        self.reset_border()

    def show_placeholder(self):
        self.entry.configure(placeholder_text=self.placeholder)

    def mark_invalid(self):
        self.entry.configure(border_color="#D32F2F")
        self.entry.was_invalid = True

    def mark_valid(self):
        self.animate_border(from_color="#D32F2F", to_color="#00C853", final_color=self.entry.original_border_color)
        self.entry.was_invalid = False

    def reset_border(self):
        self.entry.configure(border_color=self.entry.original_border_color)

    def animate_border(self, from_color, to_color, final_color=None, steps=15, duration=500):
        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip("#")
            return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

        def rgb_to_hex(rgb):
            return "#{:02x}{:02x}{:02x}".format(*map(int, rgb))

        start = hex_to_rgb(from_color)
        mid = hex_to_rgb(to_color)
        end = hex_to_rgb(final_color or self.entry.original_border_color)

        def interpolate(a, b, t):
            return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

        def phase1(step=0):
            if step > steps:
                self.after(100, lambda: phase2(0))
                return
            t = step / steps
            color = rgb_to_hex(interpolate(start, mid, t))
            self.entry.configure(border_color=color)
            self.after(duration // steps, lambda: phase1(step + 1))

        def phase2(step=0):
            if step > steps:
                self.entry.configure(border_color=rgb_to_hex(end))
                return
            t = step / steps
            color = rgb_to_hex(interpolate(mid, end, t))
            self.entry.configure(border_color=color)
            self.after(duration // steps, lambda: phase2(step + 1))

        phase1()
