"""OpenRouter adapter -- one of several LLM providers Recruitment AI Settings can use.

Kept as a catch-all: OpenRouter itself proxies many vendors' models behind one API.
See specs/recruitment_ai_screening.md (Phase 1/2) for the plan this implements.
"""

import json

import frappe
import requests
from frappe import _

BASE_URL = "https://openrouter.ai/api/v1"
MODELS_CACHE_KEY = "fanaka_app:llm_providers:openrouter:models"
MODELS_CACHE_TTL = 6 * 60 * 60  # 6 hours -- OpenRouter adds/retires models over time


def list_models(api_key: str = "") -> list[dict]:
	"""OpenRouter's model list is public -- confirmed `GET /models` returns 200 with no
	Authorization header (verified 2026-08-26) -- so api_key is accepted for interface
	consistency with the other adapters but unused here."""
	models = frappe.cache.get_value(MODELS_CACHE_KEY)
	if models is None:
		response = requests.get(f"{BASE_URL}/models", timeout=15)
		response.raise_for_status()
		models = response.json().get("data", [])
		frappe.cache.set_value(MODELS_CACHE_KEY, models, expires_in_sec=MODELS_CACHE_TTL)

	return [{"value": m["id"], "description": m.get("name", m["id"])} for m in models]


def chat_completion(*, model: str, api_key: str, messages: list[dict], timeout: int = 90) -> dict:
	# Guards against a whitespace-only key slipping past `if not api_key` and reaching
	# OpenRouter as a technically-present-but-blank Authorization header -- OpenRouter
	# reports that as "Missing Authentication header", which reads like the header
	# never arrived at all and is easy to mistake for a code bug rather than bad config.
	api_key = (api_key or "").strip()
	if not api_key:
		frappe.throw(_("OpenRouter API Key is not configured in Recruitment AI Settings."))
	if not model:
		frappe.throw(_("Model is not configured in Recruitment AI Settings."))

	try:
		response = requests.post(
			f"{BASE_URL}/chat/completions",
			headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
			json={"model": model, "messages": messages, "response_format": {"type": "json_object"}},
			timeout=timeout,
		)
	except requests.exceptions.RequestException as e:
		frappe.throw(_("Could not reach OpenRouter: {0}").format(str(e)))

	if response.status_code != 200:
		frappe.throw(_("OpenRouter request failed ({0}): {1}").format(response.status_code, response.text[:500]))

	try:
		content = response.json()["choices"][0]["message"]["content"]
		return json.loads(content)
	except (KeyError, IndexError, json.JSONDecodeError) as e:
		frappe.throw(_("OpenRouter returned an unexpected response shape: {0}").format(str(e)))
