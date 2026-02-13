import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
import types

_BASE_DIR = Path(__file__).resolve().parent
_LOG_DIR = _BASE_DIR / "log"
_LOG_FILE = _LOG_DIR / "fast.log"
_LOGGER = logging.getLogger(__name__)


def _is_valid_log_level(value):
    """Valida se o valor pode ser convertido para um nível de log suportado."""
    try:
        level_num = int(value)
        return level_num in (
            logging.CRITICAL,
            logging.ERROR,
            logging.WARNING,
            logging.INFO,
            logging.DEBUG,
            logging.NOTSET,
        )
    except (ValueError, TypeError):
        pass

    level_name = str(value).strip().upper()
    if level_name == "WARN":
        level_name = "WARNING"
    return hasattr(logging, level_name)


def log_function_call(func):
    """Decorator to log function calls, return values, and errors."""

    def safe_repr(obj):
        try:
            return repr(obj)
        except Exception:
            return f"<{type(obj).__name__}>"

    def wrapper(*args, **kwargs):
        try:
            # Evita logar objetos tkinter diretamente (causa AttributeError)
            safe_args = tuple(safe_repr(a) for a in args)
            safe_kwargs = {k: safe_repr(v) for k, v in kwargs.items()}
            logging.debug(
                f"Chamando: {func.__name__} | Args: {safe_args} | Kwargs: {safe_kwargs}"
            )
            result = func(*args, **kwargs)  # Call the original function
            logging.debug(
                f"Finalizado: {func.__name__} | Retornado: {safe_repr(result)}"
            )
            return result
        except Exception as e:
            logging.error(f"Erro em {func.__name__}: {e}", exc_info=True)
            raise  # Re-raise the exception after logging it

    return wrapper


def auto_log_functions(cls):
    """Class decorator to automatically log all methods of a class."""
    for attr_name, attr_value in cls.__dict__.items():
        if isinstance(attr_value, types.FunctionType):  # Check if it's a function
            setattr(cls, attr_name, log_function_call(attr_value))
    return cls


def get_log_level():
    """
    Obtém o nível de log a partir da variável de ambiente LFASTLOGLEVEL.
    Aceita tanto nomes (info, warn, error, debug, etc) quanto números (10, 20, 30, ...).
    """
    env_level = os.getenv("LFASTLOGLEVEL", "INFO")

    # Tenta converter para inteiro
    try:
        level_num = int(env_level)
        if _is_valid_log_level(level_num):
            return level_num
    except (ValueError, TypeError):
        pass

    # Tenta converter para nome
    env_level_name = str(env_level).strip().upper()
    if env_level_name == "WARN":
        env_level_name = "WARNING"
    if hasattr(logging, env_level_name):
        return getattr(logging, env_level_name)

    _LOGGER.debug(
        "LFASTLOGLEVEL inválido '%s'. Usando fallback INFO (normalizado: %s)",
        env_level,
        env_level_name,
    )
    return logging.INFO


def get_log_file_path():
    """Returns the path to the current log file."""
    return str(_LOG_FILE)


def get_log_file_size():
    """Returns the current log file size in bytes."""
    try:
        return _LOG_FILE.stat().st_size
    except Exception:
        return 0


def tail_log_file(n=10):
    """Returns the last n lines of the log file."""
    try:
        with _LOG_FILE.open("r", encoding="utf-8") as f:
            # Move to end of file and get file size
            f.seek(0, 2)
            size = f.tell()

            # If file is empty, return empty list
            if size == 0:
                return []

            # Initialize list for the last n lines
            lines = []

            # Read backwards until we have n lines or reach start of file
            chars_back = 0
            while len(lines) < n and chars_back < size:
                # Move back 1024 chars or to start of file
                chars_to_read = min(1024, size - chars_back)
                f.seek(-(chars_to_read + chars_back), 2)
                data = f.read(chars_to_read)

                # Split into lines and add to list
                lines = data.splitlines() + lines
                chars_back += chars_to_read

            # Return last n lines
            return lines[-n:]
    except Exception:
        return []


def setup_logging():
    """Configura o sistema de logging com níveis apropriados e formatação."""
    # Cria diretório de logs se não existir
    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Configura o formato do log
    formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03d - [%(levelname)s] %(filename)s:%(lineno)d (%(name)s/%(funcName)s) --> %(message)s",
        datefmt="%d-%m-%Y @ %H:%M:%S",
    )

    # Obtém o nível de log da variável de ambiente
    log_level = get_log_level()
    level_name = logging.getLevelName(log_level)
    env_level = os.getenv("LFASTLOGLEVEL")
    invalid_env_level = not _is_valid_log_level(env_level)

    # Remove handlers antigos para evitar logs duplicados
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Handler para arquivo com rotação (mantém últimos 5 arquivos de 1MB cada)
    file_handler = RotatingFileHandler(
        get_log_file_path(),
        maxBytes=1024 * 1024,
        backupCount=5,
        encoding="utf-8",  # 1MB
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)

    # Handler para console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)

    # Configura o logger root
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    _LOGGER.info(
        "Logging inicializado com o nível: %s (from LFASTLOGLEVEL=%s)",
        level_name,
        env_level,
    )
    _LOGGER.debug(
        "[LOG VAR] LFASTLOGLEVEL=%s, log_level=%s (%s)",
        env_level,
        log_level,
        level_name,
    )
    if invalid_env_level:
        _LOGGER.debug(
            "LFASTLOGLEVEL inválido '%s'. Fallback INFO aplicado durante bootstrap.",
            env_level,
        )


def set_log_level(level):
    """Seta o nível de log em tempo real para o logger root e todos os handlers.

    Aceita tanto string ("DEBUG") quanto inteiro (10).
    """
    if isinstance(level, str):
        level_name = level.strip().upper()
        if level_name == "WARN":
            level_name = "WARNING"
        if hasattr(logging, level_name):
            lvl = getattr(logging, level_name)
        else:
            try:
                lvl = int(level)
            except Exception:
                return
    else:
        lvl = int(level)

    root_logger = logging.getLogger()
    root_logger.setLevel(lvl)
    for h in root_logger.handlers:
        try:
            h.setLevel(lvl)
        except Exception:
            pass

    # Also update any existing named loggers' level to inherit correctly
    logging.info(f"Nível de log atualizado para: {logging.getLevelName(lvl)}")


def clear_logs():
    """Clear all log files in the log directory."""
    if _LOG_DIR.exists():
        for file in _LOG_DIR.glob("fast.log*"):
            try:
                file.unlink()
            except Exception as e:
                logging.error(f"Erro ao limpar arquivo de log {file.name}: {e}")
        logging.info("Arquivos de log limpos com sucesso")
