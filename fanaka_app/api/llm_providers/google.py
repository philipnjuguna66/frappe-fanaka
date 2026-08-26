"""Google adapter -- direct Gemini API, not routed through OpenRouter.

See specs/recruitment_ai_screening.md (Phase 1/2) for the plan this implements.

API shape verified live 2026-08-26 against ai.google.dev's docs -- genuinely different
from the OpenAI-shaped APIs (OpenRouter/OpenAI/Anthropic-with-modification):
- Auth is a `key` query param, not a header.
- Request body is `contents: [{role, parts: [{text}]}]`, not `messages`.
- System prompt goes in a separate top-level `systemInstruction` field.
- JSON mode is `generationConfig.responseMimeType: "application/json"`.
- Response text is at `candidates[0].content.parts[0].text`.
- Model list field is `models`, not `data`, and each `name` is prefixed `models/`.
"""

import json

import frappe
import requests
from frappe import _

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


def list_models(api_key: str) -> list[dict]:
	api_key = (api_key or "").strip()
	if not api_key:
		frappe.throw(_("Google API Key is required to list models."))

	response = requests.get(f"{BASE_URL}/models", params={"key": api_key, "pageSize": 1000}, timeout=15)
	response.raise_for_status()
	models = response.json().get("models", [])
	return [
		{"value": m["name"].removeprefix("models/"), "description": m.get("displayName", m["name"])}
		for m in models
	]


def chat_completion(*, model: str, api_key: str, messages: list[dict], timeout: int = 90) -> dict:
	api_key = (api_key or "").strip()
	if not api_key:
		frappe.throw(_("Google API Key is not configured in Recruitment AI Settings."))
	if not model:
		frappe.throw(_("Model is not configured in Recruitment AI Settings."))

	system_prompt, contents = _to_gemini_contents(messages)
	body = {
		"contents": contents,
		"generationConfig": {"responseMimeType": "application/json"},
	}
	if system_prompt:
		body["systemInstruction"] = {"parts": [{"text": system_prompt}]}

	try:
		response = requests.post(
			f"{BASE_URL}/models/{model}:generateContent",
			params={"key": api_key},
			json=body,
			timeout=timeout,
		)
	except requests.exceptions.RequestException as e:
		frappe.throw(_("Could not reach Google: {0}").format(str(e)))

	if response.status_code != 200:
		frappe.throw(_("Google request failed ({0}): {1}").format(response.status_code, response.text[:500]))

	try:
		text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
		return json.loads(text)
	except (KeyError, IndexError, json.JSONDecodeError) as e:
		frappe.throw(_("Google returned an unexpected response shape: {0}").format(str(e)))


def _to_gemini_contents(messages: list[dict]) -> tuple[str, list[dict]]:
	"""Gemini has no "system" role in `contents` -- system prompt is a separate
	top-level field, and roles are "user"/"model" (not "assistant")."""
	system_parts = [m["content"] for m in messages if m.get("role") == "system"]
	role_map = {"user": "user", "assistant": "model"}
	contents = [
		{"role": role_map.get(m.get("role"), "user"), "parts": [{"text": m["content"]}]}
		for m in messages
		if m.get("role") != "system"
	]
	return "\n\n".join(system_parts), contents
