import frappe
from frappe.utils.file_manager import save_file

@frappe.whitelist(allow_guest=True)  # NOT allow_guest
def opening():
    """
    Fetch all job openings
    """

    job_openings = frappe.get_all(
        "Job Opening",
        fields=[
            "name",
            "job_title",
            "status",
            "company",
            "designation",
            "department",
            "route",
            "description",
            "posted_on",
            "closed_on",
            "closes_on"
        ],
        filters={
            "status": "Open"
        },
        order_by="posted_on desc"
    )

    return job_openings

@frappe.whitelist(allow_guest=True)
def create_job_application():
    data = frappe.local.form_dict

    # Basic validation
    required_fields = [
        "applicant_name",
        "email_id",
        "phone_number",
        "cover_letter"
    ]

    for field in required_fields:
        if not data.get(field):
            frappe.throw(f"{field} is required")

    job_application = frappe.get_doc({
        "doctype": "Job Applicant",
        "applicant_name": data.get("applicant_name"),
        "email_id": data.get("email_id"),
        "phone_number": data.get("phone_number"),
        "country": data.get("country"),
        "job_title": data.get("job_title"),
        "designation": data.get("designation"),
        "status": "Open",
        "source": data.get("source"),
        "cover_letter": data.get("cover_letter"),
        "resume_link": data.get("resume_link"),
        "currency": data.get("currency", "KES"),
        "lower_range": data.get("lower_range", 0),
        "upper_range": data.get("upper_range", 0),
    })

    job_application.insert(ignore_permissions=True)

    uploaded = frappe.request.files.get("file") if frappe.request else None
    if uploaded:
        file_doc = save_file(
            uploaded.filename,
            uploaded.stream.read(),
            "Job Applicant",
            job_application.name,
            is_private=1,
            df="resume_attachment",
        )
        # db_set() never runs doc_events (only before_change/on_change, not on_update),
        # so it would silently skip the AI screening hook on Job Applicant.on_update --
        # save() runs the full lifecycle, which is what actually queues analyze_candidate.
        job_application.resume_attachment = file_doc.file_url
        job_application.save(ignore_permissions=True)

    frappe.db.commit()

    return {
        "status": "success",
        "message": "Job application submitted successfully",
        "name": job_application.name
    }

