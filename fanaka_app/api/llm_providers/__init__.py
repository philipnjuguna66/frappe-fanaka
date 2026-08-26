"""Registry of LLM provider adapters for AI recruitment screening.

Each adapter module exposes two functions with a common signature:
- ``list_models(api_key: str) -> list[dict]`` -- ``[{"value": slug, "description": name}]``
- ``chat_completion(*, model, api_key, messages, timeout=90) -> dict`` -- parsed JSON
  object from the model's response, given OpenAI-shaped ``messages``
  (``[{"role": "system"|"user", "content": str}]``); each adapter translates that into
  whatever shape its own vendor API actually wants.

Adding a new provider is: write one module with those two functions, add it here.
Nothing else in the app (settings doctype, screening job) needs to change.
See specs/recruitment_ai_screening.md for the plan this implements.
"""

from fanaka_app.api.llm_providers import anthropic, google, openai, openrouter

PROVIDERS = {
	"Anthropic": anthropic,
	"OpenAI": openai,
	"Google": google,
	"OpenRouter": openrouter,
}


def get_adapter(provider: str):
	adapter = PROVIDERS.get(provider)
	if not adapter:
		import frappe
		from frappe import _

		frappe.throw(_("Unknown AI provider: {0}").format(provider))
	return adapter
