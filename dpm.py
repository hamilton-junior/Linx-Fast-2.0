import json
import os
from datetime import date

class DailyPasswordManager:
    def __init__(self, file_path="config.json"):
        self.file_path = file_path
        self.today = str(date.today())
        self.password = None
        self._load_password()

    def _load_password(self):
        config = self._read_config()
        dp = config.get("daily_password", {})

        # Se a data for hoje, carrega a senha; se não, limpa
        if dp.get("date") == self.today:
            self.password = dp.get("password")
        else:
            self._update_config_password(None)  # Reset para hoje

    def get_today_password(self):
        return self.password

    def set_today_password(self, password):
        self.password = password
        self._update_config_password(password)

    def reset_daily_password(self):
        self.set_today_password(None)


    def _read_config(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[ERRO ao ler config.json]: {e}")
                print("A leitura do arquivo de configuração falhou. Por favor, verifique se o arquivo está corrompido ou com permissões corretas.")
                # Notifica o usuário e retorna None para evitar sobrescrever o arquivo
                return None
        else:
            print(f"[AVISO]: O arquivo de configuração '{self.file_path}' não existe.")
        return None


    def _write_config(self, data):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"[ERRO ao escrever config.json]: {e}")

    def _update_config_password(self, new_password):
        config = self._read_config()
        if config is None:
            print("[ERRO]: Não foi possível atualizar a senha diária porque a configuração não pôde ser lida.")
            return
        config["daily_password"] = {
            "date": self.today,
            "password": new_password
        }
        self._write_config(config)
