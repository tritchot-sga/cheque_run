import ChequeRun from './ChequeRun.vue'
import ADropdown from './ADropdown.vue'

frappe.provide('cheque_run')

cheque_run.mount_table = frm => {
	cheque_run.frm = frm
	frm.transactions.forEach(val => {
		val.mopIsOpen = true
		val.pay = val.pay ? val.pay : false
	})
	frm.cheque_run_state = Vue.observable({
		transactions: frm.transactions,
		party_filter: "",
		docstatus: frm.doc.docstatus,
		modes_of_payment: frm.modes_of_payment,
		show_party_filter: false,
		cheque_run_total: function () {
			return this.transactions.reduce((partialSum, t) => {
				val = t.pay ? Math.round(partialSum + t.amount, 2) : partialSum
				alert(val)
				return val;
			}, 0);
		},
		selectedRow: 0,
		mopsOpen: 0
	})
	if (frm.$cheque_run instanceof Vue) {
		frm.$cheque_run.$destroy();
	}
	$('#cheque-run-vue').remove()
	$(frm.fields_dict['cheque_run_table'].wrapper).html($("<div id='cheque-run-vue'></div>").get(0));
	frm.$cheque_run = new window.Vue({
		el: $("#cheque-run-vue").get(0),
		render: h => h(
			ChequeRun,
			{
				props: {
					transactions: frm.cheque_run_state.transactions, //list of transtactions
					modes_of_payment: frm.cheque_run_state.modes_of_payment, // populate modes_of_payment select. doesn't get updated
					docstatus: frm.cheque_run_state.docstatus, // used to conditionally render column inputs based on submission status. doesn't get updated
					state: frm.cheque_run_state
				}
			}
		)
	})
}