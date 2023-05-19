from odoo import fields, models, api


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
    
    payment_state = fields.Selection(
        selection=[
            ('not_paid', 'Not Paid'),
            ('in_payment', 'In Payment'),
            ('paid', 'Paid'),
            ('partial', 'Partially Paid'),
            ('reversed', 'Reversed'),
            ('invoicing_legacy', 'Invoicing App Legacy'),
        ],
        string="Payment Status",
        # compute='_compute_payment_state', 
        store=True, 
        readonly=False,
        copy=False,
        tracking=True,
    )
    
    picking_ids = fields.Many2many('stock.picking', string='Pickings', compute='_compute_picking_ids')

    @api.depends('invoice_line_ids.sale_line_ids.order_id')
    def _compute_picking_ids(self):
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
