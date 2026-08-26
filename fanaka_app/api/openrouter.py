"""OpenRouter client: model picker for Recruitment AI Settings + chat completion helper
used by the AI resume screening job.

See specs/recruitment_ai_screening.md (Phase 1 settings, Phase 2 analysis) for the plan
this implements. OpenRouter's `/models` endpoint is public (no API key needed, verified
2026-08-26) and returns `{"data": [{"id": "vendor/model-slug", "name": ..., ...}, ...]}` --
`id` is exactly the string OpenRouter's chat-completions `model` param expects.
"""

import json

import frappe
import requests
from frappe import _

BASE_URL = "https://openrouter.ai/api/v1"
MODELS_CACHE_KEY = "fanaka_app:openrouter:models"
MODELS_CACHE_TTL = 6 * 60 * 60  # 6 hours -- OpenRouter adds/retires models over time


def _cached_models() -> list[dict]:
	models = frappe.cache.get_value(MODELS_CACHE_KEY)
	if models is not None:
		return models

	response = requests.get(f"{BASE_URL}/models", timeout=15)
	response.raise_for_status()
	models = response.json().get("data", [])

	frappe.cache.set_value(MODELS_CACHE_KEY, models, expires_in_sec=MODELS_CACHE_TTL)
	return models


@frappe.whitelist()
def get_providers() -> list[str]:
	"""Distinct providers, derived from the `vendor` prefix of each model id."""
	frappe.only_for(("System Manager", "HR Manager"))
	providers = {m["id"].split("/", 1)[0] for m in _cached_models() if "/" in m.get("id", "")}
	return sorted(providers)


@frappe.whitelist()
def get_models(provider: str) -> list[dict]:
	"""Models for one provider, for the Model select's `frm.set_query`."""
	frappe.only_for(("System Manager", "HR Manager"))
	return [
		{"value": m["id"], "description": m.get("name", m["id"])}
		for m in _cached_models()
		if m.get("id", "").startswith(f"{provider}/")
	]


def chat_completion(*, model: str, api_key: str, messages: list[dict], timeout: int = 90) -> dict:
	"""Call OpenRouter's chat-completions endpoint and return the parsed JSON message content.

	Expects the model to return a JSON object in its message content (requested via
	`response_format`). Raises `frappe.ValidationError` with a clear, user-facing reason
	on any failure -- network, HTTP, or malformed-JSON -- since this always runs inside a
	background job where the failure otherwise disappears into the job's error log.
	"""
	if not api_key:
		frappe.throw(_("OpenRouter API Key is not configured in Recruitment AI Settings."))
	if not model:
		frappe.throw(_("OpenRouter provider/model is not configured in Recruitment AI Settings."))

	try:
		response = requests.post(
			f"{BASE_URL}/chat/completions",
			headers={
				"Authorization": f"Bearer {api_key}",
				"Content-Type": "application/json",
			},
			json={
				"model": model,
				"messages": messages,
				"response_format": {"type": "json_object"},
			},
			timeout=timeout,
		)
	except requests.exceptions.RequestException as e:
		frappe.throw(_("Could not reach OpenRouter: {0}").format(str(e)))

	if response.status_code != 200:
		frappe.throw(
			_("OpenRouter request failed ({0}): {1}").format(response.status_code, response.text[:500])
		)

	try:
		content = response.json()["choices"][0]["message"]["content"]
		return json.loads(content)
	except (KeyError, IndexError, json.JSONDecodeError) as e:
		frappe.throw(_("OpenRouter returned an unexpected response shape: {0}").format(str(e)))
