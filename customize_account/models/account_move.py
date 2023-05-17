from odoo import fields, models


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
    
    picking_ref = fields.Many2one('stock.picking', 
                                  compute='_compute_picking_id', 
                                  string='Bon de livraison',)
                                  
    
    def _compute_picking_id(self):
        for move in self:
            order = self.env['sale.order'].search([('name', '=', move.invoice_origin)], limit=1)
            if order and order.picking_ids:
                pickings = order.picking_ids.filtered(lambda p: p.state == 'done')
                move.picking_ref = pickings[0]
