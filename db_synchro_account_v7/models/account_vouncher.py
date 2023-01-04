# -*- coding: utf-8 -*-

from odoo import fields, models
import logging
_logger = logging.getLogger(__name__)


class AccountVoucher(models.Model):
    _name = "account.voucher"
    _description = "Imported Voucher"
    _order = "date desc, id desc"

    name = fields.Char(string='Memo', index=True)

    type = fields.Selection([
            ('sale','Sale'),
            ('purchase','Purchase'),
            ('payment','Payment'),
            ('receipt','Receipt'),
        ], index=True)
    date = fields.Date(string='Date', index=True)
    journal_id = fields.Many2one('account.journal', string='Journal')
    account_id = fields.Many2one('account.account')
    narration = fields.Text('Notes')
    company_id = fields.Many2one('res.company', string='Company')
    currency_id = fields.Many2one('res.currency', string='Currency')
    state = fields.Selection(
            [('draft','Draft'),
             ('cancel','Cancelled'),
             ('proforma','Pro-forma'),
             ('posted','Posted')
            ], string='Status')

    amount = fields.Monetary(string='Total')
    reference = fields.Char(string='Payment Ref.')
    number = fields.Char('number')
    move_id = fields.Many2one('account.move', string='MOVE Account', index=True)
    partner_id = fields.Many2one('res.partner')

    voucher_line_ok = fields.Boolean('Ready to post')
    voucher_post_ok = fields.Boolean('Post done')
    voucher_post = fields.Selection(related='move_id.state', store=True)
    synchro_obj = fields.Many2one('synchro.obj')

    def recompute_voucher(self):
        "recompute this imported vouncher"

        for voucher in self:
            if not voucher.move_id:
                voucher_vals = {
                    'name': voucher.number,
                    'communication': voucher.reference,
                    'amount': voucher.amount,
                    'payment_date': voucher.date,
                    'currency_id': voucher.currency_id.id,
                    'journal_id': voucher.journal_id.id,
                    'partner_id': voucher.partner_id.id,
                    }

                if voucher.amount > 0.0:
                    if voucher.type == 'payment':
                        voucher_vals['payment_type'] = 'outbound'
                        voucher_vals['payment_method_id'] = 2
                        voucher_vals['partner_type'] = 'supplier'

                    elif voucher.type == 'receipt':
                        voucher_vals['payment_type'] = 'inbound'
                        voucher_vals['payment_method_id'] = 1
                        voucher_vals['partner_type'] = 'customer'

                    if not self.env['account.payment'].search([('name', '=', voucher.number)]):
                        new_payment = self.env['account.payment'].create(voucher_vals)
                        new_payment.post()
                        if new_payment.move_line_ids:
                            voucher.move_id = new_payment.move_line_ids[0].move_id

    def import_remote_move(self):
        "reimport this voucher"
        return True
