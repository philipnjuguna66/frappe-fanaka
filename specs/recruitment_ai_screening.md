# AI Recruitment Screening — Plan

## The problem

Every Job Opening collects a pile of Job Applicant records, each with a resume attachment and
cover letter. Today someone in HR opens them one at a time and reads them cold. That costs in
three ways:

- **Screening is slow and doesn't scale.** Time-to-shortlist grows linearly with applicant
  count, so a well-advertised opening is punished with more manual reading.
- **Screening is inconsistent and undocumented.** Two reviewers rank the same CV differently,
  and neither decision leaves a written reason behind. When a hiring choice is later
  questioned, there is nothing on the record explaining why a candidate was passed over.
- **Rejected candidates hear nothing.** Sending individual regret emails is manual work with
  no deadline attached, so in practice it doesn't happen. Candidates are left waiting
  indefinitely, which is both discourteous and bad for the employer's reputation.

## What we want to achieve

1. **Cut manual screening effort** — AI reads each resume + cover letter against the Job
   Opening on upload and scores the candidate, so HR starts from a ranked list instead of an
   undifferentiated inbox.
2. **Make every decision explainable** — each applicant carries a visible score card:
   an aggregate score plus the specific reasons behind it (skills, experience, education). Not
   just the shortlisted ones — *every* candidate, so any decision can be justified after the
   fact.
3. **Keep a human in the loop** — AI recommends, it does not decide. Strong matches land in a
   new `Shortlisted by AI` status that only a human can convert to a real `Shortlisted`.
   Nobody is hired or rejected by the model alone.
4. **Close the loop with every candidate** — regret emails become automatic and reliable
   instead of manual and forgotten, with HR keeping full control of the wording, the score
   threshold that triggers them, and whether automation is on at all.
5. **Never block the user or lose an email** — all AI calls and mail sending run as background
   jobs through Frappe's queue, so form saves stay fast and sends get retries.

**Non-goals**: auto-rejecting or auto-hiring anyone without human review; replacing the
interview process; scoring candidates on anything outside the job requirements.

---

No prior plan file found in repo/git history — this is a fresh spec (confirmed with user 2026-08-26).
Verification pass run 2026-08-26 (Opus) — every API/field/convention claim below was checked
against the actual code in this bench. Corrections from that pass are marked **[verified]** /
**[corrected]**.

**Stack**: Frappe **v16.24.0**, hrms **v16.10.1** [verified]. App: `fanaka_app` (Frappe custom
app). Extends core HR doctypes from `hrms`: `Job Opening`, `Job Applicant`
(`apps/hrms/hrms/hr/doctype/job_applicant`). Follow existing fanaka_app conventions: custom
fields via `fanaka_app/fixtures/custom_field.json`, event handlers under
`fanaka_app/events/<module>/`, wired in `hooks.py` `doc_events` / `scheduler_events` (see
`Leave Application`, `expiry_reminders.run` for pattern).

## Flow in one line

CV upload → background AI scoring against the Job Opening → score card on every applicant →
strong matches to `Shortlisted by AI` for human approval → weak matches get a queued,
HR-editable regret email.

---

## Phase 1 — Data Model

**[corrected] All custom fields on `Job Applicant` must use the `custom_` prefix** — all 21
existing custom fields in this app do (`custom_kra_pin`, `custom_project_block`, …), and
Frappe v15+ reserves the prefix to avoid collisions with future core fields. Earlier draft
used bare names (`ai_score`); corrected throughout.

- Custom fields on `Job Applicant` (fixtures + Property Setter for status options):
  - `custom_ai_score` (Percent)
  - `custom_ai_analysis_summary` (Small Text)
  - `custom_ai_analyzed_on` (Datetime)
  - `custom_ai_score_breakdown` (Table → new child doctype `Job Applicant Score Item`:
    `category` [Select: Skills/Experience/Education], `criteria`, `points`, `remark`)
  - `custom_regret_email_sent` (Check, read-only)
  - `custom_regret_email_sent_on` (Datetime, read-only)
  - Extend `status` Select options: `Open / Replied / Shortlisted by AI / Shortlisted /
    Rejected / Hold / Accepted` via Property Setter (keeps hrms core file untouched). Note the
    controller's `status: DF.Literal[...]` type hint won't list the new option — that's a
    static type annotation only, Property Setter still governs at runtime [verified].

