# Copyright (c) 2022, AgriTheory and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import json
from itertools import groupby, zip_longest
from io import StringIO
from PyPDF2 import PdfFileWriter
import frappe
from frappe.model.document import Document
from frappe.utils.data import flt
from frappe.utils.data import date_diff, add_days, nowdate, getdate, now, get_datetime
from frappe.utils.print_format import read_multi_pdf
from frappe.permissions import has_permission
from frappe.utils.file_manager import save_file, download_file
from frappe.utils.password import get_decrypted_password
from erpnext.accounts.utils import get_balance_on
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_dimensions

class ChequeRun(Document):
	def validate(self):
		self.set_status()
		gl_account = frappe.get_value('Bank Account', self.bank_account, 'account')
		if not gl_account:
			frappe.throw(frappe._("This Bank Account is not associated with a General Ledger Account."))
		self.beg_balance = get_balance_on(gl_account, self.cheque_run_date)
		if self.flags.in_insert:
			if self.initial_cheque_number is None:
				self.get_last_cheque_number()
				self.get_default_payable_account()
				self.set_default_dates()				
		else:
			self.validate_last_cheque_number()


	def set_status(self, status=None):
		if status:
			self.status = status
		elif self.status == 'Confirm Print':
			pass
		elif self.docstatus == 0:
			self.status = 'Draft'
		elif self.docstatus == 1 and self.print_count > 0:
			self.status = 'Printed'
		elif self.docstatus == 1:
			self.status = 'Submitted'


	def get_last_cheque_number(self):
		if self.ach_only().ach_only:
			return
		cheque_number = frappe.get_value('Bank Account', self.bank_account, "cheque_number")
		self.initial_cheque_number = int(cheque_number or 0) + 1


	def get_default_payable_account(self):
		self.pay_to_account = frappe.get_value('Company', self.company, "default_payable_account")


	def set_default_dates(self):
		if not self.cheque_run_date:
			if not self.cheque_run_date:
				self.cheque_run_date = getdate()
			if not self.end_date:
				self.end_date = getdate()
			self.start_discount_date = getdate()
			self.end_discount_date = add_days(getdate(), 14)			

	@frappe.whitelist()
	def validate_last_cheque_number(self, cheque_number=None):
		if self.ach_only().ach_only:
			return
		cheque_number = cheque_number if cheque_number else (self.initial_cheque_number or 0)
		account_cheque_number = frappe.get_value('Bank Account', self.bank_account, "cheque_number") or 0
		if int(cheque_number) < int(account_cheque_number):
			frappe.throw(f'Initial Cheque Number cannot be lower than the last used cheque number <b>{account_cheque_number}</b> for <b>{self.bank_account}</b>')

	@frappe.whitelist()
	def before_submit(self):
		self.payment_entries = []
		self.dt_pes = []
		transactions = self.transactions
		transactions = json.loads(transactions)
		if len(transactions) < 1:
			frappe.throw("You must select at least one Invoice to pay.")
		transactions = sorted([frappe._dict(item) for item in transactions if item.get("pay")], key=lambda x: x.party)
		_transactions = self.create_payment_entries(transactions)
		self.print_count = 0
		self.transactions = json.dumps(_transactions)
		if self.ach_only().ach_only:
			self.initial_cheque_number = ""
			self.final_cheque_number = ""
		else:
			#self.final_cheque_number = _transactions[-1].cheque_number
			frappe.db.set_value('Bank Account', self.bank_account, 'cheque_number', self.final_cheque_number)
		return self


	def build_nacha_file(self):
		electronic_mop = frappe.get_all('Mode of Payment', {'type': 'Electronic', 'enabled': 1}, 'name', pluck="name")
		ach_payment_entries = list(set(
			[e.get('payment_entry') for e in json.loads(self.transactions) if e.get('mode_of_payment') in electronic_mop]
		))
		payment_entries = [frappe.get_doc('Payment Entry', pe) for pe in ach_payment_entries]
		nacha_file = build_nacha_file_from_payment_entries(self, payment_entries)
		ach_file = StringIO(nacha_file())
		ach_file.seek(0)
		return ach_file

	@frappe.whitelist()
	def ach_only(self):
		transactions = json.loads(self.transactions) if self.transactions else []
		ach_only = frappe._dict({'ach_only': True, 'print_cheques_only': True})
		if not self.transactions:
			ach_only.ach_only = False
			ach_only.print_cheques_only = False
			return ach_only
		if any([t.get('mode_of_payment') == 'Cheque' for t in transactions]):
			ach_only.ach_only = False
		if any([t.get('mode_of_payment') in ('ACH/EFT', 'ECheque') for t in transactions]):
			ach_only.print_cheques_only = False
		return ach_only


	def create_payment_entries(self, transactions):
		cheque_count = 0
		_transactions = []
		account_currency = frappe.get_value('Account', self.pay_to_account, 'account_currency')
		gl_account = frappe.get_value('Bank Account', self.bank_account, 'account')
		for party_ref, _group in groupby(transactions, key=lambda x: x.party_ref):
			_group = list(_group)
			# split cheques in groups of 5 if first reference is a cheque
			groups = list(zip_longest(*[iter(_group)] * 5)) if _group[0].mode_of_payment == 'Cheque' else [_group]
			if not groups:
				continue
			for group in groups:
				_references = []
				pe = frappe.new_doc("Payment Entry")
				pe.payment_type = "Pay"
				pe.posting_date = nowdate()
				project = self.get_dimensions_from_references(group, 'project')
				if project != 'None' and project:
					pe.project = project
				cost_center = self.get_dimensions_from_references(group, 'cost_center')
				if cost_center != 'None' and project:
					pe.cost_center = cost_center
				pe.mode_of_payment = group[0].mode_of_payment
				pe.company = self.company
				pe.paid_from = gl_account
				pe.paid_to = self.pay_to_account
				pe.reference_date = self.cheque_run_date
				pe.party = party_ref
				pe.party_type = 'Supplier' if group[0].doctype == 'Purchase Invoice' else 'Employee'
				pe.cheque_run = self.name
				total_amount = 0

				if pe.mode_of_payment == 'Cheque':
					pe.reference_no = int(self.initial_cheque_number) + cheque_count
					cheque_count += 1
					self.final_cheque_number = pe.reference_no
				else:
					pe.reference_no = self.name

				for reference in group:
					if not reference:
						continue
					pe.append('references', {
							"reference_doctype": reference.doctype,
							"reference_name": reference.name or reference.ref_number,
							"due_date": reference.get("due_date"),
							"outstanding_amount": flt(reference.amount),
							"allocated_amount": flt(reference.amount),
							"total_amount": flt(reference.amount),
					})
					total_amount += reference.amount
					reference.cheque_number = pe.reference_no
					_references.append(reference)


				pe.received_amount = total_amount
				pe.base_received_amount = total_amount
				pe.paid_amount = total_amount
				pe.base_paid_amount = total_amount
				pe.paid_from_account_currency = account_currency
				pe.paid_to_account_currency = account_currency
				pe.target_exchange_rate = group[0].conversion_rate
				pe.source_exchange_rate = group[0].conversion_rate

				pe.save()
				pe.submit()
				for reference in _references:
					reference.payment_entry = pe.name
					_transactions.append(reference)
		return _transactions

	def get_dimensions_from_references(self, references, dimension):
		dimensions, default_dimensions = get_dimensions(with_cost_center_and_project=True)
		parents = [reference.get('name') for reference in references if reference]
		purchase_invoice_items = frappe.get_all('Purchase Invoice Item', {'parent': ['in', parents]})
		expense_claim_details = frappe.get_all('Expense Claim Detail', {'parent': ['in', parents]})
		children = purchase_invoice_items + expense_claim_details
		return mode_dimensions(children, dimension)

	@frappe.whitelist()
	def increment_print_count(self, type,Pay_To,reprint_cheque_number=None):	
		FinalResult=bool(False)			
		if(type == "reprint"):					
			Cheq_tran =  frappe.db.sql("""
			(
				SELECT
					count(*) as Total
				FROM `tabPayment Entry`	
				where `tabPayment Entry`.reference_no =  %(cheque_No)s and `tabPayment Entry`.paid_to =  %(Pay_To)s		
			)	
			""", {
				'cheque_No': reprint_cheque_number,'Pay_To': Pay_To				
			}, as_dict=True)	

			for _st in Cheq_tran:
				if _st.get('Total') > 0:			
					FinalResult=bool(True)	
				else:
					FinalResult=bool(False)		
		if FinalResult == False:
			self.print_count = self.print_count + 1
			self.set_status('Submitted')
			self.save()	
			frappe.enqueue_doc(self.doctype, self.name, 'render_cheque_pdf',	reprint_cheque_number=reprint_cheque_number, queue='short', now=True)			
		return FinalResult

	@frappe.whitelist()
	def render_cheque_pdf(self, reprint_cheque_number=None):		
		if not frappe.db.exists('File', 'Home/Cheque Run'):
			frappe.new_doc("File").update({"file_name":"Cheque Run", "is_folder": True, "folder":"Home"}).save()
		initial_cheque_number = int(self.initial_cheque_number)
		if reprint_cheque_number and reprint_cheque_number != 'undefined':
			reprint_cheque_number = int(reprint_cheque_number)
			self.initial_cheque_number = reprint_cheque_number
		output = PdfFileWriter()
		transactions = json.loads(self.transactions)
		cheque_increment = 0
		_transactions = []
		for pe, group in groupby(transactions, key=lambda x: x.get('payment_entry')):
			group = list(group)
			mode_of_payment, docstatus = frappe.db.get_value('Payment Entry', pe, ['mode_of_payment', 'docstatus'])
			
			if docstatus == 1 and frappe.db.get_value('Mode of Payment', mode_of_payment, 'type') == 'Bank':
				output = frappe.get_print(
					'Payment Entry',
					pe,
					frappe.get_meta('Payment Entry').default_print_format,
					as_pdf=True,
					output=output,
					no_letterhead=0,
				)				
				if initial_cheque_number != reprint_cheque_number:					
					frappe.db.set_value('Payment Entry', pe, 'reference_no', self.initial_cheque_number + cheque_increment)
					for ref in group:
						ref['cheque_number'] = self.initial_cheque_number + cheque_increment
						_transactions.append(ref)
				cheque_increment += 1

		if _transactions and reprint_cheque_number:
			frappe.db.set_value('Cheque Run', self.name, 'transactions', json.dumps(_transactions))
			frappe.db.set_value('Cheque Run', self.name, 'initial_cheque_number', self.initial_cheque_number)
			frappe.db.set_value('Cheque Run', self.name, 'final_cheque_number', self.initial_cheque_number + cheque_increment -1)
			frappe.db.set_value('Bank Account', self.bank_account, 'cheque_number', self.final_cheque_number)
		
		frappe.db.set_value('Cheque Run', self.name, 'status', 'Ready to Print')
		save_file(f"{self.name}.pdf", read_multi_pdf(output), None, self.name, 'Home/Cheque Run', False, 0)
	
