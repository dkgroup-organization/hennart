# -*- coding: utf-8 -*-

from odoo import fields, models
import logging
_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _name = "account.invoice"
    _description = "Imported Invoice"
    _order = "date_invoice desc, number desc, id desc"

    name = fields.Char(string='Reference/Description', index=True)
    origin = fields.Char(string='Source Document')
    market_place = fields.Char(string='Market Place')
    reconciliation_shopping_feed = fields.Char(string='Reconciliation Shopping feed')
    partner_shipping_id = fields.Many2one('res.partner', 'Shipping address')

    type = fields.Selection([
            ('out_invoice', 'Customer Invoice'),
            ('in_invoice', 'Vendor Bill'),
            ('out_refund', 'Customer Credit Note'),
            ('in_refund', 'Vendor Credit Note'),
        ], index=True)

    refund_invoice_id = fields.Many2one('account.invoice', string="Invoice for which this invoice is the credit note")
    number = fields.Char('number')
    move_name = fields.Char(string='Journal Entry Name', default=False, copy=False)
    reference = fields.Char(string='Payment Ref.')
    comment = fields.Text('Additional Information')

    state = fields.Selection([
            ('draft', 'Draft'),
            ('proforma', 'Proformat'),
            ('proforma2', 'Proformat2'),
            ('open', 'Open'),
            ('in_payment', 'In Payment'),
            ('paid', 'Paid'),
            ('cancel', 'Cancelled'),
        ], string='Status', index=True, default='draft')

    sent = fields.Boolean('sent')
    date_invoice = fields.Date(string='Invoice Date', index=True)
    date_due = fields.Date(string='Due Date', index=True)
    partner_id = fields.Many2one('res.partner')
    vendor_bill_id = fields.Many2one('account.invoice', string='Vendor Bill')
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms')
    date = fields.Date(string='Accounting Date')

    account_id = fields.Many2one('account.account')

    refund_invoice_ids = fields.One2many('account.invoice', 'refund_invoice_id', string='Refund Invoices')
    move_id = fields.Many2one('account.move', string='MOVE Account', index=True)

    amount_untaxed = fields.Monetary(string='Untaxed Amount')
    amount_untaxed_signed = fields.Monetary(string='Untaxed Amount in Company Currency')
    amount_untaxed_invoice_signed = fields.Monetary(string='Untaxed Amount in Invoice Currency')
    amount_tax = fields.Monetary(string='Tax')
    amount_tax_signed = fields.Monetary(string='Tax in Invoice Currency')
    amount_total = fields.Monetary(string='Total')
    amount_total_signed = fields.Monetary(string='Total in Invoice Currency')
    amount_total_company_signed = fields.Monetary(string='Total in Company Currency')
    currency_id = fields.Many2one('res.currency', string='Currency')
    journal_id = fields.Many2one('account.journal', string='Journal')
    company_id = fields.Many2one('res.company', string='Company')
    partner_bank_id = fields.Many2one('res.partner.bank', string='Bank Account')

    payment_ids = fields.Many2many('account.payment', 'account_invoice_payment_v12_rel', 'invoice_id', 'payment_id', string="Payments")

    user_id = fields.Many2one('res.users', string='Salesperson')
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position')
    commercial_partner_id = fields.Many2one('res.partner', string='Commercial Entity')

    sequence_number_next = fields.Char(string='Next Number')
    sequence_number_next_prefix = fields.Char(string='Next Number Prefix')
    incoterm_id = fields.Many2one('account.incoterms', string='Incoterm')
    source_email = fields.Char(string='Source Email')
    tax_line_ids = fields.One2many('account.invoice.tax', 'invoice_id', string='Tax Lines')

    invoice_line_ids = fields.One2many('account.invoice.line', 'invoice_id')
    invoice_line_ok = fields.Boolean('Ready to post')
    invoice_post_ok = fields.Boolean('Post done')
    invoice_post = fields.Selection(related='move_id.state', store=True)

    synchro_obj = fields.Many2one('synchro.obj')
    remote_id = fields.Integer('Remote_id')

    state_balanced = fields.Selection(
            [('to_check', 'To check'), ('ok', 'ok'), ('nok', 'nok')], string='balanced')
    state_void_line = fields.Selection(
            [('to_check', 'To check'), ('ok', 'ok'), ('nok', 'nok')], string='void line')
    state_reconcile = fields.Selection(
            [('to_check', 'To check'), ('ok', 'ok'), ('nok', 'nok')], string='reconciled')
    state_date = fields.Datetime('Last checked date')

    def get_account_tax(self):
        "get the account tax"
        account_tax = self.env['account.account']
        for invoice in self:
            for line in invoice.tax_line_ids:
                account_tax |= line.account_id
        return account_tax

    def recompute_invoice(self):
        "Recompute the tax, exclude the non invoice line, post the move"

        account_tax = self.get_account_tax()

        for invoice in self:

            if not invoice.move_id or invoice.move_id.state == 'posted':
                continue
            invoice = invoice.sudo()

            for line in invoice.move_id.line_ids:
                line = line.sudo().with_context(check_move_validity=False)
                if line.account_id in account_tax:
                    line.unlink()
                elif not line.product_id:
                    line.write({
                            'exclude_from_invoice_tab': True,
                            'sequence': -line.id})
                else:
                    line.write({'sequence': -line.id})

            move = invoice.move_id.sudo().with_context(check_move_validity=False)

            if move.state != 'draft':
                move.button_draft()

            move._recompute_dynamic_lines(
                recompute_all_taxes=True, recompute_tax_base_amount=True)

            # In old version, sometime the refund is a negative invoice
            if move.is_invoice(include_receipts=True) and move.amount_total < 0.0:
                if move.move_type == 'out_refund':
                    move.move_type = 'out_invoice'
                if move.move_type == 'in_refund':
                    move.move_type = 'in_invoice'
                move.action_switch_invoice_into_refund_credit_note()
                move._compute_amount()

            if move.line_ids:
                move.action_post()
                invoice.invoice_post_ok = True
            elif not invoice.state_void_line:
                invoice.state_void_line = 'to_check'
                invoice.invoice_post_ok = False
            else:
                invoice.state_void_line = 'nok'
                invoice.invoice_post_ok = False


