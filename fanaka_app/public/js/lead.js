frappe.ui.form.on("Lead", {

    refresh(frm) {

        frm.add_custom_button("Call Customer", () => {

            frappe.prompt(
                [
                    {
                        label: "Phone Number",
                        fieldname: "phone_number",
                        fieldtype: "Data",
                        reqd: 1,
                        default: frm.doc.phone || ""
                    }
                ],
                function(values) {

                    frappe.call({
                        method: "fanaka_app.api.call.make_call",
                        args: {
                            phone_number: values.phone_number
                        },
                        callback: function(r) {

                            if (r.message && r.message.status === "success") {
                                frappe.msgprint("📞 Call initiated successfully");
                            } else {
                                frappe.msgprint("Call failed");
                            }

                        }
                    });

                },
                "Enter Phone Number",
                "Call"
            );

        });

    }

});