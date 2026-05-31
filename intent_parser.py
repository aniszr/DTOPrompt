import re
import logging
from llm_client import call_llm

INTENT_MAP = {
    # Core Model (Models, Mixins, Fields)
    r"\b(model|modèle|class\s+.*models\.(Model|AbstractModel)|_name\s*=|_description)\b": "model",

    # Compute Fields
    r"\b(compute|calculé|@api\.depends|precompute)\b|\b(somme|total).*ligne\b": "compute_field",

    # Onchange
    r"\b(onchange|@api\.onchange)\b|\b(quand|si|lorsque).*change(nt)?\b|\b(déclench|met à jour).*champ\b": "onchange",

    # Constraints & Validations
    r"\b(constraint|contrainte|@api\.constrains|_sql_constraints)\b|\bbloquer.*\b(si|quand)\b|\bempêcher\b|\bvalidation.*champ\b|\bunique\b": "constraint",

    # Views (Form, Tree, Kanban)
    r"\b(formulaire|vue form|form view|<form)\b": "view_form",
    r"\b(liste|vue tree|tree view|<tree)\b": "view_tree",
    r"\b(kanban|carte|card view|<kanban)\b": "view_kanban",

    # Actions and Menus
    r"\b(action|menuitem|ir\.actions|act_window|server action|action serveur)\b": "action_menu",

    # Wizard (TransientModel)
    r"\b(wizard|assistant|pop-?up|boîte de dialogue|dialog|models\.TransientModel)\b": "wizard",

    # Security (Access Rights, Record Rules)
    r"\b(security|sécurité|access rights|ir\.model\.access|ir\.rule|record rules?|group_user|groupe.*accès|droits)\b": "security",

    # Controllers & Routes
    r"\b(route|controller|endpoint|http|url|api.*rest|json.*route|http\.Controller)\b": "controller",

    # Reports (QWeb, PDF)
    r"\b(rapport|report|qweb|pdf|impression|imprimer|ir\.actions\.report|report_type)\b": "report_qweb",

    # Inheritance & Extensions
    r"\b(héritage|inherit|surcharge|override|extend|_inherit|_inherits|xpath)\b": "inheritance",

    # Migrations
    r"\b(migration|upgrade|script.*version|rename_column|create_column|pre_init_hook|post_init_hook)\b": "migration",

    # Cron / Scheduled actions
    r"\b(cron|tâche.*planifiée|scheduled.*action|automatique|ir\.cron|batching|tâche de fond)\b": "cron",

    # OWL / JS Framework
    r"\b(owl|javascript|js|composant.*web|component|frontend|interface.*utilisateur|@odoo\/owl)\b": "owl",
}

def parse_intent(user_input: str, provider: str = None, api_key: str = None) -> tuple[list[str], bool]:
    """
    Retourne la liste des topics détectés (max 2 pour éviter la dilution du contexte)
    et un booléen indiquant si on a utilisé le fallback (regex ou défaut, pas l'IA).
    """
    valid_topics = list(INTENT_MAP.values())
    ai_requested = bool(provider and api_key)

    # --- V2: SÉMANTIQUE (IA) ---
    if ai_requested:
        system_prompt = f"""Tu es un routeur sémantique expert Odoo. Ta tâche est de classer la demande de l'utilisateur dans une ou maximum deux des catégories suivantes : {', '.join(valid_topics)}.
Si la demande correspond à une "vue formulaire", renvoie "view_form". Si c'est un "champ calculé", "compute_field", etc.
Réponds UNIQUEMENT par les noms des catégories séparés par une virgule. Aucune autre phrase.
Si tu ne trouves aucune catégorie pertinente, réponds 'model'."""
        try:
            ai_response, _ = call_llm(provider, api_key, system_prompt, user_input, max_tokens=50)
            found_ai = [t.strip() for t in ai_response.split(',') if t.strip() in valid_topics]
            if found_ai:
                return found_ai[:2], False
        except Exception as e:
            logging.error("Parser sémantique IA échoué (%s). Fallback sur les Regex.", e)

    # --- V1: REGEX (Fallback) ---
    clean_input = user_input.replace("\n", " ").strip()
    found = []

    for pattern, topic in INTENT_MAP.items():
        if re.search(pattern, clean_input, re.IGNORECASE):
            if topic not in found:
                found.append(topic)

    views_topics = ["view_form", "view_tree", "view_kanban"]
    if any(view in found for view in views_topics):
        if "model" in found and not re.search(r"\b(nouveau|créer).*(modèle|model)\b", clean_input, re.IGNORECASE):
            found.remove("model")

    if "cron" in found and "action_menu" in found:
        if not re.search(r"\b(menu|bouton|ir\.actions\.act_window)\b", clean_input, re.IGNORECASE):
            found.remove("action_menu")

    if not found:
        return ["model"], True

    # is_fallback=True when AI was requested but failed and we fell back to regex
    return found[:2], ai_requested
