import json
from prompt_compiler import compile_prompt, parse_intent

test_cases = [
    {
        "name": "1. Test de base (Compute sans mot-clé avancé)",
        "input": "je veux un champ calculé qui somme le total",
        "version": "18"
    },
    {
        "name": "2. Test de l'Intent Parser strict (évite faux positifs)",
        "input": "créer un champ compute sans @api.depends",
        "version": "18"
    },
    {
        "name": "3. Test des Paramètres Avancés (Precompute)",
        "input": "créer un champ calculé avec precompute avant insertion",
        "version": "18"
    },
    {
        "name": "4. Test Multi-Topics (Primaire + Secondaire)",
        "input": "ajouter un onchange sur la date, et bloquer si la date est dans le passé (contrainte)",
        "version": "18"
    },
    {
        "name": "5. Test du Fallback (Hors scope complet)",
        "input": "Je veux créer une banane rouge",
        "version": "18"
    },
    {
        "name": "6. Test Architecture V2 (Contexte Technique)",
        "input": "créer une contrainte sur les dates pour qu'elles soient logiques",
        "version": "19"
    }
]

for i, test in enumerate(test_cases, 1):
    print(f"\\n{'='*50}\\n🔍 {test['name']}\\nInput: '{test['input']}'\\n{'-'*50}")
    
    intents, is_fallback = parse_intent(test["input"])
    print(f"Topics détectés : {intents} (Fallback: {is_fallback})")
    
    result = compile_prompt(test["input"], test["version"])
    prompt = result["prompt"]
    
    # Analyze the prompt
    lines = prompt.split('\\n')
    advanced_found = any("[Avancé activé]" in line for line in lines)
    
    print(f"Longueur du prompt : {len(prompt)} caractères")
    context_found = any("## Contexte Technique" in line for line in lines)
    print(f"Paramètres avancés injectés ? {'Oui' if advanced_found else 'Non'}")
    print(f"Contexte sémantique (V2) injecté ? {'Oui' if context_found else 'Non (V1/Snippet)'}")
    
    print("\\n[Extrait des règles et directives injectées]")
    for line in lines:
        if line.startswith("## À ne PAS faire"):
            break
        if line.strip() and not line.startswith("Tu es un expert") and not line.startswith("Génère uniquement"):
            print(line)
