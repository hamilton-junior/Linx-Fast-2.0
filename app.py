import logging
from logger_config import setup_logging
from main_window import TemplateApp

if __name__ == "__main__":
    # Configura logging
    setup_logging()
    logger = logging.getLogger("app")
    logger.info("Iniciando Linx Fast...")

    try:
        app = TemplateApp()
        app.mainloop()
    except Exception:
        logger.exception("Erro fatal na aplicação:")
        raise
