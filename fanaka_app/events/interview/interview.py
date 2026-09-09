"""Interview doc_events: advances the recruitment pipeline once a round is Cleared.

Automatic advancement only kicks in for a Job Opening that has actually configured a
``custom_interview_rounds`` sequence -- an opening with none configured (the default,
since none exist anywhere in this system yet) gets no *automatic* behaviour on
on_submit. This is a deliberate opt-in, not a fallback: guessing "this must be the
only/last round" for an unconfigured opening would wrongly draft a Job Offer off a
single interview HR never intended to be final. HR still has an explicit manual way
to move an unconfigured opening's candidate forward -- see ``get_pipeline_status`` /
``proceed_to_offer`` below, surfaced as a "Proceed to Job Offer" button on the
Interview form whenever there's no next round to schedule.

**Why the next round is never auto-created as a blank draft** [verified against a live
insert during build]: Interview's own doctype marks ``scheduled_on``/``from_time``/
``to_time`` both ``reqd`` AND ``set_only_once`` -- once a value is written at insert
time (even a real one), Frappe's ``validate_set_only_once`` blocks changing it on any
later save, full stop, not just "once non-empty" (see
``frappe/model/document.py:validate_set_only_once``). hrms itself works around this
with a dedicated ``reschedule_interview`` method that writes via ``db_set`` to bypass
the check. So a "blank draft, HR fills in the schedule later and saves" record would
be permanently unschedulable the moment HR tried to save it normally. The next round
is therefore only ever created via ``schedule_next_round`` below, which -- like Phase
6's ``approve_and_invite`` -- sets the schedule fields *before* insert(), in one atomic
step, exactly like every other interview creation in this app.

Rejected needs no handling here -- hrms's own on_submit dialog lets HR mark the Job
Applicant Rejected, and that status change is what fires the regret email (see
fanaka_app.events.job_applicant.job_applicant.on_update).

See specs/recruitment_ai_screening.md (Phase 8) for the plan this implements.
"""

import frappe
from frappe import _
from frappe.utils import today

from fanaka_app.events.hr_notify import notify_hr
from fanaka_app.events.job_applicant.interview_invite import enqueue_interview_invite
from fanaka_app.events.job_applicant.job_applicant import APPROVAL_ROLES


def on_submit_advance_pipeline(doc, method=None):
	if doc.status != "Cleared" or not doc.job_opening:
		return

	rounds = _configured_rounds(doc.job_opening)
	if doc.interview_type not in rounds:
		# No round sequence configured for this opening (or this round isn't part of
		# one) -- nothing this app can safely automate.
		return

	position = rounds.index(doc.interview_type)
	if position + 1 < len(rounds):
		next_round = rounds[position + 1]
		notify_hr(
			"Interview",
			doc.name,
			_('Candidate cleared {0} -- use "Schedule Next Round" on this Interview to set up {1}.').format(
				doc.interview_type, next_round
			),
		)
	else:
		_create_offer_draft(doc)


def _configured_rounds(job_opening: str) -> list[str]:
	return frappe.get_all(
		"Job Opening Interview Round",
		filters={"parent": job_opening, "parenttype": "Job Opening"},
		order_by="idx",
		pluck="interview_type",
	)


def _build_offer_draft(applicant):
	"""Create + insert a bare Job Offer draft for a qualified applicant. Raises on
	failure (e.g. one already exists) -- callers decide how to handle that: the
	automatic hook logs and swallows it, the manual action below lets it surface to
	the user.

	[corrected] Job Applicant.designation is optional (reqd=0), unlike Job Opening's
	own (always reqd=1) -- an applicant without one left Job Offer's designation blank
	and insert() threw "Value missing for Designation" even with the field "set" to
	None. Falls back to the linked Job Opening's designation, which always has one.

	Also inserts with ignore_mandatory=True: this bench's hrms has exactly 5 reqd
	fields on Job Offer (job_applicant/applicant_name/offer_date/designation/company),
	all covered above -- but a live site hit "Value missing for Valid Till", a field
	that doesn't exist in this checkout's hrms at all, meaning a newer hrms version can
	add reqd fields this code has no way to know about in advance. A bare draft that
	can't be inserted at all defeats the point of "HR fills in the rest"; deferring the
	mandatory check to HR's own save (which still enforces it, same protection) is the
	only version-proof option."""
	designation = applicant.designation
	if not designation and applicant.job_title:
		designation = frappe.db.get_value("Job Opening", applicant.job_title, "designation")

	offer = frappe.get_doc(
		{
			"doctype": "Job Offer",
			"job_applicant": applicant.name,
			"applicant_name": applicant.applicant_name,
			"designation": designation,
			"offer_date": today(),
			"company": frappe.defaults.get_global_default("company"),
		}
	)
	offer.insert(ignore_permissions=True, ignore_mandatory=True)
	return offer


