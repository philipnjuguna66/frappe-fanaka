import frappe
from hrms.hr.doctype.leave_application.leave_application import LeaveApplication


class FanakaLeaveApplication(LeaveApplication):
	"""
	Blocked days (e.g. Sundays / holidays synced to Leave Block Lists) may fall
	inside a leave range. Core HRMS raises a warning for them and throws
	`LeaveDayBlockedError` when approving a leave that touches a block date.

	Fanaka policy: blocked days inside the range are simply not counted as leave
	days (handled in events.leave_applications.validate_leave_block). Approving
	or editing such a leave must not raise. So both block-day gates are disabled.
	"""

	def show_block_day_warning(self):
		# No warning toast for block dates inside the leave range.
		pass

	def validate_block_days(self):
		# Do not throw when approving a leave that spans a block date.
		pass
