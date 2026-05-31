import json
import logging
import os
import re
from intent_parser import parse_intent

KNOWLEDGE_BASE_PATH = os.path.join(os.path.dirname(__file__), "knowledge")
SCHEMA_BASE_PATH = os.path.join(KNOWLEDGE_BASE_PATH, "schema")
SIMPLE_QUERY_WORD_LIMIT = 15

# Maps regex patterns to schema file keys.
# Ordered from most specific to least specific to avoid wrong matches.
SCHEMA_MODEL_PATTERNS = [
    (r"\b(sale\.order|commande\s+(vente|client)|sales?\s+order)\b",          "sale_order"),
    (r"\b(purchase\.order|commande\s+(achat|fournisseur)|purchase\s+order)\b", "purchase_order"),
    (r"\b(account\.move|facture|invoice|avoir|credit\s+note|vendor\s+bill)\b", "account_move"),
    (r"\b(stock\.picking|livraison|bon\s+de\s+livraison|delivery\s+order|picking)\b", "stock_picking"),
    (r"\b(mrp\.production|ordre\s+de\s+fabrication|manufacturing\s+order)\b", "mrp_production"),
    (r"\b(hr\.employee|employé)\b",                                           "hr_employee"),
    (r"\b(project\.task|tâche\s+de\s+projet)\b",                             "project_task"),
    (r"\b(product\.template|product\.product|modèle\s+de\s+produit)\b",      "product_template"),
    (r"\b(res\.partner)\b",                                                   "res_partner"),
]


