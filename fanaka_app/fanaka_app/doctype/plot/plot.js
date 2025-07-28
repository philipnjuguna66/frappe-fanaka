// Copyright (c) 2025, Philip Njuguna and contributors
// For license information, please see license.txt

frappe.ui.form.on("Plot", {
	refresh(frm) {
        if (!frm.doc.__islocal) { // Check if the document has been saved
            frm.disable_save(); // This will disable the save button for new documents
        }
        console.log(frappe.ui.toolbar);
        // To hide the 'New' button from the list view.
        // This method is for list view buttons.
        if (frappe.route_options.view === 'List') {

            frappe.ui.toolbar.get_primary_action_button().hide();
        }
	},
});
