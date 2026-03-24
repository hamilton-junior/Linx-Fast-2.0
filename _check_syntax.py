import ast
import sys

files = [
    "main_window.py",
    "settings_manager.py",
    "dpm.py",
    "template_meta.py",
    "quick_template_popup.py",
    "settings_window.py",
    "logger_config.py",
]

results = []
for f in files:
    try:
        with open(f, "r", encoding="utf-8") as fh:
            src = fh.read()
        ast.parse(src)
        results.append(f"OK: {f}")
    except SyntaxError as e:
        results.append(f"SYNTAX ERROR in {f}: {e}")
    except Exception as e:
        results.append(f"ERROR {f}: {e}")

with open("_syntax_check_result.txt", "w") as out:
    out.write("\n".join(results) + "\n")

print("\n".join(results))
