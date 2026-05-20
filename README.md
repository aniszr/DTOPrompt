# Odoo Prompt Compiler

Ce projet implémente une architecture de **Prompt Compilation** sans appel LLM pour la récupération de contexte (Zéro LLM Retrieval).

## Lancer le projet

1. Installez les dépendances :
   ```bash
   pip install -r requirements.txt
   ```

2. Lancez le serveur FastAPI :
   ```bash
   uvicorn app:app --reload
   ```

3. Ouvrez votre navigateur sur `http://127.0.0.1:8000/static/index.html`

## Ajouter un nouveau Topic JSON

Pour ajouter de nouvelles connaissances à l'outil (ex: `nouvelle_api.json`) :

1. Créez un fichier dans `knowledge/v17/`, `v18/`, ou `v19/` selon la version visée :
   ```json
   {
     "version": "19",
     "topic": "nouvelle_api",
     "label": "Nouvelle API Odoo",
     "imports": "from odoo import api",
     "snippet": "def ...",
     "rules": ["Règle 1", "Règle 2"],
     "anti_patterns": ["❌ Erreur fréquente"],
     "related_topics": [],
     "difficulty": "advanced",
     "last_updated": "2026-05-19"
   }
   ```

2. Ajoutez le mot-clé Regex correspondant dans `intent_parser.py` (dictionnaire `INTENT_MAP`) :
   ```python
   INTENT_MAP = {
       # ...
       r"nouvell.*api|new.*api": "nouvelle_api",
   }
   ```

C'est tout ! Le routeur trouvera automatiquement votre fichier et l'ajoutera au prompt compilé si le mot-clé est détecté dans la demande du développeur.
