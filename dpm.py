import json
import os
from datetime import date, datetime
import logging
from logger_config import auto_log_functions

# Get the module logger
logger = logging.getLogger(__name__)


@auto_log_functions
class DailyPasswordManager:
    def __init__(self, file_path="config.json"):
        self.file_path = file_path
        self.today = str(date.today())
        self.password = None
        self._config_cache = None
        self._load_password()

    def _log(self, msg):
        logger.info(msg)

    def _read_config(self):
        if self._config_cache is not None:
            return self._config_cache

        if not os.path.exists(self.file_path):
            self._log(f"Arquivo de configuração '{self.file_path}' não encontrado. Criando novo.")
            self._config_cache = {}
            return self._config_cache

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                self._config_cache = json.load(f)
                return self._config_cache
        except json.JSONDecodeError:
            self._log(f"Arquivo '{self.file_path}' está corrompido. Substituindo por um novo.")
            self._config_cache = {}
            return self._config_cache
        except Exception as e:
            self._log(f"Erro ao ler config: {e}")
            self._config_cache = {}
            return self._config_cache

    def _write_config(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self._config_cache, f, indent=4)
        except Exception as e:
            self._log(f"Erro ao salvar config: {e}")

    def _load_password(self):
        config = self._read_config()
        dp = config.get("daily_password", {})

        if dp.get("date") == self.today:
            self.password = dp.get("password")
        else:
            # Atualiza somente se necessário
            config["daily_password"] = {
                "date": self.today,
                "password": None
            }
            self.password = None
            self._write_config()

    def get_today_password(self):
        return self.password

    def set_today_password(self, password):
        config = self._read_config()
        self.password = password
        config["daily_password"] = {
            "date": self.today,
            "password": password
        }
        self._write_config()

    def reset_daily_password(self):
        self.set_today_password(None)

    def is_password_set(self):
        return bool(self.password)
