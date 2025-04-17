class UIAnimator:
    @staticmethod
    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    @staticmethod
    def rgb_to_hex(rgb):
        return "#{:02x}{:02x}{:02x}".format(*map(int, rgb))

    @classmethod
    def animate_border(cls, widget, from_color, to_color, steps=10, duration=1000, on_complete=None):
        start = cls.hex_to_rgb(from_color)
        end = cls.hex_to_rgb(to_color)
        diff = [(e - s) / steps for s, e in zip(start, end)]

        def step(i=0):
            if i > steps:
                if on_complete:
                    on_complete()
                return
            rgb = [start[j] + diff[j] * i for j in range(3)]
            widget.configure(border_color=cls.rgb_to_hex(rgb))
            widget.after(duration // steps, lambda: step(i + 1))

        step()
