# Copyright (c) 2026, Philip Njuguna and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class SMSTemplate(Document):
	def should_send(self, automated: bool = True) -> bool:
		if not self.is_active:
			return False
		if automated and not self.is_automated:
			return False
		return bool(self.sms)
