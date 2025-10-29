import sys
import os

# Ensure project root is on sys.path so imports work when running from tests/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main_window import TemplateApp

# Instantiate the app, open settings, then close after a short delay.
app = TemplateApp()

# Open settings window
try:
    app.open_settings()
except Exception as e:
    print("Error opening settings:", e)

# Schedule app to close after 1.5 seconds
app.after(1500, app.destroy)
app.mainloop()
