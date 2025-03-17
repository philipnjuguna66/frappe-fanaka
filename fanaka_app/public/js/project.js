frappe.ui.form.on("Project", {
    refresh: function(frm) {

        if (frm.doc.project_type == "Real Estate") {

            frm.add_custom_button(__("Subdivide Plots"), function() {
                // Open a custom dialog to collect input
                open_subdivide_dialog(frm);
            });

        }



    }
});

function open_subdivide_dialog(frm) {
    // Create a dialog with input fields
    const dialog = new frappe.ui.Dialog({
        title: __("Subdivide Plots"),
        fields: [
            {
                label: __("Number of Plots"),
                fieldname: "no_of_plots",
                description: __("e.g 25"),
                fieldtype: "Int",
                reqd: 1
            },
            {
                label: __("Plot Size (in Ha)"),
                fieldname: "plot_size",
                fieldtype: "Data",
                description: __("Approx 0.035 ha"),
                reqd: 1
            },
            {
                label: __("Price per Plot"),
                fieldname: "price_per_plot",
                fieldtype: "Currency",
                reqd: 1
            }
        ],
        primary_action_label: __("Subdivide"),
        primary_action(values) {
            // Call the server-side method to subdivide plots
            frappe.call({
                method: "fanaka_app.fanaka_app.doctype.project.project.subdivide_plots",
                args: {
                    project: frm.doc.name,
                    no_of_plots: values.no_of_plots,
                    plot_size: values.plot_size,
                    price_per_plot: values.price_per_plot,
                    location: values.location
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.msgprint(r.message);
                        frm.refresh(); // Refresh the form to show the new plots
                    }
                }
            });
            dialog.hide();
        }
    });

    dialog.show();
}