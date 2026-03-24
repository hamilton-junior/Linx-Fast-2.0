import requests
import logging
from logger_config import log_function_call

# Get the module logger
logger = logging.getLogger(__name__)


@log_function_call
def fetch_nocodb_templates(base_url, base_name, table_name, token=None):
    """
    Busca todos os templates do NocoDB via API REST, trazendo todos os registros (até 1000).
    Levanta requests.RequestException em caso de erro.
    """
    url = f"{base_url}/api/v1/db/data/v1/{base_name}/{table_name}?pageSize=1000"
    headers = {
        "accept": "application/json",
    }
    if token:
        headers["xc-token"] = token
        
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    
    if data.get("list"):
        print(f"[NocoDB] {len(data['list'])} registros retornados.")
    else:
        print("[NocoDB] Nenhum registro encontrado.")
        
    return data.get("list", [])
