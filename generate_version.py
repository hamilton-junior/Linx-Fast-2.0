import subprocess
import datetime

def get_git_version():
    try:
        # Pega o último tag anotado (ex: v1.2.3). Se não houver, retorna "dev"
        tag = subprocess.check_output(["git", "describe", "--tags", "--abbrev=0"], encoding="utf-8").strip()
    except Exception:
        tag = "dev"
    date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    return tag, date

def write_version_py():
    tag, date = get_git_version()
    with open("version.py", "w", encoding="utf-8") as f:
        f.write(f'VERSION = "{tag}"\n')
        f.write(f'BUILD_DATE = "{date}"\n')

if __name__ == "__main__":
    write_version_py()