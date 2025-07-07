import requests

def fetch_nocodb_templates(base_url, base_name, table_name, token=None):
    url = f"{base_url}/api/v1/db/data/v1/{base_name}/{table_name}"
    headers = {
        "accept": "application/json",
    }
    if token:
        headers["xc-token"] = token
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("list", [])
    return []