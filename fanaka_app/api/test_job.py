import io

import frappe
from fanaka_app.test_utils import FanakaTestCase
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request as WerkzeugRequest

from fanaka_app.api.job import create_job_application


class TestCreateJobApplication(FanakaTestCase):
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

	def _apply(self, **extra):
		builder = EnvironBuilder(
			method="POST",
			base_url="http://fanaka.localhost",
			data={
				"applicant_name": "Jane Doe",
				"email_id": "jane.loc@example.com",
				"phone_number": "0700000000",
				"cover_letter": "Submitted via website.",
				**extra,
			},
		)
		wreq = WerkzeugRequest(builder.get_environ())
		frappe.local.request = wreq
		frappe.local.form_dict = frappe._dict(wreq.form.to_dict())
		return create_job_application()

	def test_preferred_work_location_is_saved_on_job_applicant(self):
		result = self._apply(custom_preferred_work_location="Mombasa Road, including Kitengela")

		self.assertEqual(
			frappe.db.get_value("Job Applicant", result["name"], "custom_preferred_work_location"),
			"Mombasa Road, including Kitengela",
		)

	def test_preferred_work_location_is_optional(self):
		result = self._apply()

		self.assertFalse(
			frappe.db.get_value("Job Applicant", result["name"], "custom_preferred_work_location")
		)

