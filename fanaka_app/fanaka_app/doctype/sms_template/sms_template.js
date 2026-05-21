// Copyright (c) 2026, Philip Njuguna and contributors
// For license information, please see license.txt

frappe.ui.form.on("SMS Template", {
	refresh(frm) {
		if (!frm.doc.is_active) {
			frm.dashboard.set_headline_alert(
				'<span class="indicator-pill red">Inactive — no SMS or email will be sent</span>'
			);
		} else if (!frm.doc.is_automated) {
			frm.dashboard.set_headline_alert(
				'<span class="indicator-pill orange">Active, manual-only — automated sends are paused</span>'
			);
		} else {
			frm.dashboard.set_headline_alert(
				'<span class="indicator-pill green">Active &amp; automated</span>'
			);
		}
	},
});
