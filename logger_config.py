import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
import types

_BASE_DIR = Path(__file__).resolve().parent
_LOG_DIR = _BASE_DIR / "log"
_LOG_FILE = _LOG_DIR / "fast.log"


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
        if level_num in (
            logging.CRITICAL,
            logging.ERROR,
            logging.WARNING,
            logging.INFO,
            logging.DEBUG,
            logging.NOTSET,
        ):
            return level_num
    except (ValueError, TypeError):
        pass

    # Tenta converter para nome
    env_level_name = str(env_level).strip().upper()
    if env_level_name == "WARN":
        env_level_name = "WARNING"
    if hasattr(logging, env_level_name):
        return getattr(logging, env_level_name)

    print(f"[DEBUG] LFASTLOGLEVEL={env_level}, log_level={env_level_name}")
    return logging.INFO


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

    # Loga o valor lido da variável de ambiente para depuração
    print(
        f"[LOG VAR] LFASTLOGLEVEL={os.getenv('LFASTLOGLEVEL')}, log_level={log_level} ({level_name})"
    )

    # Remove handlers antigos para evitar logs duplicados
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Handler para arquivo com rotação (mantém últimos 5 arquivos de 1MB cada)
    file_handler = RotatingFileHandler(
        str(_LOG_FILE),
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

    logging.info(
        f"Logging inicializado com o nível: {level_name} (from LFASTLOGLEVEL={os.getenv('LFASTLOGLEVEL')})"
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
    """Clear all log files in the log directory.

    Note: clearing logs from the UI was removed; this helper remains for
    programmatic use. If you prefer to remove it entirely, I can delete it
    as well — currently it's safe to keep since it's defined here only.
    """
    if _LOG_DIR.exists():
        for file in _LOG_DIR.glob("fast.log*"):
            try:
                file.unlink()
            except Exception as e:
                logging.error(f"Erro ao limpar arquivo de log {file.name}: {e}")
        logging.info("Arquivos de log limpos com sucesso")
