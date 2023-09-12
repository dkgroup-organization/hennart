from odoo import fields, models, api, Command

PAYMENT_STATE_SELECTION = [
        ('not_paid', 'Not Paid'),
        ('in_payment', 'In Payment'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('reversed', 'Reversed'),
        ('invoicing_legacy', 'Invoicing App Legacy'),
]


class AccountMove(models.Model):
    _inherit = "account.move"

    picking_id = fields.Char(string="Bon de livraison")
    incoterm_port = fields.Char(string="Port of entry")
    incoterm_date = fields.Date(string="Date of arrival in UK")
    payment_method_id = fields.Char(string="Methode de paiement")

    total_ht = fields.Float(string='Total HT')
    total_tva = fields.Float(string='Total TVA')
    total_ttc = fields.Float(string='Total TTC')
    piece_comptable = fields.Char(string='ID piece comptable')

    account_id = fields.Many2one(
        'account.account',
        string='Account',
    )

    picking_ids = fields.Many2many('stock.picking', string='Pickings')

    payment_state = fields.Selection(
        selection=PAYMENT_STATE_SELECTION,
        string="Payment Status",
        compute=False, store=True, readonly=False,
        copy=False,
        default='not_paid',
        tracking=True,
    )
    suitable_journal_ids = fields.Many2many(
        'account.journal',
        compute='_compute_suitable_journal2_ids',
    )

    @api.depends('company_id', 'invoice_filter_type_domain', 'src_dest_country_id')
    def _compute_suitable_journal2_ids(self):
        for m in self:
            journal_type = m.invoice_filter_type_domain or 'general'
            company_id = m.company_id.id or self.env.company.id
            domain = [('company_id', '=', company_id), ('type', '=', journal_type)]
            if m.src_dest_country_id:
                domain += [('country_ids', 'in', m.src_dest_country_id.ids)]
            else:
                domain += [('country_ids', '=', False)]
            m.suitable_journal_ids = self.env['account.journal'].search(domain)

    @api.onchange('partner_id')
    def onchange_partner2_id(self):
        """ select journal by country"""
        if self.journal_id not in self.suitable_journal_ids:
            self.journal_id = False

    def action_valide_imported(self):
        """ Valid a imported move, there is some correction todo"""
        uom_weight = self.env['product.template'].sudo()._get_weight_uom_id_from_ir_config_parameter()
        remote_server = self.env['synchro.server'].search([])
        sync_obj = remote_server[0].obj_ids.search([('model_name', '=', 'account.invoice.line')])

        for move in self:
            if move.state != 'draft' or not move.piece_comptable or not move.fiscal_position_id:
                continue

            if move.fiscal_position_id.id in [2, 3]:
                # error imported reload
                self.env['synchro.obj.line'].search([('obj_id.model_name', '=', 'account.invoice'),
                                                     ('local_id', '=', move.id)]).update_values()
                if move.fiscal_position_id.id in [2, 3]:
                    move.fiscal_position_id = False
                    # Manual correction needed
                    continue

            if not move.invoice_line_ids:
                " Import the line"
                piece_comptable = eval(move.piece_comptable)
                if len(piece_comptable):
                    domain = [('invoice_id.move_id', '=', piece_comptable[0])]
                    remote_ids = sync_obj.remote_search(domain)
                    remote_values = sync_obj.remote_read(remote_ids)
                    sync_obj.write_local_value(remote_values)
            for line in move.invoice_line_ids:
                if line.product_uos == uom_weight:
                    line.manual_weight = line.quantity
                else:
                    line.uom_qty = line.quantity

            move.invoice_line_ids.get_product_uom_id()

            if move.piece_comptable and move.total_ttc == move.amount_total:
                if move.journal_id.type == 'sale':
                    move.sudo().action_post()
                    if move.total_ttc == move.amount_total:
                        move.payment_state = 'paid'
                else:
                    if move.partner_id.vat and move.fiscal_position_id and move.piece_comptable and move.total_ttc == move.amount_total:
                        move.sudo().action_post()
                        if move.total_ttc == move.amount_total:
                            move.payment_state = 'paid'
                    else:
                        # update this
                        pass

    def compute_picking_ids(self):
        for invoice in self:
            order_ids = invoice.invoice_line_ids.mapped('sale_line_ids.order_id')
            picking_ids = self.env['stock.picking'].search([
                ('sale_id', 'in', order_ids.ids),
                ('state', '=', 'done')
            ])
            if picking_ids:
                invoice.picking_ids = picking_ids
            else:
                invoice.picking_ids = False
