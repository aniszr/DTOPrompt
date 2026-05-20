// Persistance session + badge visuel
function setVersion(v) {
  sessionStorage.setItem("odoo_version", v);
  const badge = document.getElementById("version-badge");
  if (v) {
    badge.textContent = `Odoo ${v}`;
    badge.classList.remove("hidden");
  } else {
    badge.classList.add("hidden");
  }
}

// Restaure la version au rechargement
async function fetchServerApiConfig() {
  try {
    const res = await fetch("/api/ai-config");
    if (!res.ok) return null;
    return await res.json();
  } catch (error) {
    console.warn("Impossible de charger la configuration serveur.", error);
    return null;
  }
}

window.addEventListener("DOMContentLoaded", async () => {
  const saved = sessionStorage.getItem("odoo_version");
  if (saved) {
    document.getElementById("odoo-version").value = saved;
    setVersion(saved);
  }
  
  // Load API key & provider from localStorage first
  const provider = localStorage.getItem("ai_provider") || "anthropic";
  document.getElementById("aiProvider").value = provider;
  const key = localStorage.getItem(`api_key_${provider}`);
  if (key) {
    document.getElementById("apiKeyInput").value = key;
  }

  // If browser storage is empty, try server-side persisted config
  if (!key) {
    const serverConfig = await fetchServerApiConfig();
    if (serverConfig) {
      document.getElementById("aiProvider").value = serverConfig.provider || provider;
      if (serverConfig.api_key) {
        document.getElementById("apiKeyInput").value = serverConfig.api_key;
        localStorage.setItem("ai_provider", serverConfig.provider || provider);
        localStorage.setItem(`api_key_${serverConfig.provider || provider}`, serverConfig.api_key);
      }
    }
  }

  updateApiKeyPlaceholder();
});

// Modal Logic
function showApiConfigModal() {
  const provider = document.getElementById("aiProvider").value;
  const key = localStorage.getItem(`api_key_${provider}`);
  document.getElementById("apiKeyInput").value = key || "";
  document.getElementById("apiModal").classList.add("show");
}

function hideApiConfigModal() {
  document.getElementById("apiModal").classList.remove("show");
}

function updateApiKeyPlaceholder() {
  const provider = document.getElementById("aiProvider").value;
  const input = document.getElementById("apiKeyInput");
  
  // Auto-fill if we have a key for the newly selected provider
  const key = localStorage.getItem(`api_key_${provider}`);
  input.value = key || "";

  if (provider === "anthropic") input.placeholder = "sk-ant-...";
  else if (provider === "openai" || provider === "chatgpt") input.placeholder = "sk-proj-...";
  else if (provider === "gemini") input.placeholder = "AIza...";
}

async function saveApiConfig() {
  const provider = document.getElementById("aiProvider").value;
  const key = document.getElementById("apiKeyInput").value.trim();
  
  localStorage.setItem("ai_provider", provider);
  if (key) {
    localStorage.setItem(`api_key_${provider}`, key);
  }

  try {
    await fetch("/api/ai-config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider, api_key: key })
    });
  } catch (error) {
    console.warn("Impossible d'enregistrer la configuration sur le serveur.", error);
  }

  hideApiConfigModal();
}

function copyToClipboard() {
  const outputText = document.getElementById("output").textContent;
  navigator.clipboard.writeText(outputText).then(() => {
    const btn = document.getElementById("copy-btn");
    const originalText = btn.textContent;
    btn.textContent = "✅ Copié !";
    setTimeout(() => btn.textContent = originalText, 2000);
  });
}

// Compilation et Appel API
async function optimizePrompt() {
  const version = sessionStorage.getItem("odoo_version");
  const userInput = document.getElementById("user-input").value.trim();
  
  const provider = document.getElementById("aiProvider").value;
  const apiKey = localStorage.getItem(`api_key_${provider}`);
  
  const generateBtn = document.getElementById("generate-btn");

  // Garde-fou : version obligatoire
  if (!version) {
    alert("Veuillez sélectionner une version Odoo avant de continuer.");
    return;
  }
  if (!userInput) {
    alert("Veuillez décrire votre besoin.");
    return;
  }
  
  try {
    generateBtn.textContent = "⚙️ 1. Compilation Locale...";
    generateBtn.disabled = true;

    // 1. Appel backend pour compiler le prompt brut (0 token si pas de clé, sémantique si clé)
    const compileRes = await fetch("/compile-prompt", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ 
        input: userInput, 
        version: version,
        provider: provider,
        api_key: apiKey
      })
    });

    if (!compileRes.ok) throw new Error("Erreur lors de la compilation du prompt");
    const compileData = await compileRes.json();

    if (compileData.is_fallback) {
      alert("⚠️ Topic non reconnu, résultat basé sur le pattern compute par défaut.");
    }

    // Affiche le prompt compilé brut
    document.getElementById("compiled-prompt-preview").textContent = compileData.compiled_prompt;

    if (!apiKey) {
      alert("Contexte brut compilé ! Pour que l'IA l'optimise, veuillez configurer votre clé API.");
      document.getElementById("output").textContent = "En attente de la clé API pour raffiner le prompt...";
      document.getElementById("token-stats").style.display = "none";
      generateBtn.textContent = "✨ Compiler & Affiner";
      generateBtn.disabled = false;
      return;
    }

    // 2. Appel backend pour raffiner le prompt (IA Refiner)
    generateBtn.textContent = "✨ 2. Affinage par l'IA...";
    document.getElementById("output").textContent = "L'IA est en train d'optimiser votre prompt...";
    
    const refineRes = await fetch("/refine-prompt", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ 
        compiled_prompt: compileData.compiled_prompt,
        user_input: userInput,
        provider: provider,
        api_key: apiKey
      })
    });

    if (!refineRes.ok) {
        const err = await refineRes.json();
        throw new Error(err.detail || "Erreur lors de l'affinage par l'IA");
    }
    
    const refineData = await refineRes.json();
    if (!refineData.refined_prompt || refineData.refined_prompt.trim() === "") {
      document.getElementById("output").textContent = "⚠️ L'IA a renvoyé une réponse vide. Veuillez reformuler votre demande ou vérifier vos quotas/clés API.";
      const tokenStats = document.getElementById("token-stats");
      tokenStats.textContent = "Tokens utilisés : non disponible";
      tokenStats.style.display = "block";
    } else {
      document.getElementById("output").textContent = refineData.refined_prompt;
      const tokenStats = document.getElementById("token-stats");
      if (refineData.token_count != null) {
        tokenStats.textContent = `Tokens utilisés : ${refineData.token_count}`;
      } else {
        tokenStats.textContent = "Tokens utilisés : non disponible";
      }
      tokenStats.style.display = "block";
    }

  } catch (error) {
    console.error("Erreur:", error);
    alert(error.message);
    document.getElementById("output").textContent = "Une erreur s'est produite.";
  } finally {
    generateBtn.textContent = "✨ Compiler & Affiner";
    generateBtn.disabled = false;
  }
}
