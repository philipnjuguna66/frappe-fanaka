import frappe
from frappe import _
from frappe.model.document import Document


class UserLicense(Document):
	def validate(self):
		self.prevent_duplicate_type_provider()

	def prevent_duplicate_type_provider(self):
		"""A user may not hold two licences with the same type + provider."""
		duplicate = frappe.db.exists(
			"User License",
			{
				"user": self.user,
				"license_type": self.license_type,
				"provider_type": self.provider_type,
				"name": ("!=", self.name),
			},
		)

		if duplicate:
			frappe.throw(
				_("This user already has a {0} licence from {1}.").format(
					self.license_type, self.provider_type
				)
			)
