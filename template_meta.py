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
            # Unifica entradas duplicadas (case-insensitive) e padroniza capitalização do nome do template (não da pasta)
            self._unify_case_insensitive_entries()
        else:
            self.meta = {}

    def _unify_case_insensitive_entries(self):
        # Unifica entradas duplicadas (case-insensitive) e padroniza capitalização do nome do template (não da pasta)
        lowered = {}
        to_remove = []
        for k, v in list(self.meta.items()):
            # Padroniza: mantém a pasta como está, mas o nome do template com a primeira letra maiúscula
            if " / " in k:
                pasta, nome = k.split(" / ", 1)
                nome_corrigido = nome[:1].upper() + nome[1:] if nome else nome
                canonical_name = f"{pasta} / {nome_corrigido}"
            else:
                nome_corrigido = k[:1].upper() + k[1:] if k else k
                canonical_name = nome_corrigido
            k_lower = canonical_name.lower()
            if k_lower in lowered:
                # Unifica: mantém o nome com mais informações (mais campos True, ou mais campos no geral)
                existing = lowered[k_lower]
                # Junta os campos (favorito, protegido, nocodb_id, etc)
                merged = existing.copy()
                merged.update(v)
                # Se algum dos dois for favorito/protegido, mantém True
                if existing.get("favorito") or v.get("favorito"):
                    merged["favorito"] = True
                if existing.get("protegido") or v.get("protegido"):
                    merged["protegido"] = True
                # Se algum dos dois tiver nocodb_id, mantém
                if existing.get("nocodb_id") and not merged.get("nocodb_id"):
                    merged["nocodb_id"] = existing["nocodb_id"]
                if v.get("nocodb_id") and not merged.get("nocodb_id"):
                    merged["nocodb_id"] = v["nocodb_id"]
                # Sempre mantém o nome padronizado
                self.meta[canonical_name] = merged
                to_remove.append(k)
                if lowered[k_lower + "_orig"] in self.meta and lowered[k_lower + "_orig"] != canonical_name:
                    to_remove.append(lowered[k_lower + "_orig"])
            else:
                lowered[k_lower] = v
                lowered[k_lower + "_orig"] = canonical_name
                # Se o nome não está padronizado, move para o padronizado
                if k != canonical_name:
                    self.meta[canonical_name] = v
                    to_remove.append(k)
        # Remove duplicados
        for k in set(to_remove):
            if k in self.meta:
                del self.meta[k]
        if to_remove:
            self._save()

    def _ensure_unified(self):
        # Garante que o meta está unificado antes de qualquer operação
        self._unify_case_insensitive_entries()

    def _save(self):
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(self.meta, f, indent=2, ensure_ascii=False)

    def _ensure_entry(self, template_name):
        self._ensure_unified()
        canonical_name = self._canonical_name(template_name)
        if canonical_name not in self.meta:
            self.meta[canonical_name] = {}

    def _canonical_name(self, name):
        # Mantém a pasta como está, mas o nome do template com a primeira letra maiúscula
        if " / " in name:
            pasta, nome = name.split(" / ", 1)
            nome_corrigido = nome[:1].upper() + nome[1:] if nome else nome
            return f"{pasta} / {nome_corrigido}"
        else:
            nome_corrigido = name[:1].upper() + name[1:] if name else name
            return nome_corrigido

    def _find_meta_key(self, name):
        # Garante unificação antes de buscar
        self._ensure_unified()
        # Busca insensível a capitalização, mas padroniza só o nome do template
        def normalize(n):
            if " / " in n:
                pasta, nome = n.split(" / ", 1)
                return f"{pasta} / {nome[:1].upper() + nome[1:] if nome else nome}".lower()
            else:
                return (n[:1].upper() + n[1:] if n else n).lower()
        name_norm = normalize(name)
        for k in self.meta:
            if normalize(k) == name_norm:
                return k
        return self._canonical_name(name)

    def is_favorite(self, name):
        k = self._find_meta_key(name)
        return self.meta.get(k, {}).get("favorito", False)

    def is_protected(self, name):
        k = self._find_meta_key(name)
        return self.meta.get(k, {}).get("protegido", False)

    def toggle_favorite(self, name):
        k = self._find_meta_key(name)
        self._ensure_entry(k)
        current = self.is_favorite(k)
        self.meta[k]["favorito"] = not current
        if not current:
            self.meta[k]["protegido"] = False  # Favorito remove proteção manual
        self._save()

    def toggle_protected(self, name):
        k = self._find_meta_key(name)
        self._ensure_entry(k)
        if self.is_favorite(k):
            return  # Favorito já é protegido, não permite alterar
        current = self.is_protected(k)
        self.meta[k]["protegido"] = not current
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
        k = self._find_meta_key(name)
        if k in self.meta:
            del self.meta[k]
            self._save()

    def rename_meta(self, old, new):
        old_k = self._find_meta_key(old)
        new_k = self._canonical_name(new)
        if old_k in self.meta:
            self.meta[new_k] = self.meta.pop(old_k)
            self._save()
