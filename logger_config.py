import logging
import os
from logging.handlers import RotatingFileHandler
import types


def log_function_call(func):
    """Decorator to log function calls, return values, and errors."""

    def wrapper(*args, **kwargs):
        try:
            logging.debug(
                f"Chamando: {func.__name__} | Args: {args} | Kwargs: {kwargs}"
            )
            result = func(*args, **kwargs)  # Call the original function
            logging.debug(f"Finalizado: {func.__name__} | Retornado: {result}")
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
    """Gets the log level from environment variable or falls back to INFO"""
    env_level = os.getenv("LINXFASTLOGLEVEL", "INFO").upper()
    try:
        return getattr(logging, env_level)
    except AttributeError:
        return logging.INFO


def setup_logging():
    """Configura o sistema de logging com níveis apropriados e formatação."""
    # Cria diretório de logs se não existir
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "fast.log")

    # Configura o formato do log
    formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03d - [%(levelname)s] %(filename)s:%(lineno)d (%(name)s/%(funcName)s) --> %(message)s",
        datefmt="%d-%m-%Y @ %H:%M:%S",
    )

    # Handler para arquivo com rotação (mantém últimos 5 arquivos de 1MB cada)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=1024 * 1024, backupCount=5, encoding="utf-8"  # 1MB
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    # Handler para console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(get_log_level())  # Uses environment variable or fallback

    # Configura o logger root
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logging.info(
        f"Logging initialized with console level: {logging.getLevelName(get_log_level())}"
    )

    # Loggers específicos para módulos
    modules = [
        "app",
        "main_window",
        "quick_template_popup",
        "template_editor",
        "template_manager",
    ]
    for module in modules:
        logger = logging.getLogger(module)
        logger.setLevel(logging.DEBUG)
