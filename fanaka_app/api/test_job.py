import io

import frappe
from frappe.tests.utils import FrappeTestCase
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request as WerkzeugRequest

from fanaka_app.api.job import create_job_application


class TestCreateJobApplication(FrappeTestCase):
	def tearDown(self):
		frappe.local.request = None
		super().tearDown()

	def test_uploaded_resume_is_attached_to_job_applicant(self):
		builder = EnvironBuilder(
			method="POST",
			base_url="http://fanaka.localhost",
			data={
				"applicant_name": "Jane Doe",
				"email_id": "jane@example.com",
				"phone_number": "0700000000",
				"cover_letter": "Submitted via website.",
				"file": (io.BytesIO(b"fake resume content"), "resume.txt"),
			},
		)
		wreq = WerkzeugRequest(builder.get_environ())
		frappe.local.request = wreq
		frappe.local.form_dict = frappe._dict(wreq.form.to_dict())

		result = create_job_application()

		applicant = frappe.get_doc("Job Applicant", result["name"])
		self.assertTrue(applicant.resume_attachment)
		self.assertEqual(applicant.resume_link, applicant.resume_attachment)
		self.assertTrue(
			frappe.db.exists(
				"File",
				{
					"attached_to_doctype": "Job Applicant",
					"attached_to_name": applicant.name,
					"attached_to_field": "resume_attachment",
				},
			)
		)
