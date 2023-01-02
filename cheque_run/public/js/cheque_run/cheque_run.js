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
				return t.pay ? partialSum + t.amount : partialSum;
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

cheque_run.keyDownHandler = e => {
	if (!cheque_run.frm) {
		return
	}

	if (e.keyCode == 40 && cheque_run.frm.cheque_run_state.selectedRow < (cheque_run.frm.cheque_run_state.transactions.length - 1)) {
		for (let j = 0; j < cheque_run.frm.cheque_run_state.transactions.length; j++) {
			if (cheque_run.frm.cheque_run_state.transactions[j].mopIsOpen) {
				return
			}
		}
		document.getElementById(`mop-input-${cheque_run.frm.cheque_run_state.selectedRow}`).blur()
		cheque_run.frm.cheque_run_state.selectedRow += 1
	}

	if (e.keyCode == 38 && cheque_run.frm.cheque_run_state.selectedRow > 0) {
		for (let j = 0; j < cheque_run.frm.cheque_run_state.transactions.length; j++) {
			if (cheque_run.frm.cheque_run_state.transactions[j].mopIsOpen) {
				return
			}
		}
		document.getElementById(`mop-input-${cheque_run.frm.cheque_run_state.selectedRow}`).blur()
		cheque_run.frm.cheque_run_state.selectedRow -= 1
	}

	if (e.keyCode == 32 && cheque_run.frm.cheque_run_state.selectedRow != null && cheque_run.frm.cheque_run_state.transactions.length) {
		e.preventDefault()
		if (cheque_run.frm.cheque_run_component) {
			cheque_run.frm.cheque_run_component.chequePay();
		}
	}

	if (e.keyCode && e.keyCode >= 65 && e.keyCode <= 90 && cheque_run.frm.cheque_run_state.selectedRow != null && cheque_run.frm.cheque_run_state.transactions.length) {
		cheque_run.frm.cheque_run_component.openMopWithSearch(e.keyCode)
	}
}

window.removeEventListener('keydown', cheque_run.keyDownHandler);
window.addEventListener('keydown', cheque_run.keyDownHandler);
