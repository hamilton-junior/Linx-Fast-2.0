from logger_config import setup_logging
import logging
from main_window import TemplateApp

setup_logging()

if __name__ == "__main__":
    logger = logging.getLogger("app")
    logger.info("Iniciando Linx Fast...")

    try:
        app = TemplateApp()
        app.mainloop()
    except Exception:
        logger.exception("Erro fatal na aplicação:")
        raise