- **[corrected] Fixture export gotchas** — both are easy to miss and silently produce an
  un-deployable app:
  - `hooks.py` `fixtures` exports Custom Field via an **explicit name whitelist**
    (`["name", "in", [...]]`). Every new field must be appended there as
    `Job Applicant-custom_ai_score` etc., or it will not export.
  - Property Setter is filtered by `["module", "=", "Fanaka App"]`. A Property Setter created
    through Customize Form defaults to the *host doctype's* module (HR), so its `module` must
    be set to `Fanaka App` explicitly or it won't export either.

- New Single doctype `Recruitment AI Settings` (fanaka_app) — regret fields in Phase 4:
  - `enable_ai_screening` (Check)
  - `shortlist_threshold_score` (Percent) — score ≥ this ⇒ auto status `Shortlisted by AI`
  - `openrouter_api_key` (Password) — `Password` fieldtype confirmed in Frappe core (used on
    `User`) [verified], encrypted at rest. Note this repo's other external integration
    (`api/mpesa.py`) reads keys from `os.environ` instead — going with the in-app Password
    field per your choice, since HR needs to rotate it without shell access.
  - `openrouter_provider` (Select) + `openrouter_model` (Select, filtered by provider) —
    global, applies to all screening. **[verified]** `GET https://openrouter.ai/api/v1/models`
    returns HTTP 200 **with no `Authorization` header** and yields
    `{"data": [{"id": "vendor/model-slug", "name", "pricing", "context_length", …}]}` — so the
    picker needs no API key (earlier draft hedged on this; now confirmed public).
    Whitelisted methods `fanaka_app.api.openrouter.get_providers` / `get_models(provider)`
    fetch + cache the list and derive provider from each `id`'s `vendor` prefix.
    **[corrected]** use `frappe.cache.set_value(...)` — in v16 `frappe.cache()` as a *call* is
    only a backward-compat shim. Saved value stays the full slug, which is what OpenRouter's
    chat-completions `model` param expects.

## Phase 2 — AI Resume/Cover Letter Analysis

- `doc_events["Job Applicant"]["on_update"]` → if `resume_attachment` or `cover_letter`
  changed and `enable_ai_screening`: enqueue
  `fanaka_app.events.job_applicant.ai_screen.analyze_candidate`.
  **[corrected]** use `frappe.enqueue(..., queue="long", enqueue_after_commit=True)` — without
  `enqueue_after_commit` the worker can start before the transaction commits and read stale
  data. Confirmed a real `enqueue` param [verified].
- Extract resume text — **[corrected]** `pdfplumber` is **already installed** in this bench's
  env (so is `pypdf`, and `requests`); only **`python-docx` is missing** and needs adding to
  `pyproject.toml`. Earlier draft claimed both were missing.
- Call OpenRouter (`requests.post("https://openrouter.ai/api/v1/chat/completions", ...)`, same
  `requests` pattern as `api/mpesa.py`) with the Job Opening description as context.
- Model returns a single aggregate score (0–100%) **plus** a breakdown across 3 fixed
  categories — **skills, experience, education** — with a variable number of AI-chosen reasons
  inside each, summing to the aggregate. Example: `80% — Skills: Python (+15), no AWS cert
  (-5); Experience: 5yrs relevant (+20); Education: BSc CS (+10)`.
- Write `custom_ai_score`, `custom_ai_analysis_summary`, populate `custom_ai_score_breakdown`
  rows (one per reason).
