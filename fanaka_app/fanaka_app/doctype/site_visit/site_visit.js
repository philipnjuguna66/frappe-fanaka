// Copyright (c) 2024, Philip Njuguna and contributors
// For license information, please see license.txt

frappe.ui.form.on("Site Visit", {
	refresh(frm) {

	},
    start_odometer: function (frm){

        const distance = frm.doc.end_odometer -  frm.doc.start_odometer

        frm.set_value("distance",  distance)
    },
    end_odometer: function (frm){

        const distance = frm.doc.end_odometer -  frm.doc.start_odometer

        frm.set_value("distance",  distance)
    }
});
