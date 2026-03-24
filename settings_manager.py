import json
import os
import logging
from logger_config import set_log_level

logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

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


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into *base*, preserving all nested keys."""
    result = base.copy()
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def get_config_path() -> str:
    """Return the absolute path to config.json."""
    return CONFIG_PATH


def load_config(path: str = CONFIG_PATH) -> dict:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            return _deep_merge(DEFAULT_CONFIG, cfg)
        except Exception as e:
            logger.error(f"Erro ao carregar {path}: {e}")
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()


def save_config(config: dict, path: str = CONFIG_PATH) -> bool:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar config {path}: {e}")
        return False


def apply_log_level_from_config(config: dict) -> None:
    level = config.get("log_level", "INFO")
    try:
        set_log_level(level)
    except Exception as e:
        logger.error(f"Erro ao aplicar log level: {e}")


def ensure_defaults_saved(path: str = CONFIG_PATH) -> None:
    cfg = load_config(path)
    save_config(cfg, path)
