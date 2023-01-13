frappe.provide('frappe.ui.form')

frappe.ui.form.ChequeRunQuickEntryForm = frappe.ui.form.QuickEntryForm.extend({
	init: function (doctype, after_insert) {
		this._super(doctype, after_insert)
	},
	render_dialog: function () {
		this.mandatory = this.get_fields()
		this._super()
		this.dialog.$wrapper.find('.btn-secondary').hide()
		this.dialog.fields_dict["bank_account"].get_query = () => {
			return {
				"filters": {
					"company": this.dialog.get_field("company").value,
				}
			}
		}
		this.dialog.fields_dict["pay_to_account"].get_query = () => {
			return {
				"filters": {
					"company": this.dialog.get_field("company").value,
					'account_type': 'Payable'
				}
			}
		}
		this.dialog.fields_dict["discount_account"].get_query = () => {
			return {
				"filters": {
					"company": this.dialog.get_field("company").value
				}
			}
		}
		frappe.db.get_value('Bank Account', {
			company: frappe.defaults.get_default('company'),
			is_default: 1,
			is_company_account: 1
		}, 'name')
		.then(r => {
			this.dialog.fields_dict["bank_account"].set_value(r.message.name)
		})
		frappe.db.get_value('Company', {
			name: frappe.defaults.get_default('company'),
		}, 'default_payable_account')
		.then(r => {
			this.dialog.fields_dict["pay_to_account"].set_value(r.message.default_payable_account)
		})
		frappe.db.get_value('Company', {
			name: frappe.defaults.get_default('company'),
		}, 'default_discount_account')
		.then(r => {
			this.dialog.fields_dict["discount_account"].set_value(r.message.default_discount_account)
		})
		this.dialog.fields_dict["company"].df.onchange = () => {
			const values = dialog.get_values()
			if(!values.company){ return }
			frappe.db.get_value('Bank Account', {
				company: values.company,
				is_default: 1,
				is_company_account: 1
			}, 'name')
			.then(r => {
				this.dialog.fields_dict["bank_account"].set_value(r.message.name)
			})
			frappe.db.get_value('Company', {
				company: values.company,
			}, 'default_payable_account')
			.then(r => {
				this.dialog.fields_dict["pay_to_account"].set_value(r.message.default_payable_account)
			})
			frappe.db.get_value('Company', {
				company: values.company,
			}, 'default_discount_account')
			.then(r => {
				this.dialog.fields_dict["discount_account"].set_value(r.message.default_discount_account)
			})
		}
	},
	get_fields: () => {
		return [
			{
				label: __("Company"),
				fieldname: "company",
				fieldtype: "Link",
				options: "Company",
				reqd: 1,
			},
			{
				label: __("Paid From (Bank Account)"),
				fieldname: "bank_account",
				fieldtype: "Link",
				options: "Bank Account",
				reqd: 1
			},
			{
				label: __("Payable Account"),
				fieldname: "pay_to_account",
				fieldtype: "Link",
				options: "Account",
				reqd: 1
			},
			{
				label: __("Discount Account"),
				fieldname: "discount_account",
				fieldtype: "Link",
				options: "Account",
				reqd: 1
			}
		]
	},
	register_primary_action: function() {
		debugger
		const me = this
		this.dialog.set_primary_action(__('Start Cheque Run'), () => {
			const values = me.dialog.get_values()
			frappe.xcall("cheque_run.cheque_run.doctype.cheque_run.cheque_run.cheque_for_draft_cheque_run",
				{ company: values.company, bank_account: values.bank_account, payable_account: values.pay_to_account, discount_account: values.discount_account }
			).then(r => {
				frappe.set_route("Form", "Cheque Run", r)
			})
		})
	},
})
