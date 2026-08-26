app_name = "fanaka_app"
app_title = "Fanaka App"
app_publisher = "Philip Njuguna"
app_description = "Fanaka Real Estate App"
app_email = "philipnjuguna66@gmail.com"
app_license = "mit"

# import insights.www.insights
# import fanaka_app.overrides.insights

# insights.www.insights.get_context = fanaka_app.overrides.insights.get_context


# required_apps = []

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/fanaka_app/css/fanaka_app.css"
# app_include_js = "/assets/fanaka_app/js/fanaka_app.js"

# include js, css files in header of web template
# web_include_css = "/assets/fanaka_app/css/fanaka_app.css"
# web_include_js = "/assets/fanaka_app/js/fanaka_app.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "fanaka_app/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

doctype_js = {
	"Project" : "public/js/project.js",
	"Lead" : "public/js/lead.js",
	"Stock Entry": "public/js/stock_entry_custom.js",
}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "fanaka_app/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "fanaka_app.utils.jinja_methods",
# 	"filters": "fanaka_app.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "fanaka_app.install.before_install"
# after_install = "fanaka_app.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "fanaka_app.uninstall.before_uninstall"
# after_uninstall = "fanaka_app.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "fanaka_app.utils.before_app_install"
# after_app_install = "fanaka_app.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "fanaka_app.utils.before_app_uninstall"
# after_app_uninstall = "fanaka_app.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "fanaka_app.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

override_doctype_class = {
	"Leave Application": "fanaka_app.overrides.leave_application.FanakaLeaveApplication",
	"Stock Entry": "fanaka_app.overrides.stock_entry.StockEntry"
}

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

doc_events = {
	"Leave Application": {
		 "validate": "fanaka_app.events.leave_applications.leave_application.validate_leave_block",
		 "before_insert": "fanaka_app.events.leave_applications.leave_application.pass_requirement",

	},
	"Holiday List": {
		"before_save": "fanaka_app.events.leave_applications.leave_application.sync_holiday_list_to_blocks"
	},
	"Purchase Invoice": {
		"validate": "fanaka_app.events.purchase_invoice.purchase_invoice.create_purchase_invoice",
	},
	"Stock Entry": {
		"before_insert": "fanaka_app.events.stock_entry.stock_entry.generate_plot_serial_numbers"
	},
	"Commission Entry": {
		"after_insert": "fanaka_app.api.commission_engine.calculate_commission",
		"on_submit": "fanaka_app.api.commission_engine.process_commission_to_salary"
	},
	"Notification": {
		"after_insert": "fanaka_app.api.notifications.handle_sms_cc"
	},
	"Project": {
		"validate": "fanaka_app.events.project.project.validate",
		"after_insert": "fanaka_app.events.project.project.after_insert"
	},
	"Job Applicant": {
		"on_update": "fanaka_app.events.job_applicant.job_applicant.on_update"
	}

}



# Scheduled Tasks
# ---------------

scheduler_events = {
	"daily": [
		"fanaka_app.api.expiry_reminders.run"
	],
}

# Testing
# -------

# before_tests = "fanaka_app.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "fanaka_app.event.get_events"
# }

# hooks.py




#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "fanaka_app.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["fanaka_app.utils.before_request"]
# after_request = ["fanaka_app.utils.after_request"]

# Job Events
# ----------
# before_job = ["fanaka_app.utils.before_job"]
# after_job = ["fanaka_app.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"fanaka_app.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }


fixtures = [
	{"doctype": "Workflow"},
	{"doctype": "Workflow State"},
	{
		"doctype": "Custom Field",
		"filters": [
			["name", "in", [
				"Supplier-custom_land_details_section",
				"Supplier-custom_kra_pin",
				"Supplier-custom_next_of_kin",
				"Supplier-custom_vendor_col_break",
				"Supplier-custom_default_block_number",
				"Project-custom_land_section",
				"Project-custom_total_acreage",
				"Project-custom_county",
				"Project-custom_primary_vendor",
				"Project-custom_total_purchase_price",
				"Project-custom_acquisition_status",
				"Project-custom_blocks_section",
				"Project-custom_blocks",
				"Purchase Invoice-custom_project_block",
				"Purchase Order-custom_project_block",
				"Plot-custom_stock_section",
				"Plot-custom_item",
				"Plot-custom_serial_no",
				"Plot-custom_warehouse",
				"Plot-custom_project_block",
				"Plot-custom_stock_status",
				"Job Applicant-custom_ai_section",
				"Job Applicant-custom_ai_score",
				"Job Applicant-custom_ai_analyzed_on",
				"Job Applicant-custom_ai_column_break",
				"Job Applicant-custom_regret_email_sent",
				"Job Applicant-custom_regret_email_sent_on",
				"Job Applicant-custom_ai_analysis_summary",
				"Job Applicant-custom_ai_score_breakdown"
			]]
		]
	},
	{"doctype": "Property Setter", "filters": [["module", "=", "Fanaka App"]]},
	{"doctype": "Expense Type"}
]

# inside your_app/hooks.py
add_to_apps_screen = [
    {
        "name": "fanaka_app",
        "logo": "storage/fanaka-real_estate_logo.png",
        "title": "My Fanaka App",
        "route": "/desk/fanaka-app",
    }
]