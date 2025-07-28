// Copyright (c) 2025, Philip Njuguna and contributors
// For license information, please see license.txt

frappe.ui.form.on("Plot", {
	refresh(frm) {
        if (!frm.doc.__islocal) { // Check if the document has been saved
            frm.disable_save(); // This will disable the save button for new documents
        }

        console.log(frm)

        console.log(frappe.ui.toolbar);
        // To hide the 'New' button from the list view.
        // This method is for list view buttons.
        if (frappe.route_options.view === 'List') {

            frappe.ui.toolbar.get_primary_btn().hide();
        }
	},
});
frappe.listview_settings['Plot'] = {
    refresh: function(listview) {
        console.log(listview)
        // Condition: Hide the button if a certain field in a DocType is 'Disabled'.
        // Example: If the 'allow_creation' field in the 'System Settings' DocType is unchecked.
        // You would need to fetch the value of this field first.

        // This is the most reliable way to remove the button.
        listview.page.wrapper.find('.btn-primary[data-action="new"]').hide();
    }
};