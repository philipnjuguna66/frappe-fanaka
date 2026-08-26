"""Anthropic adapter -- direct Claude API, not routed through OpenRouter.

See specs/recruitment_ai_screening.md (Phase 1/2) for the plan this implements.

API shape verified live 2026-08-26 against Anthropic's docs (platform.claude.com):
- Models: GET /v1/models, headers `x-api-key` + `anthropic-version`, no bearer scheme.
- Messages: POST /v1/messages -- system prompt is a top-level `system` field, NOT a
  message with role "system" (Anthropic rejects that role in `messages`), and
  `max_tokens` is mandatory. Response text is at `content[0].text`, not
  `choices[0].message.content` like the OpenAI-shaped APIs.
"""

import json

import frappe
import requests
from frappe import _

BASE_URL = "https://api.anthropic.com/v1"
ANTHROPIC_VERSION = "2023-06-01"
MAX_TOKENS = 4096


def _headers(api_key: str) -> dict:
	return {
		"x-api-key": api_key,
		"anthropic-version": ANTHROPIC_VERSION,
		"content-type": "application/json",
	}


def list_models(api_key: str) -> list[dict]:
	api_key = (api_key or "").strip()
	if not api_key:
		frappe.throw(_("Anthropic API Key is required to list models."))

	response = requests.get(f"{BASE_URL}/models", headers=_headers(api_key), params={"limit": 1000}, timeout=15)
	response.raise_for_status()
	models = response.json().get("data", [])
	return [{"value": m["id"], "description": m.get("display_name", m["id"])} for m in models]


def chat_completion(*, model: str, api_key: str, messages: list[dict], timeout: int = 90) -> dict:
	api_key = (api_key or "").strip()
	if not api_key:
		frappe.throw(_("Anthropic API Key is not configured in Recruitment AI Settings."))
	if not model:
		frappe.throw(_("Model is not configured in Recruitment AI Settings."))

	system_prompt, chat_messages = _split_system_prompt(messages)

	try:
		response = requests.post(
			f"{BASE_URL}/messages",
			headers=_headers(api_key),
			json={
				"model": model,
				"max_tokens": MAX_TOKENS,
				"system": system_prompt,
				"messages": chat_messages,
			},
			timeout=timeout,
		)
	except requests.exceptions.RequestException as e:
		frappe.throw(_("Could not reach Anthropic: {0}").format(str(e)))

	if response.status_code != 200:
		frappe.throw(_("Anthropic request failed ({0}): {1}").format(response.status_code, response.text[:500]))

	try:
		text = response.json()["content"][0]["text"]
		return _parse_json_response(text)
	except (KeyError, IndexError) as e:
		frappe.throw(_("Anthropic returned an unexpected response shape: {0}").format(str(e)))


def _split_system_prompt(messages: list[dict]) -> tuple[str, list[dict]]:
	"""Anthropic's Messages API takes the system prompt as its own top-level field --
	pull any role="system" entries out of the OpenAI-shaped messages list callers pass."""
	system_parts = [m["content"] for m in messages if m.get("role") == "system"]
	chat_messages = [m for m in messages if m.get("role") != "system"]
	return "\n\n".join(system_parts), chat_messages


def _parse_json_response(text: str) -> dict:
	"""Anthropic has no strict JSON-mode response_format (unlike the OpenAI-shaped
	APIs) -- the prompt asks for JSON only, but strip any stray code-fence wrapping
	before parsing, since models sometimes wrap JSON in ```json blocks regardless."""
	stripped = text.strip()
	if stripped.startswith("```"):
		stripped = stripped.strip("`")
		if stripped.startswith("json"):
			stripped = stripped[4:]
		stripped = stripped.strip()

	try:
		return json.loads(stripped)
	except json.JSONDecodeError as e:
		frappe.throw(_("Anthropic returned non-JSON content: {0}").format(str(e)))
