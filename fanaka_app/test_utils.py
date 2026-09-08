"""Frappe v15/v16 test-base compatibility shim.

`frappe.tests.utils.FrappeTestCase` (v15) was removed in v16 in favour of
`frappe.tests.IntegrationTestCase`. This branch supports both Frappe
versions, so doctype tests import `FanakaTestCase` from here instead of
importing a version-specific base directly.
"""

try:
	from frappe.tests import IntegrationTestCase as FanakaTestCase  # Frappe >= 16
except ImportError:
	from frappe.tests.utils import FrappeTestCase as FanakaTestCase  # Frappe 15