@frappe.whitelist()
def cheque_for_draft_cheque_run(company, bank_account, payable_account):	
	existing = frappe.get_value(
		'Cheque Run', {
			'company': company,
			'bank_account': bank_account,
			'pay_to_account': payable_account,
			'status': ['in', ['Draft', 'Submitted']],
			'initial_cheque_number': ['!=', 0]
		}
	)	
	if existing:
		return existing
	cr = frappe.new_doc('Cheque Run')	
	cr.company = company
	cr.bank_account = bank_account
	cr.pay_to_account = payable_account	
	cr.save()
	aa=frappe.db.sql("""update `tabCheque Run` set  pay_to_account=%(pay_to_account)s where name= %(name)s""", {
		'pay_to_account': payable_account,'name':cr.name
	}, as_dict=True)
	return cr.name

@frappe.whitelist()
def confirm_print(docname):
	return frappe.db.set_value('Cheque Run', docname, 'status', 'Printed')

@frappe.whitelist()
def get_entries(doc):
	doc = frappe._dict(json.loads(doc)) if isinstance(doc, str) else doc
	if isinstance(doc.end_date, str):
		doc.end_date = getdate(doc.end_date) 
	modes_of_payment = frappe.get_all('Mode of Payment' , order_by='name')
	#modes_of_payment = frappe.get_all('Mode of Payment' ,filters = {'name':'Cheque'}, order_by='name')
	if frappe.db.exists('Cheque Run', doc.name):		
		db_doc = frappe.get_doc('Cheque Run', doc.name)				
		if doc.start_date == db_doc.start_date and doc.end_date == db_doc.end_date and db_doc.transactions:
			return {'transactions': json.loads(db_doc.transactions), 'modes_of_payment': modes_of_payment}	
		
	transactions = query_pending_transactions(doc)
	return {'transactions': transactions, 'modes_of_payment': modes_of_payment}

