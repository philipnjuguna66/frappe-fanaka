"""OpenAI adapter -- direct GPT API, not routed through OpenRouter.

See specs/recruitment_ai_screening.md (Phase 1/2) for the plan this implements.

Note on verification: platform.openai.com's docs pages returned 403 to an automated
fetch (Cloudflare), so this wasn't confirmed against the docs directly. What IS
confirmed live (2026-08-26): `GET https://api.openai.com/v1/models` returns 401 with
no Authorization header, i.e. the endpoint exists and needs bearer auth. The request/
response shapes below are the standard OpenAI Chat Completions / Models API shape --
also the same shape OpenRouter deliberately mirrors and that this app's OpenRouter
adapter already exercises successfully against a real key, which is corroborating
evidence even without a direct OpenAI docs fetch.
"""

import json

import frappe
import requests
from frappe import _

BASE_URL = "https://api.openai.com/v1"


def list_models(api_key: str) -> list[dict]:
	if not api_key:
		frappe.throw(_("OpenAI API Key is required to list models."))

	response = requests.get(
		f"{BASE_URL}/models", headers={"Authorization": f"Bearer {api_key}"}, timeout=15
	)
	response.raise_for_status()
	models = response.json().get("data", [])
	return [{"value": m["id"], "description": m["id"]} for m in models]


def chat_completion(*, model: str, api_key: str, messages: list[dict], timeout: int = 90) -> dict:
	if not api_key:
		frappe.throw(_("OpenAI API Key is not configured in Recruitment AI Settings."))
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
		frappe.throw(_("Could not reach OpenAI: {0}").format(str(e)))

	if response.status_code != 200:
		frappe.throw(_("OpenAI request failed ({0}): {1}").format(response.status_code, response.text[:500]))

	try:
		content = response.json()["choices"][0]["message"]["content"]
		return json.loads(content)
	except (KeyError, IndexError, json.JSONDecodeError) as e:
		frappe.throw(_("OpenAI returned an unexpected response shape: {0}").format(str(e)))
