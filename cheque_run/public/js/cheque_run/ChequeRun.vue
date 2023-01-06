<style scoped>
    .party-filter {
        margin-top: 5px;
    }

    .table thead th {
        vertical-align: top;
    }

    .chequerun-cheque-box {
        vertical-align: sub; /* weird but this gives the best alignment */
    }

    .cheque-run-table td, .cheque-run-table th {
        max-height: 1.5rem;
        padding: 0.4rem;
        vertical-align: middle;
    }

    .table tr.selectedRow {
        background-color: var(--yellow-highlight-color);
    }
</style>

<script>
    import ADropdown from "./ADropdown.vue";

    export default {
        name: 'ChequeRun',
        components: {
            ADropdown
        },
        props: ['transactions', 'modes_of_payment', 'docstatus', 'state'],
        data() {
            return {
                selectAll: false,
                sort_order: {
                    party_ref: 1,
                    due_date: 1,
                    amount: 1,
                    mode_of_payment: 1,
                    posting_date: 1,
                    gross_amount: 1,
                    discount: 1
                },
                modeOfPaymentNames: this.modes_of_payment.map(mop => mop.name)
            }
        },
        watch: {
            selectAll: (val, oldVal) => {
                cur_frm.cheque_run_state.transactions.forEach(row => { row.pay = val })
                cur_frm.doc.amount_cheque_run = cur_frm.cheque_run_state.cheque_run_total()
                cur_frm.refresh_field("amount_cheque_run")
                cur_frm.dirty();
            },
        },
        methods: {
            transactionUrl: transaction => {
                if (!transaction) {
                    return ""
                }
                return encodeURI(frappe.urllib.get_base_url() + "/app/" + transaction.doctype.toLowerCase().replace(" ", "-") + "/" + transaction.name);
            },
            paymentEntryUrl: transaction => {
                if (!transaction) {
                    return ""
                }
                return encodeURI(frappe.urllib.get_base_url() + "/app/payment-entry/" + transaction.payment_entry);
            },
            sortTransactions(key) {
                this.transactions.sort((a, b) => (a[key] > b[key] ? this.sort_order[key] : this.sort_order[key] * -1));
                this.sort_order[key] *= -1;
            },
            partyIsInFilter(party) {
                return cur_frm.cheque_run_state.party_filter.length < 1 || party.toLowerCase().includes(cur_frm.cheque_run_state.party_filter.toLowerCase());
            },
            toggleShowPartyFilter() {
                cur_frm.cheque_run_state.party_filter = "";
                cur_frm.cheque_run_state.show_party_filter = !cur_frm.cheque_run_state.show_party_filter;
            },
            markDirty() {
                cur_frm.dirty()
            },
            onPayChange() {
                cur_frm.doc.amount_cheque_run = cur_frm.cheque_run_state.cheque_run_total()
                cur_frm.refresh_field("amount_cheque_run")
                this.markDirty()
                if (this.transactions[selectedRow].pay && !this.transactions[selectedRow].mode_of_payment) {
                    frappe.show_alert(__('Please add a Mode of Payment for this row'))
                }
            },
            chequePay() {
                if (this.state.docstatus >= 1 || !this.transactions.length) {
                    return
                }
                this.transactions[this.state.selectedRow].pay = !this.transactions[this.state.selectedRow].pay
                this.onPayChange()
            },
            openMopWithSearch(keycode) {
                if (!this.transactions.length) {
                    return
                }
                this.$refs.dropdowns[this.state.selectedRow].openWithSearch()
            }
        },
        beforeMount() {
            let amountInChequeRun = 0.0
            this.moment = moment;
            this.format_currency = format_currency;
            cur_frm.cheque_run_component = this;
        }
    }
</script>

