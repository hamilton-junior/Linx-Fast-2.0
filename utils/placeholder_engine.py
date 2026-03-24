import re
import csv
import datetime
import logging
from logger_config import auto_log_functions

# Configure logger for this module
logger = logging.getLogger(__name__)

@auto_log_functions
class PlaceholderEngine:
    """
    Manages dynamic placeholder substitution in text templates.

    Allows registration of custom handlers for placeholders and provides built-in support for date/time placeholders like $Agora$ and $Agora[formato]$.
    """

    def __init__(self):
        self.handlers = {}

    def register_handler(self, name, func):
        self.handlers[name] = func

    def process(self, text):
        def replacer(match):
            content = match.group(1)

            # Handle $Agora$ and $Agora[format]$
            if content == "Agora":
                fmt = "%H:%M"
                try:
                    return datetime.datetime.now().strftime(fmt)
                except Exception:
                    return match.group(0)
            if content.startswith("Agora[") and content.endswith("]"):
                fmt = content[6:-1]
                try:
                    return datetime.datetime.now().strftime(fmt)
                except Exception:
                    return match.group(0)

            # Support default value syntax: $Name|Default$
            name = content
            default = None
            if "|" in content:
                # Split only on the first '|' to allow '|' in defaults
                name, default = content.split("|", 1)

            # Trim whitespace
            name = name.strip()
            if default is not None:
                default = default

            # Support arguments syntax: Name(arg1,arg2)
            args = []
            base_name = name
            if "(" in name and name.endswith(")"):
                try:
                    idx = name.index("(")
                    base_name = name[:idx].strip()
                    args_str = name[idx + 1 : -1]
                    if args_str.strip() != "":
                        # Parse arguments using csv.reader to allow quoted args with commas
                        try:
                            parsed = next(csv.reader([args_str], skipinitialspace=True))
                        except Exception:
                            parsed = [a.strip() for a in args_str.split(",")]

                        # Convert numeric-looking args to int/float when possible, else keep as string
                        def convert(v: str):
                            v = v.strip()
                            if v == "":
                                return ""
                            # Try int
                            try:
                                return int(v)
                            except Exception:
                                pass
                            # Try float
                            try:
                                return float(v)
                            except Exception:
                                pass
                            # Otherwise return string (without surrounding quotes if present)
                            if (v.startswith('"') and v.endswith('"')) or (
                                v.startswith("'") and v.endswith("'")
                            ):
                                return v[1:-1]
                            return v

                        args = [convert(a) for a in parsed]
                except Exception:
                    base_name = name

            # Look up handler
            handler = self.handlers.get(base_name)
            if handler:
                try:
                    # Try calling with args; if handler doesn't accept them, fall back to no-arg call
                    try:
                        val = handler(*args)
                    except TypeError:
                        val = handler()
                except Exception:
                    val = None

                if val is not None and val != "":
                    return str(val)
                if default is not None:
                    return default
                return match.group(0)

            # No handler found: return default if provided, else leave placeholder intact
            if default is not None:
                return default
            return match.group(0)

        # Regex: capture everything between $...$ (restricted to avoid matching newlines)
        return re.sub(r"\$([^\n\r$]+)\$", replacer, text)


# Instância global da engine
placeholder_engine = PlaceholderEngine()

# Handlers padrões
placeholder_engine.register_handler(
    "Hoje", lambda: datetime.datetime.now().strftime("%d/%m/%Y")
)
DIAS_SEMANA_PT = {
    "Monday": "segunda-feira",
    "Tuesday": "terça-feira",
    "Wednesday": "quarta-feira",
    "Thursday": "quinta-feira",
    "Friday": "sexta-feira",
    "Saturday": "sábado",
    "Sunday": "domingo",
}

placeholder_engine.register_handler(
    "DiaSemana",
    lambda: DIAS_SEMANA_PT.get(
        datetime.datetime.now().strftime("%A"), datetime.datetime.now().strftime("%A")
    ),
)
placeholder_engine.register_handler(
    "HoraMinuto", lambda: datetime.datetime.now().strftime("%H:%M")
)
placeholder_engine.register_handler(
    "HoraMinutoSegundo", lambda: datetime.datetime.now().strftime("%H:%M:%S")
)
