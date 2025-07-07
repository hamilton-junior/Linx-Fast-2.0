import subprocess
import datetime

def get_git_version():
    try:
        # Conta o número de commits (versão incremental)
        commit_count = subprocess.check_output(["git", "rev-list", "--count", "HEAD"], encoding="utf-8").strip()
    except Exception:
        commit_count = "0"
    try:
        # Pega o último tag anotado (ex: hotfix). Se não houver, retorna "fast"
        tag = subprocess.check_output(
            ["git", "describe", "--tags", "--abbrev=0"],
            stderr=subprocess.DEVNULL,  # suprime o erro no terminal
            encoding="utf-8"
        ).strip()
    except Exception:
        tag = "fast"
    date = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
    return commit_count, tag, date

def write_version_py():
    commit_count, tag, date = get_git_version()
    version_str = f"0.{commit_count}-{tag}"
    with open("version.py", "w", encoding="utf-8") as f:
        f.write(f'VERSION = "{version_str}"\n')
        f.write(f'BUILD_DATE = "{date}"\n')

if __name__ == "__main__":
    write_version_py()