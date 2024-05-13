app_name = "whithat"
app_title = "Whitehats"
app_publisher = "mt"
app_description = "Whitehats"
app_email = "a@gmail.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html

doctype_js = {
    "Subscription": "public/js/subscription.js",
    "Item Price": "public/js/item_price.js",
    "Sales Invoice": "public/js/sales_invoice.js",
}


fixtures = [
    {"dt": "Custom Field", "filters": {"module": "Whitehats"}},
]
# app_include_css = "/assets/whithat/css/whithat.css"
# app_include_js = "/assets/whithat/js/whithat.js"

# include js, css files in header of web template
# web_include_css = "/assets/whithat/css/whithat.css"
# web_include_js = "/assets/whithat/js/whithat.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "whithat/public/scss/website"

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
# 	"methods": "whithat.utils.jinja_methods",
# 	"filters": "whithat.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "whithat.install.before_install"
# after_install = "whithat.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "whithat.uninstall.before_uninstall"
# after_uninstall = "whithat.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "whithat.utils.before_app_install"
# after_app_install = "whithat.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "whithat.utils.before_app_uninstall"
# after_app_uninstall = "whithat.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "whithat.notifications.get_notification_config"

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
	"Subscription": "whithat.custom_script.subscription.subscription.Custom_Subscription",
	"Sales Invoice": "whithat.custom_script.sales_invoice.sales_invoice.CustomSalesInvoice",
	"Sales Order": "whithat.custom_script.sales_order.sales_order.CustomSalesOrder",
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

# Scheduled Tasks
# ---------------

scheduler_events = {
    'cron': {
        '0 8 * * *': [
            'whithat.custom_script.subscription.subscription.cron_upgrade_plan'
        ],
        '0 8 * * *': [
            'whithat.custom_script.subscription.subscription.cron_price_alteration'
        ],
        '0 8 * * *': [
            'whithat.custom_script.subscription.subscription.invoice_due_date_alert'
        ],
    },
}
# scheduler_events = {
# 	"all": [
# 		"whithat.tasks.all"
# 	],
# 	"daily": [
# 		"whithat.tasks.daily"
# 	],
# 	"hourly": [
# 		"whithat.tasks.hourly"
# 	],
# 	"weekly": [
# 		"whithat.tasks.weekly"
# 	],
# 	"monthly": [
# 		"whithat.tasks.monthly"
# 	],
# }
#
# scheduler_events = {
#     "daily": [
#         "whithat.whithat.custom_script.subscription.subscription.upgrade_plan"
#     ]
# }
# Testing
# -------

# before_tests = "whithat.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "whithat.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "whithat.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["whithat.utils.before_request"]
# after_request = ["whithat.utils.after_request"]

# Job Events
# ----------
# before_job = ["whithat.utils.before_job"]
# after_job = ["whithat.utils.after_job"]

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
# 	"whithat.auth.validate"
# ]
