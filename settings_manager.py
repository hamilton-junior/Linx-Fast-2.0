import json
import os
import logging
from logger_config import set_log_level

logger = logging.getLogger(__name__)

THEME_KEY = "theme_name"
LEGACY_THEME_KEY = "theme"


DEFAULT_CONFIG = {
    "geometry": None,
    "expandable_fields": ["Procedimento Executado", "Problema Relatado"],
    "theme_name": "green",
    "appearance_mode": "dark",
    "log_level": "INFO",
    "templates_folder": "templates",
    "export_folder": "",
    "notifications": {"sound": True, "visual": True},
    "animations": True,
    "autosave": {"enabled": False, "timeout": 60},
    "smart_search": True,
    "enhanced_validation": True,
    "fonts": {"family": None, "size": 12},
}


def load_config(path="config.json"):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            # Merge defaults
            merged = DEFAULT_CONFIG.copy()
            merged.update(cfg)
            # Migração: respeita a chave canônica e usa legado apenas como fallback.
            if THEME_KEY not in cfg and LEGACY_THEME_KEY in cfg:
                merged[THEME_KEY] = cfg[LEGACY_THEME_KEY]
            merged.pop(LEGACY_THEME_KEY, None)
            return merged
        except Exception as e:
            logger.error(f"Erro ao carregar {path}: {e}")
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()


def save_config(config, path="config.json"):
    try:
        serialized_config = config.copy()
        serialized_config.pop(LEGACY_THEME_KEY, None)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(serialized_config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar config {path}: {e}")
        return False


def apply_log_level_from_config(config):
    level = config.get("log_level", "INFO")
    try:
        set_log_level(level)
    except Exception as e:
        logger.error(f"Erro ao aplicar log level: {e}")


def ensure_defaults_saved(path="config.json"):
    cfg = load_config(path)
    save_config(cfg, path)
