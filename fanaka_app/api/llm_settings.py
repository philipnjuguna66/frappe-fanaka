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
	saving. Every provider but OpenRouter requires a key just to list models.

	If ``api_key`` is empty (the client omits it when the form shows the masked
	"*****" placeholder for an already-saved key), falls back to the real decrypted
	value on file, so refreshing the Model list after a reload doesn't require
	retyping the key.
	"""
	frappe.only_for(("System Manager", "HR Manager"))

	if not api_key:
		from fanaka_app.fanaka_app.doctype.recruitment_ai_settings.recruitment_ai_settings import get_settings

		api_key = get_settings().get_password("llm_api_key", raise_exception=False) or ""

	return get_adapter(provider).list_models(api_key)


@frappe.whitelist()
def test_connection(provider: str, model: str, api_key: str = "") -> dict:
	"""Send one trivial real request to confirm Provider/Model/API Key actually work
	together, without needing a whole Job Applicant to run a real analysis against.

	Any real failure -- wrong model slug, bad/blank key, network issue -- surfaces here
	as the adapter's own clean frappe.throw() message, the same error a real screening
	job would hit, just without waiting for a background job or a real candidate.

	If ``api_key`` is empty (the client omits it when the form shows the masked "*****"
	placeholder for an already-saved key, i.e. testing without retyping it), falls back
	to the real decrypted value already on file -- same as what analyze_candidate itself
	reads at run time.
	"""
	frappe.only_for(("System Manager", "HR Manager"))

	if not api_key:
		from fanaka_app.fanaka_app.doctype.recruitment_ai_settings.recruitment_ai_settings import get_settings

		api_key = get_settings().get_password("llm_api_key", raise_exception=False) or ""

	result = get_adapter(provider).chat_completion(
		model=model,
		api_key=api_key,
		messages=[
			{
				"role": "system",
				"content": 'Respond with ONLY this exact JSON object, no other text: {"ok": true}',
			},
			{"role": "user", "content": "ping"},
		],
		timeout=30,
	)
	return {"ok": bool(result.get("ok")), "raw": result}
