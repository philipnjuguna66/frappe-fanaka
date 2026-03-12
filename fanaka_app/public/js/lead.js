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
                            phone_number: values.phone_number,
                            reference_doctype: "Lead",
                            reference_name: frm.doc.name
                        },
                        callback: function(r) {

                            console.log("Server response:", r);

                            if (r.message && r.message.status === "success") {
                                frappe.msgprint("📞 Call initiated successfully");
                            } else {
                                frappe.msgprint({
                                    title: "Call Failed",
                                    message: r.message?.message || "Unknown error",
                                    indicator: "red"
                                });
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