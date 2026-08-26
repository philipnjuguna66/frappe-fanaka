"""Provider/model picker for Recruitment AI Settings.

See specs/recruitment_ai_screening.md (Phase 1) for the plan this implements.
"""

import frappe

from fanaka_app.api.llm_providers import PROVIDERS, get_adapter


@frappe.whitelist()
def get_providers() -> list[str]:
	frappe.only_for(("System Manager", "HR Manager"))
	return sorted(PROVIDERS.keys())


@frappe.whitelist()
def get_models(provider: str, api_key: str = "") -> list[dict]:
	"""``api_key`` is passed explicitly rather than read from the saved doc, so the
	picker works while HR is still filling in the form for the first time, before
	saving. Every provider but OpenRouter requires a key just to list models."""
	frappe.only_for(("System Manager", "HR Manager"))
	return get_adapter(provider).list_models(api_key)
