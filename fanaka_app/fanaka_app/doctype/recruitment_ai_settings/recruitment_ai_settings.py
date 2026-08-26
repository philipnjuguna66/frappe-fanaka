# Copyright (c) 2026, Philip Njuguna and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class RecruitmentAISettings(Document):
	def validate(self):
		self.validate_thresholds()

	def validate_thresholds(self):
		"""Regret threshold must sit below the shortlist threshold.

		The gap between the two is the grey zone HR reviews by hand — if the regret
		threshold met or passed the shortlist one, applicants good enough to shortlist
		could also qualify for an automatic regret.
		"""
		if not (self.regret_threshold_score and self.shortlist_threshold_score):
			return

		if flt(self.regret_threshold_score) >= flt(self.shortlist_threshold_score):
			frappe.throw(
				_("Regret Threshold Score ({0}%) must be lower than Shortlist Threshold Score ({1}%).").format(
					flt(self.regret_threshold_score), flt(self.shortlist_threshold_score)
				),
				title=_("Overlapping Thresholds"),
			)


def get_settings() -> "RecruitmentAISettings":
	"""Cached settings doc. Use this instead of get_doc/get_single_value everywhere."""
	return frappe.get_cached_doc("Recruitment AI Settings")
