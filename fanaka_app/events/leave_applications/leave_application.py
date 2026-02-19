import frappe
import json
from frappe.utils import date_diff, today, getdate


def validate_leave_block(doc, method=None):
    """
    Prevent leave application if date falls inside
    Leave Block List created from Holiday List.
    """

    if not doc.from_date or not doc.to_date:
        return

    from_date = getdate(doc.from_date)
    to_date = getdate(doc.to_date)

    # Get all submitted block lists for this leave type + company
    block_lists = frappe.get_all(
        "Leave Block List",
        filters={
            "leave_type": doc.leave_type,
            "company": doc.company,

        },
        fields=["name"]
    )

    if not block_lists:
        return

    block_list_names = [b.name for b in block_lists]

    # Get blocked dates inside range
    blocked_dates = frappe.get_all(
        "Leave Block List Date",
        filters={
            "parent": ["in", block_list_names],
            "block_date": ["between", [from_date, to_date]]
        },
        fields=["block_date"]
    )

    if blocked_dates:
        dates = ", ".join(str(d.block_date) for d in blocked_dates)

        frappe.throw(
            f"Leave cannot be applied on blocked date(s): {dates}"
        )

def pass_requirement(doc, event):
    try:
        if (doc.leave_type.upper() == "ANNUAL LEAVE"):
            if doc.from_date:
                days_to_leave_start = date_diff(doc.from_date, today()) + 1
                if days_to_leave_start < 1:
                    pass

        existing_draft_leaves = frappe.db.count(
            'Leave Application',
            filters={
                'employee': doc.employee,
                'status': 'Open'
            }
        )
        if existing_draft_leaves >= 2:
            frappe.throw("You cannot create a third Annual Leave application while previous ones are still in 'Open' status.")
    except Exception as e:
        frappe.log_error(f"Error in pass_requirement: {str(e)}", "Custom Hook Error")
        raise

def sync_holiday_list_to_blocks(doc, method=None):
    """
    Hooked to Holiday List after_save.
    Creates or updates Leave Block Lists for every Leave Type.
    Naming format: snake_case(holiday_list_name + leave_type_name)
    """

    try:
        frappe.log_error(f"Starting Sync for: {doc.name}", "Leave Block Sync Debug")

        leave_types = frappe.get_all("Leave Type", fields=["name"])

        if not doc.holidays:
            frappe.log_error("No holidays found", "Leave Block Sync Debug")
            return

        holiday_dates = [
            getdate(h.holiday_date)
            for h in doc.holidays
            if h.holiday_date
        ]

        for lt in leave_types:
            leave_type = lt.name

            # Generate snake_case name
            raw_name = f"{doc.name}_{leave_type}"
            formatted_name = frappe.scrub(raw_name)

            # 🔎 Check if block list already exists
            existing_name = frappe.db.exists(
                "Leave Block List",
                {
                    "block_list_name": formatted_name,
                    "leave_type": leave_type,
                }
            )

            if existing_name:
                block_doc = frappe.get_doc("Leave Block List", existing_name)
                is_new_doc = False
            else:
                block_doc = frappe.new_doc("Leave Block List")
                block_doc.leave_block_list_name = formatted_name
                block_doc.leave_type = leave_type

                for h_date in holiday_dates:
                    block_doc.append("leave_block_list_dates", {
                        "block_date": h_date,
                        "reason": f"Auto sync from {doc.name}"
                    })
                # Insert first (important for proper naming)
                block_doc.insert(ignore_permissions=True)
                is_new_doc = True

                frappe.log_error(
                    f"Created new block list: {formatted_name}",
                    "Leave Block Sync Debug"
                )

            # Get existing dates
            existing_dates = {
                getdate(d.block_date)
                for d in block_doc.leave_block_list_dates
                if d.block_date
            }

            added = False

            for h_date in holiday_dates:
                if h_date not in existing_dates:
                    block_doc.append("leave_block_list_dates", {
                        "block_date": h_date,
                        "reason": f"Auto sync from {doc.name}"
                    })
                    added = True

            # Save only if dates were added and not newly inserted
            if added and not is_new_doc:
                block_doc.save(ignore_permissions=True)

                frappe.log_error(
                    f"Updated {formatted_name} with new dates",
                    "Leave Block Sync Debug"
                )

        frappe.msgprint("Leave Block Lists synchronized successfully.")

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Leave Block Sync Error"
        )