@frappe.whitelist()
def load_get_entries(doc):
	doc = frappe._dict(json.loads(doc)) if isinstance(doc, str) else doc
	if isinstance(doc.end_date, str):
		doc.end_date = getdate(doc.end_date) 
	modes_of_payment = frappe.get_all('Mode of Payment' , order_by='name')
	#modes_of_payment = frappe.get_all('Mode of Payment' ,filters = {'name':'Cheque'}, order_by='name')
	trans_dict=[]
	tran=[]
	AllTran_dict=[]
	Final_Tran=[]
	if frappe.db.exists('Cheque Run', doc.name):			
		db_doc = frappe.get_doc('Cheque Run', doc.name)	
		
		if db_doc.docstatus == 1:
			return {'transactions': json.loads(db_doc.transactions), 'modes_of_payment': modes_of_payment}	

		if doc.start_date == db_doc.start_date and doc.end_date == db_doc.end_date and db_doc.transactions:
			tran=json.loads(db_doc.transactions)	
			trans_dict = {entry.get('name'): entry for entry in tran}	
	if doc.start_date:
		doc.start_date=doc.start_date		
	else:
		doc.start_date="2019-01-01"
		
	transactions = query_pending_transactions(doc)

	# convert list to dict	
	if transactions:
		AllTran_dict = {entry.get('name'): entry for entry in transactions}	
		
	if trans_dict and AllTran_dict:
		# set operation to find common	
		common_entries = AllTran_dict.keys() & (trans_dict.keys())
		for _common in common_entries:			
			Final_Tran.append(trans_dict.get(_common))
		
		# set operation to find new
		new_entries = AllTran_dict.keys() - trans_dict.keys()	
		for _id in new_entries:			
			Final_Tran.append(AllTran_dict.get(_id))
	elif AllTran_dict:		
		Final_Tran=transactions
	elif trans_dict:	
		Final_Tran=tran
	else:	
		Final_Tran=[]

	# Sort the list of transactions by supplier id, due date
	Final_Tran = sorted(Final_Tran, key=lambda d: d['party_ref'])
	
	return {'transactions': Final_Tran, 'modes_of_payment': modes_of_payment}