def load_snippet(version: str, topic: str) -> dict:
    path = os.path.join(KNOWLEDGE_BASE_PATH, f"v{version}", f"{topic}.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                logging.warning("Knowledge snippet %s does not contain a JSON object", path)
                return {}
            return data
    except json.JSONDecodeError as e:
        logging.warning("Invalid JSON in knowledge file %s: %s", path, e)
        return {}
    except OSError as e:
        logging.warning("Failed to read knowledge file %s: %s", path, e)
        return {}


def load_schema(model_key: str) -> dict:
    path = os.path.join(SCHEMA_BASE_PATH, f"{model_key}.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {}
            return data
    except (json.JSONDecodeError, OSError) as e:
        logging.warning("Failed to load schema %s: %s", path, e)
        return {}


def detect_schema(user_input: str) -> dict:
    """Return the first matching model schema for the user input, or {} if none match."""
    for pattern, model_key in SCHEMA_MODEL_PATTERNS:
        if re.search(pattern, user_input, re.IGNORECASE):
            return load_schema(model_key)
    return {}


def _render_code_block(knowledge: dict, heading: str = "##") -> str:
    """Render code snippets from a knowledge dict. Reads 'snippets' array first, falls back to legacy 'snippet' string."""
    label = knowledge.get("label", "")
    snippets = knowledge.get("snippets", [])
    if snippets:
        block = f"{heading} Patterns de référence ({label})\n"
        for snip in snippets:
            code = snip.get("code", "").strip()
            if not code:
                continue
            title = snip.get("title", "")
            block += f"_{title}_\n```python\n{code}\n```\n" if title else f"```python\n{code}\n```\n"
        return block
    snippet = knowledge.get("snippet", "")
    if snippet:
        return f"{heading} Pattern de référence ({label})\n```python\n{snippet}\n```"
    return f"{heading} Pattern de référence ({label})\n_(aucun snippet disponible)_"


def _render_schema_block(schema: dict, version: str) -> str:
    """Render a model schema as a concise reference section for the compiled prompt."""
    if not schema:
        return ""
    model = schema.get("model", "")
    label = schema.get("label", "")
    block = f"## Schéma du modèle : `{model}` — {label}\n"

    key_fields = schema.get("key_fields", {})
    if key_fields:
        block += "**Champs clés :**\n"
        for field, desc in key_fields.items():
            block += f"- `{field}` : {desc}\n"

    common_methods = schema.get("common_methods", [])
    if common_methods:
        block += "\n**Méthodes utiles :**\n"
        for method in common_methods:
            block += f"- `{method}`\n"

    version_note = schema.get("version_notes", {}).get(version, "")
    if version_note:
        block += f"\n**Note Odoo {version} :** {version_note}\n"

    return block


def compile_prompt(user_input: str, version: str, provider: str = None, api_key: str = None) -> dict:
    """
    Entrée  : input naturel du développeur + version Odoo choisie
    Sortie  : Dictionnaire contenant le prompt compilé et une indication si c'est un fallback
    """
    intents, is_fallback = parse_intent(user_input, provider, api_key)

    # Rule 1: simple query → 1 topic max
    word_count = len(user_input.split())
    if word_count < SIMPLE_QUERY_WORD_LIMIT:
        intents = intents[:1]

    # Rule 2: max 2 topics
    intents = intents[:2]

    primary = load_snippet(version, intents[0])

    if not primary:
        return {
            "prompt": f"Tu es expert Odoo {version}. Tâche : {user_input}",
            "is_fallback": True
        }

    # Secondary: from parser result OR auto-filled from primary's related_topics
    secondary = []
    if len(intents) > 1:
        s = load_snippet(version, intents[1])
        if s:
            secondary.append(s)
    elif word_count >= SIMPLE_QUERY_WORD_LIMIT:
        for related in primary.get("related_topics", []):
            if related != intents[0]:
                s = load_snippet(version, related)
                if s:
                    secondary.append(s)
                    break

    # Rules & anti-patterns (primary only — Rule 3)
    rules_block = "\n".join([f"  - {rule}" for rule in primary.get("rules", [])])
    anti_patterns_block = "\n".join([f"  {ap}" for ap in primary.get("anti_patterns", [])])

    # Advanced parameters triggered by user keywords
    advanced_blocks = []
    advanced_data = primary.get("advanced") or {}
    if not isinstance(advanced_data, dict):
        advanced_data = {}
    for adv_key, adv_val in advanced_data.items():
        if not isinstance(adv_val, dict):
            continue
        triggers = adv_val.get("trigger_keywords", [])
        if any(trigger.lower() in user_input.lower() for trigger in triggers):
            adv_text = f"  - [Avancé activé] Utiliser `{adv_val.get('snippet', '')}` : {adv_val.get('warning', '')}"
            advanced_blocks.append(adv_text)

    if advanced_blocks:
        rules_block += "\n\n## Paramètres avancés requis par le contexte :\n"
        rules_block += "\n".join(advanced_blocks)

    # Breaking changes for the target Odoo version
    breaking_changes = primary.get("breaking_changes", [])
    breaking_block = "\n".join([f"  - {bc}" for bc in breaking_changes]) if breaking_changes else ""

    # Code snippets block
    code_block = _render_code_block(primary)
    if secondary:
        code_block += "\n\n## Contexte complémentaire\n"
        for s in secondary:
            code_block += _render_code_block(s, heading="###") + "\n"

    # Model schema (fields + methods) detected from user input
    schema = detect_schema(user_input)
    schema_block = _render_schema_block(schema, version)

    # Combined imports from primary + secondary
    imports: set[str] = set()

    def add_imports(imp_data):
        if not imp_data:
            return
        if isinstance(imp_data, list):
            for i in imp_data:
                imports.add(i)
        else:
            imports.add(imp_data)

    add_imports(primary.get("imports"))
    for s in secondary:
        add_imports(s.get("imports"))

    imports_block = "\n".join(sorted(imports))

    breaking_section = (
        f"\n## Changements critiques Odoo {version}\n{breaking_block}\n"
        if breaking_block else ""
    )

    schema_section = f"\n{schema_block}" if schema_block else ""

    compiled_prompt = f"""Tu es un expert développeur Odoo {version}.
Génère uniquement du code fonctionnel, sans explication, sans commentaire superflu.

## Contraintes strictes Odoo {version}
{rules_block}
{breaking_section}
## Imports requis
```python
{imports_block}
```

{code_block}
{schema_section}
## À ne PAS faire
{anti_patterns_block}

## Tâche demandée
{user_input}

## Format de réponse attendu
- Code Python/XML uniquement
- Respecte les conventions de nommage Odoo {version} (snake_case, préfixes _compute_ / _onchange_ / _check_)
- Si plusieurs fichiers : indique le nom de chaque fichier en commentaire
- Aucune explication, aucune phrase introductive
"""
    return {
        "prompt": compiled_prompt,
        "is_fallback": is_fallback
    }
