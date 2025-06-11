frappe.ui.form.on('Stock Entry', {
    refresh: function(frm) {
        // Only show the button if the Stock Entry is a draft ('Repack' purpose)
        // and has not yet been submitted.
        if (frm.doc.docstatus === 0 && frm.doc.purpose === "Repack") {
            frm.add_custom_button(__('Generate Plot Serials'), function() {
                // Client-side validation before calling the server script
                if (!frm.doc.project) {
                    frappe.msgprint(__('Please link a Project to this Stock Entry first.'), __('Project Required'));
                    return;
                }

                let plotItemFound = false;
                if (frm.doc.repacked_items && frm.doc.repacked_items.length > 0) {
                    for (let i = 0; i < frm.doc.repacked_items.length; i++) {
                        // IMPORTANT: Replace "PLOT-001" with the actual Item Code of your 'Plot' item
                        if (frm.doc.repacked_items[i].item_code === "PLOT-001") {
                            if (!frm.doc.repacked_items[i].qty || frm.doc.repacked_items[i].qty <= 0) {
                                frappe.msgprint(__('Quantity for "Plot" item must be greater than 0.'), __('Invalid Quantity'));
                                return;
                            }
                            plotItemFound = true;
                            break;
                        }
                    }
                }

                if (!plotItemFound) {
                    frappe.msgprint(__('Please add the "Plot" item to the "Repacked Items" table.'), __('Item Missing'));
                    return;
                }

                // Call the server-side Python method
                frappe.call({
                    // Full path to your Python method:
                    // app_name.module_name.file_name.Class_Name.method_name
                    method: "my_land_app.doctype.stock_entry.stock_entry.StockEntry.generate_and_attach_plot_serials",
                    args: {
                        // Pass the current document's data to the server method
                        doc: frm.doc
                    },
                    freeze: true, // Show a loading indicator while the script runs
                    callback: function(r) {
                        if (r.message) {
                            // If the server returns a message, show it as an alert
                            frappe.show_alert({
                                message: r.message,
                                indicator: 'green'
                            }, 5);
                            // Refresh the 'repacked_items' child table to show the newly populated serial numbers
                            frm.refresh_field('repacked_items');
                        }
                        if (r.exc) {
                            // Handle exceptions/errors from the server-side script
                            frappe.show_alert({
                                message: __('An error occurred: ') + r.exc,
                                indicator: 'red'
                            });
                        }
                    }
                });
            }, __('Generate')); // 'Generate' is the button group/category
        }
    }
});