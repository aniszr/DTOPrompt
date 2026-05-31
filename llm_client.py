import logging


def call_llm(provider: str, api_key: str, system: str, user: str, max_tokens: int = 1024) -> tuple[str, int | None]:
    """Dispatch an LLM call to the given provider. Returns (response_text, total_token_count)."""
    if provider == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=max_tokens,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
        )
        text = message.content[0].text if message.content else ""
        usage = message.usage
        token_count = (usage.input_tokens + usage.output_tokens) if usage else None
        return text, token_count

    elif provider in ("openai", "chatgpt"):
        import openai
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        text = response.choices[0].message.content if response.choices else ""
        token_count = response.usage.total_tokens if response.usage else None
        return text, token_count

    elif provider == "gemini":
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user,
            config=genai.types.GenerateContentConfig(system_instruction=system),
        )
        text = response.text if response.text else ""
        meta = getattr(response, "usage_metadata", None)
        token_count = getattr(meta, "total_token_count", None) if meta else None
        return text, token_count

    else:
        raise ValueError(f"Fournisseur IA non supporté : {provider}")