class AccountInvoiceLine(models.Model):
    _name = "account.invoice.line"
    _description = "Invoice Line"
    _order = "invoice_id,sequence,id"

    name = fields.Text(string='Description')
    origin = fields.Char(string='Source Document')
    sequence = fields.Integer(default=10)
    invoice_id = fields.Many2one(
        'account.invoice', string='Invoice Reference', index=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', index=True)
    product_id = fields.Many2one('product.product', string='Product', index=True)

    account_id = fields.Many2one('account.account', string='Account')
    price_unit = fields.Monetary(string='Unit Price')
    price_total = fields.Monetary(string='Amount (with Taxes)')
    price_subtotal = fields.Monetary(string='Amount')
    currency_id = fields.Many2one('res.currency', string='Currency')

    quantity = fields.Float(string='Quantity')
    discount = fields.Float(string='Discount (%)', default=0.0)

    invoice_line_tax_ids = fields.Many2many(
            'account.tax',
            'account_invoice_line_tax_imported', 'invoice_line_id', 'tax_id',
            string='Taxes')

    account_analytic_id = fields.Many2one(
            'account.analytic.account',
            string='Analytic Account')

    is_rounding_line = fields.Boolean(string='Rounding Line', help='Is a rounding line in case of cash rounding.')
    move_line_id = fields.Many2one('account.move.line', string='Move line')
    imported_date = fields.Datetime('Imported Date')


class AccountInvoiceTax(models.Model):
    _name = "account.invoice.tax"
    _description = "Invoice Tax"

    invoice_id = fields.Many2one('account.invoice', string='Invoice', index=True)
    name = fields.Char(string='Tax Description')
    tax_id = fields.Many2one('account.tax', string='Tax')
    account_id = fields.Many2one('account.account', string='Tax Account')

    amount = fields.Monetary('Tax Amount')
    amount_rounding = fields.Monetary('Amount Delta')
    amount_total = fields.Monetary(string="Amount Total")

    company_id = fields.Many2one('res.company', string='Company', related='account_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', related='invoice_id.currency_id', store=True, readonly=True)
    base = fields.Monetary(string='Base', compute='_compute_base_amount', store=True)