@frappe.whitelist()
def get_balance(doc):
	doc = frappe._dict(json.loads(doc)) if isinstance(doc, str) else doc
	if not doc.bank_account or not doc.cheque_run_date:
		return
	gl_account = frappe.get_value('Bank Account', doc.bank_account, 'account')
	return get_balance_on(gl_account, doc.cheque_run_date)

def query_pending_transactions(doc):
	return frappe.db.sql("""
	(
		SELECT
			'Purchase Invoice' as doctype,
			'Supplier' AS party_type,
			`tabPurchase Invoice`.name,
			`tabPurchase Invoice`.bill_no AS ref_number,
			`tabPurchase Invoice`.supplier_name AS party,
			`tabPurchase Invoice`.supplier AS party_ref,
			`tabPurchase Invoice`.outstanding_amount AS gross_amount,
			`tabPurchase Invoice`.conversion_rate,
			`tabPurchase Invoice`.due_date,
			`tabPurchase Invoice`.posting_date,
			CASE WHEN `tabPurchase Invoice`.status = 'Paid' THEN 'true' else 'false' END as IsPaid,
			COALESCE(`tabPurchase Invoice`.supplier_default_mode_of_payment, `tabSupplier`.supplier_default_mode_of_payment, '\n') AS mode_of_payment,
			CASE WHEN `tabPayment Schedule`.discount_date >= %(cheque_run_date)s THEN `tabPayment Schedule`.early_payment_discount_amount ELSE 0 END AS discount,
			CASE WHEN `tabPayment Schedule`.discount_date >= %(cheque_run_date)s THEN `tabPurchase Invoice`.outstanding_amount - `tabPayment Schedule`.early_payment_discount_amount ELSE `tabPurchase Invoice`.outstanding_amount END AS amount
		FROM `tabPurchase Invoice`
		INNER JOIN `tabSupplier` ON `tabSupplier`.name = `tabPurchase Invoice`.supplier
		INNER JOIN `tabPayment Schedule` ON `tabPayment Schedule`.parent = `tabPurchase Invoice`.name 
		WHERE 
			`tabPurchase Invoice`.outstanding_amount > 0 AND
			`tabPurchase Invoice`.company = %(company)s AND
			`tabPurchase Invoice`.docstatus = 1 AND
			`tabPurchase Invoice`.credit_to = %(pay_to_account)s AND
			(
				`tabPurchase Invoice`.due_date <= %(end_date)s OR
				(
					`tabPayment Schedule`.early_payment_discount_amount != 0 AND
					`tabPayment Schedule`.discount_date >= %(start_discount_date)s AND
					`tabPayment Schedule`.discount_date <= %(end_discount_date)s 
				)
			) AND
			`tabPurchase Invoice`.status != 'On Hold'
	)
	UNION
	(
		SELECT
			'Expense Claim' as doctype,
			'Employee' AS party_type,
			`tabExpense Claim`.name,
			`tabExpense Claim`.name AS ref_number,
			`tabExpense Claim`.employee_name AS party,
			`tabExpense Claim`.employee AS party_ref,
			`tabExpense Claim`.grand_total AS gross_amount,
			1.0 AS conversion_rate,
			`tabExpense Claim`.posting_date AS due_date,
			`tabExpense Claim`.posting_date,
			'false' as IsPaid,
			COALESCE(`tabExpense Claim`.mode_of_payment, `tabEmployee`.mode_of_payment, '\n') AS mode_of_payment,
			0 as discount,
			`tabExpense Claim`.grand_total AS amount
		FROM 
			`tabExpense Claim`, `tabEmployee`
		WHERE 
			`tabExpense Claim`.grand_total > `tabExpense Claim`.total_amount_reimbursed AND
			`tabExpense Claim`.employee = `tabEmployee`.name AND
			`tabExpense Claim`.company = %(company)s AND
			`tabExpense Claim`.docstatus = 1 AND
			`tabExpense Claim`.payable_account = %(pay_to_account)s AND
			`tabExpense Claim`.posting_date <= %(end_date)s
	)
	UNION 
	(
		SELECT
			'Journal Entry' AS doctype,
			`tabJournal Entry`.name,
			`tabJournal Entry`.name AS ref_number,
			`tabJournal Entry Account`.party AS party,
			`tabJournal Entry Account`.party AS party_ref,
			`tabJournal Entry Account`.party_type,
			`tabJournal Entry Account`.credit_in_account_currency AS gross_amount,
			`tabJournal Entry Account`.exchange_rate AS conversion_rate,
			`tabJournal Entry`.due_date AS due_date,
			`tabJournal Entry`.posting_date,
			'false' as IsPaid,
			COALESCE(`tabJournal Entry`.mode_of_payment, '\n') AS mode_of_payment,
			0 as discount,
			`tabJournal Entry Account`.credit_in_account_currency AS amount
		FROM 
			`tabJournal Entry`, `tabJournal Entry Account`
		WHERE 
			`tabJournal Entry`.name = `tabJournal Entry Account`.parent AND
			`tabJournal Entry`.company = %(company)s AND
			`tabJournal Entry`.docstatus = 1 AND
			`tabJournal Entry Account`.account = %(pay_to_account)s	AND
			`tabJournal Entry`.due_date <= %(end_date)s AND
			`tabJournal Entry`.name NOT in (
				SELECT 
					`tabPayment Entry Reference`.reference_name
				FROM 
					`tabPayment Entry`, `tabPayment Entry Reference`
				WHERE 
					`tabPayment Entry Reference`.parent = `tabPayment Entry`.name AND
					`tabPayment Entry Reference`.reference_doctype = 'Journal Entry' AND
					`tabPayment Entry`.docstatus = 1
			)
	)
	ORDER BY party_ref ASC, due_date ASC
	""", {
		'company': doc.company, 'pay_to_account': doc.pay_to_account, 'cheque_run_date': doc.cheque_run_date,
		'end_date': doc.end_date, 'start_discount_date':doc.start_discount_date,'end_discount_date':doc.end_discount_date
	}, as_dict=True)

