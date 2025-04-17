import os
import re
from template_meta import TemplateMeta

class TemplateManager:
    def __init__(self, template_dir="templates"):
        self.template_dir = os.path.abspath(template_dir)
        self.templates = {}  # {"Categoria / Nome": conteúdo}
        self.meta = TemplateMeta(self.template_dir)
        self._ensure_directory()
        self.load_templates()

    def _ensure_directory(self):
        os.makedirs(self.template_dir, exist_ok=True)

    def _template_path(self, full_name):
        category, name = self._split_name(full_name)
        if category == "Geral":
            return os.path.join(self.template_dir, f"{name}.txt")
        folder = os.path.join(self.template_dir, category)
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, f"{name}.txt")

    def _split_name(self, full_name):
        parts = full_name.split(" / ", 1)
        if len(parts) == 1:
            return ("Geral", parts[0])
        return (parts[0], parts[1])

    def get_template_names(self):
        return self.meta.get_sorted_templates(list(self.templates.keys()))

    def get_display_names(self):
        return [self.meta.get_display_name(name) for name in self.get_template_names()]

    def get_template(self, full_name):
        return self.templates.get(full_name, "")

    def save_template(self, old_name, new_name, content):
        if old_name != new_name and old_name in self.templates:
            old_path = self._template_path(old_name)
            if os.path.exists(old_path):
                os.remove(old_path)
            del self.templates[old_name]
            self.meta.rename_meta(old_name, new_name)

        self.templates[new_name] = content
        with open(self._template_path(new_name), "w", encoding="utf-8") as f:
            f.write(content)

    def add_template(self, full_name, content=""):
        if full_name not in self.templates:
            self.templates[full_name] = content
            with open(self._template_path(full_name), "w", encoding="utf-8") as f:
                f.write(content)

    def delete_template(self, full_name):
        if full_name in self.templates:
            path = self._template_path(full_name)
            if os.path.exists(path):
                os.remove(path)
            del self.templates[full_name]
            self.meta.remove_meta(full_name)

    def load_templates(self):
        self.templates = {}

        for root, _, files in os.walk(self.template_dir):
            for file in files:
                if file.endswith(".txt"):
                    rel_path = os.path.relpath(root, self.template_dir)
                    category = rel_path.replace("\\", "/") if rel_path != "." else "Geral"
                    name = file[:-4]
                    full_name = f"{category} / {name}" if category != "Geral" else f"{name}"
                    self.templates[full_name] = self._read_template(os.path.join(root, file))

        if not self.templates:
            self.add_template("Template Padrão", self.get_default_template())

    def _read_template(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def extract_placeholders(self, content):
        return list({match.strip("$") for match in re.findall(r"\$[a-zA-Z0-9 _\\-çÇáéíóúãõâêîôûÀ-ÿ]+\$", content)})

    def get_default_template(self):
        return (
            "Olá $Nome$,\n\n"
            "Identificamos o seguinte problema: $Problema Relatado$.\n"
            "CNPJ: $CNPJ$\n"
            "Telefone: $Telefone$\n"
            "Email: $Email$\n"
            "Protocolo: $Protocolo$\n\n"
            "Procedimento realizado: $Procedimento Executado$\n\n"
            "Atenciosamente,\nEquipe de Suporte."
        )