<template>
    <div>
        <table class="table table-compact table-hover cheque-run-table" style="text-align: center; margin: 0;">
            <thead>
                <tr>
                    <th style="text-align:left; cursor:pointer" class="col col-sm-2" id="cheque-run-party-filter">
                        <span class="party-onclick party-display" @click="sortTransactions('party_ref')">
                            Supplier
                        </span> 
                        
                        <span class="filter-icon">
                            <svg class="icon  icon-sm" @click="toggleShowPartyFilter()">
                                <use class="" href="#icon-filter"></use>
                            </svg>
                        </span>

                        <div class="party-filter" v-if="state.show_party_filter">
                            <input type="text" class="form-control" v-model="state.party_filter"/>
                        </div>
                    </th>

                    <th class="col col-sm-2" style="white-space: nowrap; width: 12.49%; cursor: pointer">
                        <span @click="sortTransactions('party_ref')">
                            Supplier Number
                        </span>
                    </th>

                    <th class="col col-sm-2">
                        <span class="cheque-run-sort-indicator" id="cheque-run-doc-sort">
                            Document
                        </span>
                    </th>

                    <th class="col col-sm-2" style="white-space: nowrap; width: 12.49%; cursor: pointer">
                        <span @click="sortTransactions('posting_date')" class="cheque-run-sort-indicator" id="cheque-run-doc-date-sort">
                            Document Date
                        </span>
                    </th>

                    <th class="col col-sm-2" style="white-space: nowrap; width: 12.49%; cursor: pointer">
                        <span @click="sortTransactions('mode_of_payment')" class="cheque-run-sort-indicator" id="cheque-run-mop-sort">
                            Mode of Payment
                        </span>
                    </th>

                    <th class="col col-sm-2" style="cursor: pointer">
                        <span @click="sortTransactions('gross_amount')" class="cheque-run-sort-indicator">
                            Amount Before Discount
                        </span>
                    </th>

                    <th class="col col-sm-2" style="cursor: pointer">
                        <span @click="sortTransactions('discount')" class="cheque-run-sort-indicator">
                            Discount
                        </span>
                    </th>

                    <th class="col col-sm-2" style="cursor: pointer">
                        <span @click="sortTransactions('amount')" class="cheque-run-sort-indicator" id="cheque-run-outstanding-sort">
                            Outstanding Amount
                        </span>
                    </th>

                    <th class="col col-sm-1" style="cursor: pointer">
                        <span @click="sortTransactions('due_date')" class="cheque-run-sort-indicator" id="cheque-run-due-date-sort">
                            Due Date
                        </span>
                    </th>

                    <th v-if="state.docstatus < 1" style="min-width:200px; text-align: left">
                        <input type="checkbox" autocomplete="off" class="input-with-feedback reconciliation" data-fieldtype="Cheque" id="select-all" v-model="selectAll"/>
                        <span>Select All</span>
                    </th>

                    <th v-else class="col col-sm-2"> Cheque Number | Reference </th>
                </tr>
            </thead>

            <tbody>
                <template v-for="(item, i) in transactions">
                    <tr v-if="partyIsInFilter(item.party)" class="chequerun-row-container">
                        <td style="text-align: left">
                            {{ item.party }}
                        </td>

                        <td style="text-align: center">
                            {{ item.party_ref }}
                        </td>

                        <td>
                            <a :href="transactionUrl(item)" target="_blank">
                                {{ item.ref_number || item.name}}
                            </a>
                        </td>

                        <td>
                            {{ item.posting_date }}
                        </td>

                        <!-- code for dropdown in mode of payment -->
                        <td class="mop-onclick" :data-mop-index="i">
                            <ADropdown 
                                ref="dropdowns" 
                                v-model="state.transactions[i].mode_of_payment"
                                :items="modeOfPaymentNames" 
                                v-if="state.docstatus < 1" 
                                :transactionIndex="i"
                                :isOpen="state.transactions[i].mopIsOpen"
                                @isOpenChanged="val => state.transactions[i].mopIsOpen = val"
                            />
                            <span v-else>
                                {{ transactions[i].mode_of_payment }}
                            </span>
                        </td>

                        <td>
                            {{ format_currency(item.gross_amount, "USD", 2) }}
                        </td>

                        <td>
                            {{ format_currency(item.discount, "USD", 2) }}
                        </td>

                        <td>
                            {{ format_currency(item.amount, "USD", 2) }}
                        </td>

                        <td>
                            {{ moment(item.due_date).format("MM/DD/YY") }}
                        </td>

                        <td v-if="state.docstatus < 1" style="text-align: left">
                            <input 
                                type="checkbox" 
                                class="input-with-feedback chequerun-cheque-box"
                                data-fieldtype="Cheque" 
                                @change="onPayChange(i)" 
                                :data-checkbox-index="i"
                                v-model="item.pay" 
                                :id="item.id"
                            />
                            Pay
                        </td>

                        <td v-else>
                            <a :href="paymentEntryUrl(item)" target="_blank">
                                {{ item.cheque_number }}
                            </a>
                        </td>
                        
                    </tr>
                </template>
            </tbody>
        </table>
    </div>
</template>
