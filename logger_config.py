import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logging():
    """Configura o sistema de logging com níveis apropriados e formatação."""
    # Cria diretório de logs se não existir
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "fast.log")

    # Configura o formato do log
    formatter = logging.Formatter(
        "%(asctime)s - [%(levelname)s] %(filename)s:%(lineno)d (%(name)s/%(funcName)s) --> %(message)s",
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
    console_handler.setLevel(logging.INFO)

    # Configura o logger root
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

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
