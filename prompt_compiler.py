import json
import logging
import os
from intent_parser import parse_intent

KNOWLEDGE_BASE_PATH = os.path.join(os.path.dirname(__file__), "knowledge")

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

def compile_prompt(user_input: str, version: str, provider: str = None, api_key: str = None) -> dict:
    """
    Entrée  : input naturel du développeur + version Odoo choisie
    Sortie  : Dictionnaire contenant le prompt compilé et une indication si c'est un fallback
    """
    intents, is_fallback = parse_intent(user_input, provider, api_key)
    
    # Règle 1 : 1 seul topic si la phrase est simple (< 15 mots)
    word_count = len(user_input.split())
    if word_count < 15:
        intents = intents[:1]
        
    # Règle 2 : max 2 topics même pour les phrases longues
    intents = intents[:2]

    # Séparation Primaire / Secondaire
    primary = load_snippet(version, intents[0])
    secondary = []
    if len(intents) > 1:
        s = load_snippet(version, intents[1])
        if s:
            secondary.append(s)

    if not primary:
        return {
            "prompt": f"Tu es expert Odoo {version}. Tâche : {user_input}",
            "is_fallback": True
        }

    # Règle 3 : Règles et anti-patterns uniquement pour le primaire
    rules_block = "\n".join([f"  - {rule}" for rule in primary.get("rules", [])])
    anti_patterns_block = "\n".join([f"  {ap}" for ap in primary.get("anti_patterns", [])])
    
    # Injection avancée : paramètres contextuels (ex: precompute)
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

    # Context / Snippets
    if "context" in primary:
        code_block = f"## Contexte Technique ({primary.get('label', '')})\n"
        for k, v in primary["context"].items():
            if isinstance(v, list):
                code_block += f"- **{k.capitalize()}** : {', '.join(v)}\n"
            else:
                code_block += f"- **{k.capitalize()}** : {v}\n"
    else:
        code_block = f"## Pattern de référence ({primary.get('label', '')})\n```python\n{primary.get('snippet', '')}\n```"

    if secondary:
        code_block += "\n\n## Contexte complémentaire\n"
        for s in secondary:
            if "context" in s:
                code_block += f"### {s.get('label', '')}\n"
                for k, v in s["context"].items():
                    if isinstance(v, list):
                        code_block += f"- **{k.capitalize()}** : {', '.join(v)}\n"
                    else:
                        code_block += f"- **{k.capitalize()}** : {v}\n"
            else:
                code_block += f"### {s.get('label', '')}\n```python\n{s.get('snippet', '')}\n```\n"

    # Imports combinés
    imports = set()
    def add_imports(imp_data):
        if not imp_data: return
        if isinstance(imp_data, list):
            for i in imp_data: imports.add(i)
        else:
            imports.add(imp_data)
            
    add_imports(primary.get("imports"))
    for s in secondary:
        add_imports(s.get("imports"))
        
    imports_block = "\n".join(sorted(imports))

    compiled_prompt = f"""Tu es un expert développeur Odoo {version}.
Génère uniquement du code fonctionnel, sans explication, sans commentaire superflu.

## Contraintes strictes Odoo {version}
{rules_block}

## Imports requis
```python
{imports_block}
```

{code_block}

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
