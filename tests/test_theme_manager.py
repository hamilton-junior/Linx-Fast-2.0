import unittest
from theme_manager import ThemeManager


class DummyWindow:
    def __init__(self):
        self._exists = True
        self.refreshed = False
        self.after_calls = []

    def winfo_exists(self):
        return self._exists

    def winfo_children(self):
        return []

    def update_idletasks(self):
        return None

    def after(self, ms, callback):
        # For test purposes, call immediately and record
        self.after_calls.append((ms, callback))
        try:
            callback()
        except Exception:
            pass

    def on_theme_changed(self):
        self.refreshed = True


class ThemeManagerTests(unittest.TestCase):
    def test_register_and_refresh(self):
        tm = ThemeManager(theme_name="green", mode="dark")
        w = DummyWindow()
        tm.register_window(w)
        # Call set_theme which should schedule refresh and trigger on_theme_changed
        # Use a different theme to trigger an actual update (set_theme now no-ops
        # when the requested theme is already active).
        tm.set_theme("blue")
        # Because DummyWindow.after calls callback immediately, refreshed should be True
        self.assertTrue(w.refreshed)

    def test_refresh_all_windows_async_prunes_dead(self):
        tm = ThemeManager()
        w1 = DummyWindow()
        w2 = DummyWindow()
        w2._exists = False
        tm.register_window(w1)
        tm.register_window(w2)
        tm.refresh_all_windows_async()
        # windows list should only include the alive window
        self.assertIn(w1, tm.windows)
        self.assertNotIn(w2, tm.windows)


if __name__ == "__main__":
    unittest.main()
