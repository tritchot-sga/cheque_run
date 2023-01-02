// Copyright (c) 2022, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on("Cheque Run", {
	validate: frm => {
		validate_mode_of_payment_mandatory(frm)
		if (frm.cheque_run_state.party_filter.length > 0) {
			frm.cheque_run_state.party_filter = ""
			frm.cheque_run_state.show_party_filter = false
			return new Promise(function (resolve, reject) {
				reject(
					frappe.msgprint(__(
						'The document was not saved because a Party filter was present. The Party filter has now been cleared. Please review the document before saving.'
					))
				)
			})
		}
		frm.doc.transactions = JSON.stringify(frm.cheque_run_state.transactions)
		frm.doc.amount_cheque_run = frm.cheque_run_state.cheque_run_total()
	},
	refresh: frm => {
		frm.layout.show_message('')
		permit_first_user(frm)
		get_defaults(frm)
		set_queries(frm)
		if (frm.is_new()) {
			get_balance(frm)
		}
		frappe.call({
			method: "ach_only",
			doc: frm.doc,
		}).done(r => {
			if (!r.message.ach_only) {
				if (frm.doc.docstatus == 1) {
					if (frm.doc.print_count > 0 && frm.doc.status != 'Ready to Print') {
						frm.add_custom_button("Re-Print Cheque", () => { reprint_cheques(frm) })
					} else if (frm.doc.print_count == 0 && (frm.doc.status.toLowerCase() == 'submitted' || frm.doc.status.toLowerCase() == "confirm print")) {
						frm.add_custom_button("Print Cheque", () => { print_cheques(frm) })
						//frm.add_custom_button("Print Cheque", () => { print_cheques(frm) })				
						//render_cheques(frm)
					}
				}
				if (frm.doc.status.toLowerCase() == 'ready to print') {
					frm.add_custom_button("Download Cheque", () => { download_cheques(frm) })
				}
			}
			if (!r.message.print_cheques_only) {
				if (frm.doc.docstatus == 1) {
					frm.add_custom_button("Download NACHA File", () => { download_nacha(frm) })
				}
			}
		})
		get_entries(frm)
		//confirm_print(frm)
		if (frm.doc.docstatus > 0) {
			frm.set_df_property('initial_cheque_number', 'read_only', 1)
			frm.set_df_property('final_cheque_number', 'read_only', 1)
		}
	},
	onload_post_render: frm => {
		frm.page.wrapper.find('.layout-side-section').hide()
		permit_first_user(frm)
		load_get_entries(frm)
		// mode_of_payement_change(frm)
	},
	end_date: frm => {
		load_get_entries(frm)
	},
	mode_of_payment: frm => {
		mode_of_payement_change(frm)
	},
	start_date: frm => {
		frappe.xcall('cheque_run.cheque_run.doctype.cheque_run.cheque_run.get_balance', { doc: frm.doc })
		.then(r => {
			frm.set_value('beg_balance', r)
			load_get_entries(frm)
		})
	},
	start_discount_date: frm => {
		load_get_entries(frm)
	},
	end_discount_date: frm => {
		load_get_entries(frm)
	},
	onload: frm => {
		frm.$cheque_run = undefined
		frm.transactions = []
		// frm.cheque_run_sort = {
		// 	partyInput: '',
		// 	docDate: false,
		// 	mop: false,
		// 	outstanding: false,
		// 	dueDate: false,
		// }
	},
	pay_to_account: frm => {
		load_get_entries(frm)
	},
	bank_account: frm => {
		get_balance(frm)
	}
})

function mode_of_payement_change(frm) {
	// $(".mopcls").val(frm.doc.mode_of_payment)
	
	for (let i = 0; i < frm.transactions.length; i++) {
		frm.transactions[i].mode_of_payment = frm.doc.mode_of_payment
		// console.log(i + " -> " + frm.transactions[i].mode_of_payment);
	}
	
	$(".mopcls").val(frm.doc.mode_of_payment)
}

function get_balance(frm) {
	frappe.xcall('cheque_run.cheque_run.doctype.cheque_run.cheque_run.get_balance', { doc: frm.doc })
		.then(r => {
			frm.set_value('beg_balance', r)
		})
}

function set_queries(frm) {
	frm.set_query("bank_account", function () {
		return {
			"filters": {
				"company": frm.doc.company,
			}
		}
	})
	frm.set_query("pay_to_account", function () {
		return {
			"filters": {
				"account_type": "Payable",
				"is_group": 0
			}
		}
	})
}

function get_entries(frm) {
	frappe.xcall('cheque_run.cheque_run.doctype.cheque_run.cheque_run.get_entries', { doc: frm.doc }
	).then((r) => {
		frm.transactions = r.transactions
		frm.modes_of_payment = r.modes_of_payment
		cheque_run.mount_table(frm)
		if (!frappe.user.has_role(["Accounts Manager"])) {
			frm.disable_form()
			frm.$cheque_run.css({ 'pointer-events': 'none' })
		}
	})
	alert("Test 1");
}

function load_get_entries(frm) {
	frappe.xcall('cheque_run.cheque_run.doctype.cheque_run.cheque_run.load_get_entries', { doc: frm.doc }
	).then((r) => {
		frm.transactions = r.transactions
		frm.modes_of_payment = r.modes_of_payment
		cheque_run.mount_table(frm)
		if (!frappe.user.has_role(["Accounts Manager"])) {
			frm.disable_form()
			frm.$cheque_run.css({ 'pointer-events': 'none' })
		}
	})
	alert("Test 2");
}

