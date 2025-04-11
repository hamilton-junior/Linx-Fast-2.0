import os
import json

class TemplateMeta:
    def __init__(self, base_dir="templates"):
        self.meta_path = os.path.join(base_dir, "meta.json")
        self.meta = {}
        self._load()

    def _load(self):
        if os.path.exists(self.meta_path):
            with open(self.meta_path, "r", encoding="utf-8") as f:
                self.meta = json.load(f)
        else:
            self.meta = {}

    def _save(self):
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(self.meta, f, indent=2, ensure_ascii=False)

    def _ensure_entry(self, template_name):
        if template_name not in self.meta:
            self.meta[template_name] = {}

    def is_favorite(self, name):
        return self.meta.get(name, {}).get("favorito", False)

    def is_protected(self, name):
        return self.meta.get(name, {}).get("protegido", False)

    def toggle_favorite(self, name):
        self._ensure_entry(name)
        current = self.is_favorite(name)
        self.meta[name]["favorito"] = not current
        if not current:
            self.meta[name]["protegido"] = False  # Favorito remove proteção manual
        self._save()

    def toggle_protected(self, name):
        self._ensure_entry(name)
        if self.is_favorite(name):
            return  # Favorito já é protegido, não permite alterar
        current = self.is_protected(name)
        self.meta[name]["protegido"] = not current
        self._save()

    def get_sorted_templates(self, template_names):
        def sort_key(name):
            is_fav = self.is_favorite(name)
            category = name.split(" / ")[0] if " / " in name else "Geral"
            is_geral = category == "Geral"

            return (
                0 if is_fav and is_geral else
                1 if is_fav else
                2 if is_geral else
                3,
                name.lower()
            )

        return sorted(template_names, key=sort_key)


    def get_display_name(self, name):
        if self.is_favorite(name):
            return f"⭐ {name}"
        elif self.is_protected(name):
            return f"🔒 {name}"
        return name

    def get_real_name(self, display_name):
        if display_name.startswith("⭐ ") or display_name.startswith("🔒 "):
            return display_name[2:]
        return display_name

    def remove_meta(self, name):
        if name in self.meta:
            del self.meta[name]
            self._save()

    def rename_meta(self, old, new):
        if old in self.meta:
            self.meta[new] = self.meta.pop(old)
            self._save()