def mode_dimensions_from_doc_items(doc, dimension='cost_center'):
	return mode_dimensions(doc.items, dimension)

def mode_dimensions(data, dimension='cost_center'):
	dimensions = frappe._dict()
	for row in data:
		if row.get(dimension) in dimensions:
			if not row.get('amount'):
				amount = frappe.get_value("Item", row.get('item_code'), 'last_purchase_rate') or 0
			dimensions[row.get(dimension, 'None')] += row.get('amount') if row.get('amount') else amount
		else:
			if not row.get('amount'):
				amount = frappe.get_value("Item", row.get('item_code'), 'last_purchase_rate') or 0
			dimensions[row.get(dimension, 'None')] = row.get('amount') if row.get('amount') else amount
	if not dimensions:
		return
	try:
		return max(dimensions)
	except TypeError:
		return


def get_discount_date(term, posting_date=None, bill_date=None):
	discount_validity = None
	date = bill_date or posting_date
	if term.discount_validity_based_on == "Day(s) after invoice date":
		discount_validity = add_days(date, term.discount_validity)
	elif term.discount_validity_based_on == "Day(s) after the end of the invoice month":
		discount_validity = add_days(get_last_day(date), term.discount_validity)
	elif term.discount_validity_based_on == "Month(s) after the end of the invoice month":
		discount_validity = add_months(get_last_day(date), term.discount_validity)
	return discount_validity

