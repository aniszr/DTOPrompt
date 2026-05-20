import re
import json
import anthropic
import openai
from google import genai

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
    et un booléen indiquant si on a utilisé le fallback.
    Utilise l'IA pour l'analyse sémantique si la clé API est fournie, sinon utilise les Regex.
    """
    valid_topics = list(INTENT_MAP.values())
    
    # --- V2: SÉMANTIQUE (IA) ---
    if provider and api_key:
        system_prompt = f"""Tu es un routeur sémantique expert Odoo. Ta tâche est de classer la demande de l'utilisateur dans une ou maximum deux des catégories suivantes : {', '.join(set(valid_topics))}.
Si la demande correspond à une "vue formulaire", renvoie "view_form". Si c'est un "champ calculé", "compute_field", etc.
Réponds UNIQUEMENT par les noms des catégories séparés par une virgule. Aucune autre phrase.
Si tu ne trouves aucune catégorie pertinente, réponds 'model'."""
        try:
            ai_response = ""
            if provider == "anthropic":
                client = anthropic.Anthropic(api_key=api_key)
                message = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=50,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_input}]
                )
                ai_response = message.content[0].text if message.content else ""
            elif provider in ("openai", "chatgpt"):
                client = openai.OpenAI(api_key=api_key)
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_input}
                    ]
                )
                ai_response = response.choices[0].message.content if response.choices else ""
            elif provider == "gemini":
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=user_input,
                    config=genai.types.GenerateContentConfig(
                        system_instruction=system_prompt,
                    ),
                )
                ai_response = response.text if response.text else ""
            
            # Extraction des topics depuis la réponse de l'IA
            found_ai = [t.strip() for t in ai_response.split(',') if t.strip() in valid_topics]
            if found_ai:
                return found_ai[:2], False
        except Exception as e:
            print(f"Erreur du parser sémantique IA : {e}. Fallback sur les Regex.")
            pass # Si l'IA échoue (clé invalide etc), on fallback sur les Regex
            
    # --- V1: REGEX (Fallback) ---
    # 1. Nettoyer l'entrée (espaces, retours chariot)
    clean_input = user_input.replace("\n", " ").strip()
    
    found = []
    
    # 2. Chercher les correspondances exactes via Regex
    for pattern, topic in INTENT_MAP.items():
        if re.search(pattern, clean_input, re.IGNORECASE):
            if topic not in found:
                found.append(topic)

    # 3. Règles métiers anti Faux-Positifs
    # Ex: Si on demande "vue formulaire", le mot "formulaire" peut parfois déclencher 'model' si on a mal filtré, 
    # mais surtout, on ne veut pas injecter 'model.json' si l'utilisateur ne parle que d'une vue existante.
    views_topics = ["view_form", "view_tree", "view_kanban"]
    if any(view in found for view in views_topics):
        # Si on a détecté un modèle mais que la phrase ne dit pas "créer un modèle", on retire 'model' pour ne garder que la vue.
        if "model" in found and not re.search(r"\b(nouveau|créer).*(modèle|model)\b", clean_input, re.IGNORECASE):
            found.remove("model")
            
    # Si on détecte "action" dans "tâche planifiée (action scheduled)", enlever action_menu si cron est là
    if "cron" in found and "action_menu" in found:
        if not re.search(r"\b(menu|bouton|ir\.actions\.act_window)\b", clean_input, re.IGNORECASE):
            found.remove("action_menu")

    # 4. Fallback par défaut si aucune détection
    if not found:
        # On pourrait renvoyer "model" ou "compute_field" comme point de départ
        return ["model"], True 

    # 5. Limiter à 2 topics maximum pour garder un prompt concentré
    return found[:2], False
