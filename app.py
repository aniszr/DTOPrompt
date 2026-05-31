import json
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from llm_client import call_llm
from prompt_compiler import compile_prompt

CONFIG_PATH = Path(__file__).parent / "ai_config.json"

app = FastAPI(title="Odoo Prompt Optimizer")
logging.basicConfig(level=logging.INFO)

# ✅ Middleware DOIT être enregistré AVANT les routes et les mounts
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
# Modèles Pydantic
# ──────────────────────────────────────────────

class CompileRequest(BaseModel):
    input: str
    version: str
    provider: str | None = None
    api_key: str | None = None

class RefineRequest(BaseModel):
    compiled_prompt: str
    user_input: str
    provider: str
    api_key: str | None = None

# ──────────────────────────────────────────────
# Routes API
# ──────────────────────────────────────────────

def load_ai_config() -> dict:
    if not CONFIG_PATH.exists():
        return {"provider": "anthropic", "api_key": None}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"provider": "anthropic", "api_key": None}

def save_ai_config(provider: str, api_key: str | None) -> None:
    CONFIG_PATH.write_text(
        json.dumps({"provider": provider, "api_key": api_key}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/ai-config")
def get_ai_config():
    return load_ai_config()

@app.post("/api/ai-config")
def post_ai_config(config: dict):
    provider = config.get("provider")
    api_key = config.get("api_key")
    if not provider:
        raise HTTPException(status_code=400, detail="Provider manquant.")
    save_ai_config(provider, api_key)
    return {"status": "ok"}

@app.post("/compile-prompt")
def compile_endpoint(request: CompileRequest):
    try:
        result = compile_prompt(request.input, request.version, request.provider, request.api_key)
    except Exception:
        logging.exception("compile_endpoint failed")
        raise HTTPException(status_code=500, detail="Erreur interne lors de la compilation du prompt.")

    return {
        "compiled_prompt": result["prompt"],
        "is_fallback": result["is_fallback"]
    }

_REFINE_SYSTEM_PROMPT = """Tu es un META-PROMPT ENGINEER spécialisé sur Odoo.
Ton UNIQUE but est de formuler le prompt idéal qu'un développeur donnera à une IA génératrice de code (Cursor, Copilot, ChatGPT, etc.).
TU N'ES PAS LE DÉVELOPPEUR ODOO. TU NE DOIS GÉNÉRER AUCUN CODE FONCTIONNEL POUR RÉPONDRE À LA DEMANDE UTILISATEUR.

Tu vas recevoir :
1. L'input du développeur (ce qu'il veut créer).
2. Le contexte brut compilé (Règles techniques, anti-patterns et snippets Odoo).

Ta tâche est de construire un PROMPT (des instructions) destiné à l'agent codeur.
Ton output doit être le prompt lui-même, prêt à être copié-collé, et RIEN D'AUTRE.

Structure du prompt que tu dois générer (tu peux l'adapter, mais garde cet esprit) :
---
[Rôle]
Agis comme un développeur expert Odoo.

[Contexte et Tâche]
Voici la tâche à réaliser :
{Reformulation très claire, précise et technique de l'input du développeur}

[Règles Techniques Strictes]
{Synthèse des règles et anti-patterns fournis, formulées sous forme d'ordres IMPÉRATIFS pour l'IA codeuse. Ne garde que ce qui est pertinent pour sa tâche.}

[Code de Référence / Snippets]
Inspire-toi strictement de ces exemples (Pattern de référence) :
{Les snippets pertinents issus du contexte}

[Format de Sortie Attendu]
Génère UNIQUEMENT le code (Python/XML), sans blabla, sans explications.
---

RÈGLE D'OR : NE CODE SURTOUT PAS LA SOLUTION.
Si l'utilisateur demande "Crée un modèle patient", tu NE DOIS PAS écrire `class Patient(models.Model):`.
Tu dois écrire un texte du genre : "Crée un modèle patient en respectant les règles suivantes...".
Réponds UNIQUEMENT avec le prompt optimisé, sans aucune phrase d'introduction."""


@app.post("/refine-prompt")
def refine_prompt(request: RefineRequest):
    api_key = request.api_key
    if not api_key:
        raise HTTPException(status_code=401, detail="Clé API manquante.")

    user_content = f"Input développeur : {request.user_input}\n\nContexte brut compilé :\n{request.compiled_prompt}"

    try:
        refined, token_count = call_llm(request.provider, api_key, _REFINE_SYSTEM_PROMPT, user_content, max_tokens=1024)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not refined:
        refined = "⚠️ L'IA a renvoyé une réponse vide."
    logging.info("Refine prompt — provider: %s, length: %d", request.provider, len(refined))
    return {"refined_prompt": refined, "token_count": token_count}

# ──────────────────────────────────────────────
# Fichiers statiques — montés EN DERNIER
# ──────────────────────────────────────────────

# Route racine → index.html directement (sans redirect)
@app.get("/")
@app.get("/index.html")
def read_root():
    return FileResponse("index.html")

# Servir style.css et js/ depuis le dossier static
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