- If score ≥ `shortlist_threshold_score`: set `status = "Shortlisted by AI"`.
- Every candidate gets the score card populated, not just shortlisted ones.
- **[decided] Employee Referral sync**: `JobApplicant.set_status_for_employee_referral()` maps
  status → Employee Referral status only for `Open/Replied/Hold` (→ `In Process`) and
  `Accepted/Rejected` (→ same) [verified]. The new `Shortlisted by AI` matches no branch, so a
  referred candidate's referral would silently stop updating. **Fix**: our own `on_update`
  handler sets the referral to `In Process` when status becomes `Shortlisted by AI`, matching
  how `Open/Replied/Hold` already behave, so the referrer sees the candidate progressing.
  Do this in fanaka_app's handler — do not patch the hrms method.

## Phase 3 — HR Review

- List view filter / workspace shortcut for `status = Shortlisted by AI`
- HR opens candidate, sees `custom_ai_score_breakdown` as a read-only HTML score card (same
  pattern as the doctype's existing `resume_preview_html` field), plus resume preview
- HR approves → `status = Shortlisted`; rejects → `status = Rejected`
- Mechanism: whitelisted methods
  `fanaka_app.events.job_applicant.job_applicant.approve_ai_shortlist(name)` /
  `reject_ai_shortlist(name)` behind custom form buttons, role-checked in Python.
- **[decided] Role gating**: `HR Manager` **or** `HR User` may approve/reject. Both already
  hold `Job Applicant` permissions in hrms [verified], so no new role and no permission
  fixtures are needed. (Earlier draft assumed a `Recruitment Officer` role, which does not
  exist in hrms — `Job Applicant` permits only `System Manager`, `HR User`, `HR Manager`.)
  Implementation: `if not set(frappe.get_roles()) & {"HR Manager", "HR User", "System Manager"}:
  frappe.throw(...)` at the top of each whitelisted method — an explicit check, since
  `@frappe.whitelist()` alone only verifies the user is logged in.
- **[corrected] Rationale fix**: the earlier draft justified skipping Frappe `Workflow` by
  claiming "this app doesn't use Workflow elsewhere" — **that is false**. `fanaka_app` ships a
  `Requisition` workflow (5 states, 4 transitions) and exports `Workflow` + `Workflow State`
  fixtures [verified]. Your choice of whitelisted-method still stands, and is still defensible
  (2-outcome approval, no multi-step state machine, no docstatus involvement) — but it is a
  deviation from an existing in-app pattern, not the absence of one.

## Phase 4 — Regret Emails (NEW)

**Template management** — use the core Frappe `Email Template` doctype (confirmed at
`apps/frappe/frappe/email/doctype/email_template/`) [verified]; don't build a custom template
store. Fields: `subject` (Data, required), `response` (Text Editor), `use_html` (Check),
`response_html` (Code) [verified]. HR edits it in-app, no deploy needed to change wording.

**[corrected] CRITICAL API FIX — the earlier draft was wrong.** It proposed
`frappe.sendmail(template=<Email Template name>, args=...)`. That does **not** use the Email
Template doctype: `sendmail`'s `template` param is *"Name of html template from
templates/emails folder"* — a Jinja file on disk, rendered via `get_email_from_template`
[verified in `apps/frappe/frappe/email/__init__.py`]. Passing an Email Template record name
there would fail to resolve. Correct pattern:

```python
et = frappe.get_doc("Email Template", settings.regret_email_template)
rendered = et.get_formatted_email(applicant.as_dict())   # -> {"subject", "message"}
frappe.sendmail(
    recipients=[applicant.email_id],
    subject=rendered["subject"],
    message=rendered["message"],
    reference_doctype="Job Applicant",
    reference_name=applicant.name,
    now=False,
)
```

**[decided] Placeholder convention — bare style**, matching hrms's own hiring templates:

```
Dear {{ applicant_name }}, regarding your application for {{ job_title }} …
```

So the call above passes `applicant.as_dict()` **directly** as the context, not wrapped in a
`doc` key:

```python
rendered = et.get_formatted_email(applicant.as_dict())   # bare {{ field }} placeholders
```

Rationale [verified]: hrms renders its hiring emails as `context = doc.as_dict()` →
`frappe.render_template(template.response, context)`, and its shipped `Interview Reminder`
template is written bare — `Interview: {{name}} is scheduled on {{scheduled_on}} from
{{from_time}} to {{to_time}}`. Our templates sit in the same Email Template list HR browses,
so one convention across all of them. (This reverses the earlier `{{ doc.x }}` choice.)

**⚠️ Field-name note**: you wrote `{{ application_name }}` — the actual field on Job Applicant
is **`applicant_name`** [verified in the doctype], with no `application_name` field existing.
Using `applicant_name` throughout. This is exactly the failure mode worth guarding: a wrong
placeholder name renders **empty and silent**, so the candidate gets "Dear ," with no error
raised anywhere.

**Mitigation for silent-empty placeholders** — since neither Jinja nor Frappe errors on an
unknown field here, add a "Send Test Email" button on `Recruitment AI Settings` that renders
the selected template against a real (or dummy) applicant and shows the output before HR
commits to a live send. Cheap to build, and it's the only practical way HR catches a typo
before a candidate does.

**Available placeholders** to document in the template help text: `{{ applicant_name }}`,
`{{ job_title }}`, `{{ email_id }}`, `{{ designation }}`, `{{ custom_ai_score }}`, `{{ name }}`
— any fieldname on Job Applicant.

**[note] Render the subject too** — hrms's `send_interview_reminder` passes
`interview_template.subject` **unrendered** [verified], so placeholders in its subject line
would leak as literal text. Use `get_formatted_email()`, which renders subject and body both.
*(Naming trap: `frappe.utils.get_formatted_email()` is an unrelated function that formats
"Name <addr>". Don't confuse it with the EmailTemplate method.)*

**Settings** — add to `Recruitment AI Settings`:
- `regret_email_template` (Link → Email Template) — template used for auto/bulk send
- `regret_threshold_score` (Percent) — score below this = eligible. Validate
  `regret_threshold_score < shortlist_threshold_score` on save (the gap between them is a gray
  zone HR handles manually — never auto-send there)
- `auto_send_regret_emails` (Check) — master automation toggle, **off by default**
- `regret_send_after_days` (Int) — grace period before auto-send, so HR gets a review window
- `regret_batch_size` (Int, default ~50) — throttle per scheduler run
- `interview_invite_template` (Link → Email Template) — used by Phase 6's invite action; hrms
  ships no invitation email, only a pre-interview reminder [verified]

**Two send paths, one underlying function**
(`fanaka_app.events.job_applicant.regret_email.enqueue_regret_email(applicant_name)`):

1. **Automatic** — daily scheduler entry `fanaka_app.api.regret_emails.run`, added to
   `scheduler_events["daily"]` alongside the existing `expiry_reminders.run`. Selects Job
   Applicants where `custom_ai_score < regret_threshold_score`, `status not in (Shortlisted by
   AI, Shortlisted, Accepted, Hold)`, `custom_regret_email_sent = 0`, automation enabled, and
   grace period elapsed. Enqueues in batches of `regret_batch_size`. Candidates never analyzed
   (`custom_ai_score` NULL, no resume) are excluded automatically — `NULL < threshold` is never
   true in SQL — matching your "manual only" choice with no special-casing needed.
2. **Manual/bulk** — button on the Job Applicant list view ("Send Regret Email"), works
   regardless of the automation toggle, so HR can send with automation off or act on the gray
   zone.

**Delivery = background job**: `frappe.enqueue(queue="short")` wrapping the `sendmail` call
above. Note `sendmail`'s own `delayed` param already defaults to `True`, so it writes to the
core `Email Queue` doctype even unwrapped [verified] — wrapping it still earns its keep by
keeping the template render + flag write off the web request and matching this repo's existing
background-job pattern. After a successful send set `custom_regret_email_sent = 1` and
`custom_regret_email_sent_on`. Passing `reference_doctype`/`reference_name` attaches a
`Communication` to the applicant, so the send shows in the doc's Activity — no separate audit
log needed.

**Guardrails**: never auto-send to `Shortlisted by AI`/`Shortlisted`/`Accepted`/`Hold`; never
send twice (flag check + idempotency); manual bulk respects the sent-flag unless HR explicitly
confirms a resend.
**[decided] Repeat applicants**: `JobApplicant.autoname()` sets `name = email_id`, and a person
reapplying gets `email@x.com-1`, `-2`, … [verified], so one human can hold several Job
Applicant records across openings. **One regret per application record** — each application
gets its own reply, since each is a separate opening the candidate deserves an answer on. No
dedupe on `email_id`. The per-record `custom_regret_email_sent` flag is therefore the only
idempotency guard needed.

## Phase 6 — Shortlisted Candidates Page (NEW)

A dedicated desk page listing shortlisted candidates with per-row actions and filters. This
becomes HR's main working surface and supersedes the "list view filter" bullet in Phase 3 —
the whitelisted approve/reject methods from Phase 3 are reused here, not rebuilt.

**Page tech** — standard desk Page, following this app's existing precedent
`fanaka_app/fanaka_app/page/unpaid_requisitions/` [verified]: `frappe.pages['<slug>'].on_page_load`
+ `frappe.ui.make_app_page`, Tailwind CDN injected at load, `module: "Fanaka App"`,
`standard: "Yes"`, roles declared in the Page JSON. Because it's a standard Page it ships as
code — no fixture whitelist entry needed (unlike the custom fields).
- Slug: `shortlisted-candidates`; roles on the Page JSON: `System Manager`, `HR Manager`,
  `HR User` (matching the Phase 3 approval roles)

**Listing** — candidates with `status in (Shortlisted by AI, Shortlisted)`, showing applicant
name, job title, `custom_ai_score`, score breakdown summary, applied date, resume link.
Sorted by score descending so the strongest candidates surface first.

**Filters** — Job Opening, status (`Shortlisted by AI` vs human-approved `Shortlisted`), score
range (min/max), designation, date applied, and whether a regret/invite email has already gone
out. Filter state drives one whitelisted `get_shortlisted_candidates(filters)` method that
returns rows — keep querying server-side, don't pull everything and filter in JS.

**Row actions** — two paths, both confirmed in a dialog before firing:

1. **Approve + Invite for Interview**
   - Sets `status = Shortlisted` (reuses `approve_ai_shortlist` from Phase 3)
   - Creates an `Interview` record, then emails the candidate the invitation
   - **[verified] Required inputs**: `Interview` mandates `interview_type`, `scheduled_on`,
     `from_time`, `to_time` — so the action must open a dialog collecting all four, it cannot
     be a one-click button
   - Reuse hrms's existing `hrms.hr.doctype.interview.interview.create_interview(job_applicant,
     interview_type)` [verified] — it returns an unsaved Interview with interviewers already
     prefilled from the Interview Type; we set the schedule fields and save
   - **[verified] Two hrms validations will throw and must be surfaced cleanly in the dialog,
     not as raw tracebacks**: `validate_duplicate_interview` blocks the same applicant +
     Interview Type where a submitted interview already exists; `validate_designation` throws
     if the Interview Type's designation differs from the applicant's designation
   - **[verified] hrms sends NO interview invitation email.** Its only interview mail is
     `send_interview_reminder`, a scheduled job firing shortly before the interview to
     interviewers + candidate. So the invite email is ours to build: a new
     `interview_invite_template` (Link → Email Template) on `Recruitment AI Settings`,
     rendered and queued through the same background-job path as the regret email.

2. **Reject + Send Regret Email**
   - Sets `status = Rejected` (reuses `reject_ai_shortlist` from Phase 3)
   - Calls the same `enqueue_regret_email()` from Phase 4 — one send path, whether triggered by
     the scheduler, the list-view bulk button, or this page
   - Respects the `custom_regret_email_sent` flag; resending requires explicit confirmation

**Bulk actions** — checkbox selection with the same two actions applied across selected rows.
Interview invites can't be bulk-scheduled sensibly (each needs its own time slot), so bulk is
reject+regret only; bulk approve without invite is allowed.

**[new] Sender address** — use `hiring_sender_email` from HR Settings for both the invite and
the regret email [verified: hrms already ships `hiring_sender` / `hiring_sender_email` fields
and `send_interview_reminder` sends with them]. Falls back to the default outgoing account if
unset. This keeps all recruitment mail coming from one recognizable address.

## Phase 5 — Reporting

- Score card as read-only HTML on the form (reuse the `resume_preview_html` pattern already in
  the doctype)
- List view: `custom_ai_score`, `custom_regret_email_sent` columns; score-range filters
- Dashboard chart "AI Screening Funnel" alongside the existing `job_applicant_pipeline` chart

---

## Dependencies

- **Add to `pyproject.toml`**: `python-docx` only [corrected — `pdfplumber` already present]
- Already available in bench env, no entry needed: `pdfplumber`, `pypdf`, `requests`
  (`requests` is already imported directly in `api/mpesa.py` with no pyproject entry)

## Resolved decisions (clarification rounds, 2026-08-26)

1. **LLM provider**: OpenRouter, global setting (not per-Job-Opening)
2. **Resume formats**: PDF + DOCX
3. **No-resume candidates**: manual-only regrets, never auto-sent
4. **API key storage**: `openrouter_api_key` Password field on `Recruitment AI Settings`
5. **Score model**: aggregate 0–100% + breakdown over 3 fixed categories (skills, experience,
   education) with variable AI-generated reasons in each
6. **Data retention**: keep AI critique text indefinitely, no auto-clear job
7. **Model selection UX**: separate Provider + Model Selects, populated from OpenRouter's
   public `/models` endpoint
8. **HR approval**: permission-checked whitelisted methods + form buttons, not a Workflow
9. **Approval roles**: `HR Manager` + `HR User` (existing hrms roles, no new role created)
10. **Employee Referral sync**: `Shortlisted by AI` marks the referral `In Process`
11. **Repeat applicants**: one regret email per application record, no per-person dedupe
12. **Placeholder style**: bare `{{ applicant_name }}` — matches hrms's shipped hiring
    templates; context is `applicant.as_dict()` passed directly. Plus a "Send Test Email"
    button on settings, since a mistyped placeholder fails silently
13. **Shortlisted Candidates page**: standard desk Page (Tailwind, `make_app_page`) following
    the `unpaid_requisitions` precedent, with filters and approve-invite / reject-regret actions
14. **Interview invites**: our own `interview_invite_template` — hrms has no invite email
15. **Sender**: `hiring_sender_email` from HR Settings for all recruitment mail

**No open questions remain. Plan is ready to build.**

## Build order

1. **Phase 1** — child doctype `Job Applicant Score Item`, Single `Recruitment AI Settings`,
   6 custom fields + status Property Setter, fixture whitelist entries in `hooks.py`
2. **Phase 2** — `python-docx` dep, resume text extraction, OpenRouter client + model picker
   methods, `analyze_candidate` background job, `on_update` hook, referral-sync fix
3. **Phase 3** — score card HTML, approve/reject whitelisted methods + form buttons
4. **Phase 4** — regret + invite email templates, settings fields, `enqueue_regret_email`,
   daily scheduler job, list-view bulk button, "Send Test Email" button
5. **Phase 6** — Shortlisted Candidates page: query method + filters, row/bulk actions,
   interview-scheduling dialog, invite email send
6. **Phase 5** — list columns, filters, dashboard chart

Phases 1–2 are the critical path. Phase 6 depends on Phase 3's approve/reject methods and
Phase 4's send path, so it lands after both — it's the surface that ties them together, and is
where HR actually works day to day. Phase 5 (reporting) is last and independent.
