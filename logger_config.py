import logging
import os
from logging.handlers import RotatingFileHandler
import types


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
    Obtém o nível de log a partir da variável de ambiente LINXFASTLOGLEVEL.
    Aceita tanto nomes (info, warn, error, debug, etc) quanto números (10, 20, 30, ...).
    """
    env_level = os.getenv("LINXFASTLOGLEVEL", "INFO")
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
    print(
        f"[DEBUG] LINXFASTLOGLEVEL={os.getenv('LINXFASTLOGLEVEL')}, log_level={env_level_name} ({logging.getLevelName(env_level_name)})"
    )

    return logging.INFO


def setup_logging():
    """Configura o sistema de logging com níveis apropriados e formatação."""
    # Cria diretório de logs se não existir
    log_dir = "log"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "fast.log")

    # Configura o formato do log
    formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03d - [%(levelname)s] %(filename)s:%(lineno)d (%(name)s/%(funcName)s) --> %(message)s",
        datefmt="%d-%m-%Y @ %H:%M:%S",
    )

    # Obtém o nível de log da variável de ambiente
    log_level = get_log_level()
    # Loga o valor lido da variável de ambiente para depuração
    print(
        f"[LOG VAR] LINXFASTLOGLEVEL={os.getenv('LINXFASTLOGLEVEL')}, log_level={log_level} ({logging.getLevelName(log_level)})"
    )

    # Remove handlers antigos para evitar logs duplicados
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Handler para arquivo com rotação (mantém últimos 5 arquivos de 1MB cada)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=1024 * 1024, backupCount=5, encoding="utf-8"  # 1MB
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
        f"Logging inicializado com o nível: {logging.getLevelName(log_level)} (from LINXFASTLOGLEVEL={os.getenv('LINXFASTLOGLEVEL')})"
    )