def _create_offer_draft(doc):
	applicant = frappe.get_doc("Job Applicant", doc.job_applicant)

	try:
		offer = _build_offer_draft(applicant)
	except frappe.ValidationError:
		# e.g. a Job Offer already exists for this applicant -- must never block this
		# Interview's submission. HR can retry manually via "Proceed to Job Offer" on
		# the Interview form (get_pipeline_status/proceed_to_offer below), which
		# reports errors instead of swallowing them.
		frappe.log_error(
			title="Could not auto-create Job Offer draft",
			message=frappe.get_traceback(),
		)
		return

	notify_hr(
		"Job Offer",
		offer.name,
		_("{0} cleared the final interview round -- fill in salary/terms and send the Job Offer.").format(
			applicant.applicant_name
		),
	)


@frappe.whitelist()
def get_pipeline_status(interview_name: str) -> dict:
	"""What the Interview form's action button should offer next: schedule the
	configured next round, view the Job Offer if one already exists (created either
	automatically or via a previous proceed_to_offer call), or -- if neither -- let HR
	proceed to a Job Offer manually. Covers both cases where the automatic hook does
	nothing on its own: no round sequence configured for this Job Opening at all, and
	an opening's last configured round where the automatic draft failed (logged, not
	surfaced -- see _create_offer_draft)."""
	frappe.only_for(APPROVAL_ROLES)
	doc = frappe.get_doc("Interview", interview_name)

	next_round = None
	if doc.job_opening:
		rounds = _configured_rounds(doc.job_opening)
		if doc.interview_type in rounds:
			position = rounds.index(doc.interview_type)
			if position + 1 < len(rounds):
				next_round = rounds[position + 1]

	job_offer = frappe.db.get_value(
		"Job Offer", {"job_applicant": doc.job_applicant, "docstatus": ["!=", 2]}, "name"
	)
	return {"next_round": next_round, "job_offer": job_offer}


@frappe.whitelist()
def proceed_to_offer(interview_name: str) -> dict:
	"""Manual "no next round" action for a Cleared, submitted interview: same bare
	Job Offer draft the automatic on_submit hook creates when an opening's *last*
	configured round clears -- reachable directly here for an opening with no round
	sequence configured at all (where the hook intentionally does nothing, per
	on_submit_advance_pipeline's module docstring), or as a retry if the automatic
	creation failed silently."""
	frappe.only_for(APPROVAL_ROLES)
	doc = frappe.get_doc("Interview", interview_name)
	if doc.status != "Cleared" or doc.docstatus != 1:
		frappe.throw(_("Only a submitted, Cleared interview can proceed to a Job Offer."))

	existing = frappe.db.exists("Job Offer", {"job_applicant": doc.job_applicant, "docstatus": ["!=", 2]})
	if existing:
		frappe.throw(_("{0} already has a Job Offer ({1}).").format(doc.job_applicant, existing))

	applicant = frappe.get_doc("Job Applicant", doc.job_applicant)
	offer = _build_offer_draft(applicant)
	notify_hr(
		"Job Offer",
		offer.name,
		_("{0} cleared the interview -- fill in salary/terms and send the Job Offer.").format(
			applicant.applicant_name
		),
	)
	return {"offer": offer.name}


@frappe.whitelist()
def schedule_next_round(interview_name: str, scheduled_on, from_time, to_time) -> dict:
	"""Create, schedule and invite for the round after ``interview_name`` (which must
	be Cleared), per the Job Opening's configured sequence. Mirrors Phase 6's
	``approve_and_invite`` exactly -- schedule fields are set before insert(), in one
	atomic step, since Interview makes them set_only_once (see module docstring)."""
	frappe.only_for(APPROVAL_ROLES)

	doc = frappe.get_doc("Interview", interview_name)
	if doc.status != "Cleared":
		frappe.throw(_("Only a Cleared interview can be advanced to the next round."))
	if not doc.job_opening:
		frappe.throw(_("This Interview has no linked Job Opening."))

	rounds = _configured_rounds(doc.job_opening)
	if doc.interview_type not in rounds:
		frappe.throw(_("No interview round sequence is configured for this Job Opening."))
	position = rounds.index(doc.interview_type)
	if position + 1 >= len(rounds):
		frappe.throw(_("{0} is already the last configured round.").format(doc.interview_type))
	next_interview_type = rounds[position + 1]

	from hrms.hr.doctype.job_applicant.job_applicant import create_interview

	try:
		interview = create_interview(doc.job_applicant, next_interview_type)
		interview.scheduled_on = scheduled_on
		interview.from_time = from_time
		interview.to_time = to_time
		interview.insert()
	except frappe.ValidationError as e:
		# Same two hrms validations Phase 6 already guards against
		# (validate_duplicate_interview, validate_designation).
		frappe.throw(str(e), title=_("Could Not Schedule Interview"))

	enqueue_interview_invite(doc.job_applicant, interview.name)
	return {"interview": interview.name}


@frappe.whitelist()
def send_invite(interview_name: str) -> str:
	"""Generic "Send Interview Invite" action, reachable from any round's Interview
	form. Phase 6 built the same send but only reachable from the Shortlisted
	Candidates page for the first round; this reuses it for round 2+ too (for a resend,
	since schedule_next_round above already sends one on creation)."""
	frappe.only_for(APPROVAL_ROLES)
	job_applicant = frappe.db.get_value("Interview", interview_name, "job_applicant")
	if not job_applicant:
		frappe.throw(_("Interview {0} has no linked Job Applicant.").format(interview_name))

	enqueue_interview_invite(job_applicant, interview_name)
	return "queued"