function total_cheque_run(frm) {
	var total = 0
	for (const [index, row] of frm.cheque_run_state.transactions.entries()) {
		if (row.pay) {
			total += row.amount
		}
	}
	frm.set_value("amount_cheque_run", Number(total))
}

function get_defaults(frm) {
	if (!frm.is_new()) { return }
	frm.set_value('start_date', moment().startOf('week').format())
	frm.set_value('end_date', moment().endOf('week').format())
	frm.set_value('start_discount_date', moment().startOf('week').format())
	frm.set_value('end_discount_date', moment().endOf('week').format())
}

function get_last_cheque_number(frm) {
	//  TODO: refactor to xcall
	if (frm.doc.__islocal && frm.doc.start_date) {
		frappe.call({
			method: "set_last_cheque_number",
			doc: frm.doc,
		}).then((r) => {
			frm.refresh_field("last_cheque")
			frm.refresh_field("initial_cheque_number")
		})
	}
}

function permit_first_user(frm) {
	let viewers = frm.get_docinfo()['viewers']
	if (!viewers) {
		return
	} else if (viewers.current.length == 1 && viewers.current.includes(frappe.session.user)) {
		frm.user_lock = frappe.session.user
		return
	} else if (frappe.session.user == frm.user_lock) {
		return
	} else if (frm.user_lock && frappe.session.user != frm.user_lock) {
		frm.disable_form()
		frm.$cheque_run.css({ 'pointer-events': 'none' })
	}
}

function confirm_print(frm) {
	if (frm.doc.status != 'Confirm Print') { return }
	let d = new frappe.ui.Dialog({
		title: __("Confirm Print"),
		fields: [
			{
				fieldname: 'ht', fieldtype: 'HTML', options:
					`<center><button id="confirm-print" class="btn btn-sm btn-success text-center" style="width: 48%">Confirm Print</button></center><br><br>`
			}
		],
		minimizable: false,
		static: true,
	})
	d.wrapper.find('#confirm-print').on('click', () => {
		frappe.xcall("cheque_run.cheque_run.doctype.cheque_run.cheque_run.confirm_print", { docname: frm.doc.name })
			.then(() => {
				d.hide()
				frm.reload_doc()
			})
	})
	d.show()
}

function reprint_cheques(frm) {
	let d = new frappe.ui.Dialog({
		title: __("<center>Re-Print Cheque</center>"),
		fields: [
			{
				fieldname: 'ht', fieldtype: 'HTML', options:
					`<center><button id="reprint" class="btn btn-sm btn-warning" style="width: 48%; color: white;">Re-Print Cheque</button></center><br>`
			},
			{
				fieldname: 'reprint_cheque_number',
				fieldtype: 'Data',
				label: "New Initial Cheque Number",
			}
		],
		minimizable: false,
		static: true,
	})
	d.wrapper.find('#reprint').on('click', () => {
		d.fields_dict.reprint_cheque_number.df.reqd = 1
		let values = cur_dialog.get_values()
		render_cheques(frm, values.reprint_cheque_number || undefined, "reprint")
		d.hide()
		window.setTimeout(() => {
			frm.reload_doc()
		}, 1000)
	})
	d.show()
}

function print_cheques(frm) {
	render_cheques(frm, frm.selected_doc.initial_cheque_number, "print")
}

function validate_mode_of_payment_mandatory(frm) {
	let mode_of_payment_required = []
	for (const index in frm.cheque_run_state.transactions) {
		let row = frm.cheque_run_state.transactions[index]
		if (row.pay && row.mode_of_payment.length < 2) {
			mode_of_payment_required.push({ row: index + 1, party: row.party, ref_name: row.ref_number || row.name })
		}
	}
	if (mode_of_payment_required.length == 0) { return }
	let message = ''
	for (const index in mode_of_payment_required) {
		let row = mode_of_payment_required[index]
		message += `<li>Row ${row.row}: ${row.party} - ${row.ref_name}</li>`
	}
	frappe.msgprint({
		message: `<br><br><ul>${message}</ul>`,
		indicator: 'red',
		title: __('Mode of Payment Required'),
		raise_exception: true,
	})
}

function render_cheques(frm, reprint_cheque_number = undefined, type) {
	frappe.call({
		method: "increment_print_count",
		doc: frm.doc,
		args: { type: type, Pay_To: frm.selected_doc.pay_to_account, reprint_cheque_number: reprint_cheque_number }
	}).done((rslt) => {
		if (rslt.message == true) {
			alert("Cheque number already exists, please enter another cheque number.")
			return false;
		}
		else {
			frm.reload_doc()
			frm.add_custom_button("Re-Print Cheques", () => { reprint_cheques(frm) })
		}
	}).fail((r) => {
		frm.reload_doc()
	})
}

function download_cheques(frm) {
	frappe.xcall("cheque_run.cheque_run.doctype.cheque_run.cheque_run.download_cheques", { docname: frm.doc.name })
		.then(r => {
			if (r) {
				frm.reload_doc()
				window.open(r)
			}
		})
}

function download_nacha(frm) {
	window.open(`/api/method/cheque_run.cheque_run.doctype.cheque_run.cheque_run.download_nacha?docname=${frm.doc.name}`)
	window.setTimeout(() => {
		frm.reload_doc()
	}, 1000)
}