@frappe.whitelist()
def download_cheques(docname):	
	has_permission('Payment Entry', ptype="print", verbose=False, user=frappe.session.user, raise_exception=True)
	file_name = frappe.get_value('File', {'attached_to_name': docname})
	frappe.db.set_value('Cheque Run', docname, 'status', "Confirm Print")
	return frappe.get_value('File', file_name, 'file_url')

@frappe.whitelist()
def download_nacha(docname):
	has_permission('Payment Entry', ptype="print", verbose=False, user=frappe.session.user, raise_exception=True)
	doc = frappe.get_doc('Cheque Run', docname)
	ach_file = doc.build_nacha_file()
	frappe.local.response.filename = f'{docname.replace(" ", "-").replace("/", "-")}.ach'
	frappe.local.response.type = "download"
	frappe.local.response.filecontent = ach_file.read()
	comment = frappe.new_doc('Comment')
	comment.owner = "Administrator"
	comment.comment_type = 'Info'
	comment.reference_doctype = 'Cheque Run'
	comment.reference_name = doc.name
	comment.published = 1
	comment.content = f"{frappe.session.user} created a NACHA file on {now()}"
	comment.flags.ignore_permissions = True
	comment.save()
	frappe.db.commit()


def build_nacha_file_from_payment_entries(doc, payment_entries):
	ach_entries = []
	exceptions = []
	company_bank = frappe.db.get_value('Bank Account', doc.bank_account, 'bank')
	if not company_bank:
		exceptions.append(f'Company Bank missing for {doc.company}')
	if company_bank:
		company_bank_aba_number = frappe.db.get_value('Bank Account', doc.bank_account, 'branch_code')
		company_bank_account_no = frappe.db.get_value('Bank Account', doc.bank_account, 'bank_account_no')
		company_ach_id = frappe.db.get_value('Bank Account', doc.bank_account, 'company_ach_id')
	if company_bank and not company_bank_aba_number:
		exceptions.append(f'Company Bank ABA Number missing for {doc.bank_account}')
	if company_bank and not company_bank_account_no:
		exceptions.append(f'Company Bank Account Number missing for {doc.bank_account}')
	if company_bank and not company_ach_id:
		exceptions.append(f'Company Bank ACH ID missing for {doc.bank_account}')
	for pe in payment_entries:
		if pe.docstatus != 1 or frappe.db.get_value('Mode of Payment', pe.mode_of_payment, 'type') == 'Electronic':
			continue
		party_bank_account = get_decrypted_password('Employee', pe.party, fieldname='bank_account', raise_exception=False)
		if not party_bank_account:
			exceptions.append(f'Employee Bank Account missing for {pe.party_name}')
		party_bank = frappe.db.get_value('Employee', pe.party, 'bank')
		if not party_bank:
			exceptions.append(f'Employee Bank missing for {pe.party_name}')
		if party_bank:
			party_bank_routing_number = frappe.db.get_value('Bank', party_bank, 'aba_number')
		if not party_bank_routing_number:
			exceptions.append(f'Employee Bank Routing Number missing for {pe.party_name}/{employee_bank}')
		ach_entry = ACHEntry(
			transaction_code=22, # chequeing account 
			receiving_dfi_identification=party_bank_routing_number,
			cheque_digit=5,
			dfi_account_number=party_bank_account,
			amount=int(pe.paid_amount * 100),
			individual_id_number='',
			individual_name=pe.party_name,
			discretionary_data='',
			addenda_record_indicator=0,
		)
		ach_entries.append(ach_entry)
	
	if exceptions:
		frappe.throw('<br>'.join(e for e in exceptions))

	batch = ACHBatch(
		service_class_code=220,
		company_name=doc.get('company'),
		company_discretionary_data='',
		company_id=company_ach_id,
		standard_class_code='PPD', # TODO: pass in from settings
		company_entry_description='DIRECTPAY', # TODO: pass in from settings
		company_descriptive_date=None,
		effective_entry_date=getdate(),
		settlement_date=None,
		originator_status_code=1,
		originiating_dfi_id=company_bank_account_no,
		entries=ach_entries
	)
	nacha_file = NACHAFile(
		priority_code=1,
		immediate_destination=company_bank_aba_number,
		immediate_origin=company_bank_aba_number,
		file_creation_date=getdate(),
		file_creation_time=get_datetime(),
		file_id_modifier='0',
		blocking_factor=10,
		format_code=1,
		immediate_destination_name=company_bank,
		immediate_origin_name=company_bank,
		reference_code='',
		batches=[batch]
	)
	return nacha_file