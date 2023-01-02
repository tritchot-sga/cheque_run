from . import __version__ as app_version

app_name = "cheque_run"
app_title = "Cheque Run"
app_publisher = "SGA Tech Solutions"
app_description = "Payables Utilities for ERP"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "farabi.hussain@sgatechsolutions.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/cheque_run/css/cheque_run.css"
app_include_js = [
	"/assets/js/cheque_run.min.js"
]

# include js, css files in header of web template
# web_include_css = "/assets/cheque_run/css/cheque_run.css"
# web_include_js = "/assets/cheque_run/js/cheque_run.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "cheque_run/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	'Employee': 'public/js/custom/employee_custom.js',
	"Supplier": 'public/js/custom/supplier_custom.js',
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "cheque_run.install.before_install"
# after_install = "cheque_run.install.after_install"
after_migrate = 'cheque_run.customize.load_customizations'

# Uninstallation
# ------------

# before_uninstall = "cheque_run.uninstall.before_uninstall"
# after_uninstall = "cheque_run.uninstall.after_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "cheque_run.notifications.get_notification_config"

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

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
#	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"cheque_run.tasks.all"
# 	],
# 	"daily": [
# 		"cheque_run.tasks.daily"
# 	],
# 	"hourly": [
# 		"cheque_run.tasks.hourly"
# 	],
# 	"weekly": [
# 		"cheque_run.tasks.weekly"
# 	]
# 	"monthly": [
# 		"cheque_run.tasks.monthly"
# 	]
# }

# Testing
# -------

# before_tests = "cheque_run.cheque_run.doctype.cheque_run.test_cheque_run.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "cheque_run.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "cheque_run.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]


# User Data Protection
# --------------------
#

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"cheque_run.auth.validate"
# ]

# Translation
# --------------------------------

# Make link fields search translated document names for these DocTypes
# Recommended only for DocTypes which have limited documents with untranslated names
# For example: Role, Gender, etc.
# translated_search_doctypes = []
