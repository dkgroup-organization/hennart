

from odoo import _, api, fields, models
from odoo.tools import float_compare


class AccountMoveLine(models.Model):
    """ Add the possibility to invoice by weight price.
    Get information in stock.move
    weight, quantity, lot
    """

    _inherit = "account.move.line"

    product_packaging = fields.Many2one(
        'product.packaging',
        string='Packaging',
        )

    prodlot_id = fields.Many2many(
        'stock.lot',
        string='Production lot',
        )
    
    lot = fields.Char()

    stock_move_ids = fields.Many2many('stock.move', string="Stock moves")
    default_code = fields.Char('Code', related='product_id.default_code', store=True)


    weight = fields.Float("Weight")

    cadeau = fields.Float(string='Remise Total')

    cost_price = fields.Float(string='Prix de revient')

    discount1 = fields.Float(string='R1 %')
    discount2 = fields.Float(string='R2 %')

    margin = fields.Float(string='Marge total')
    margin_percent = fields.Float(string='Marge %')

    number_of_pack = fields.Float(string='Nb pack')
    number_of_unit = fields.Float(string='Nb unit')

    promotion = fields.Float(string='Promo %')
    
    uom_qty = fields.Float(string="Qty")

    type = fields.Char()

    initial_price = fields.Float(string='Price')

    histo_cost_price = fields.Float()

    product_uos = fields.Many2one('uom.uom', string="Udv")
    
    price_net = fields.Float(
        string='Prix net',
        compute='_compute_price_net'
    )

    supplierinfo_id = fields.Many2one('product.supplierinfo',
                                      compute='get_supplierinfo_id',
                                      string="Supplier info", store=True)

    product_uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string='Unit',
        compute='get_product_uom_id', store=True, readonly=True,
        domain="[]",
        ondelete="restrict",
    )

    quantity = fields.Float(
        string='Quantity',
        compute='get_quantity', store=True, precompute=True,
        digits='Product Unit of Measure',
        help="Number of product sold or purchase in kg or unit. "
    )

    @api.depends('product_id', 'move_id.move_type', 'move_id.partner_id', 'move_id.state')
    def get_supplierinfo_id(self):
        """ get supplier info to define price, unit and packing"""
        for line in self:
            if line.move_id.state in ['cancel', 'posted']:
                continue
            elif line.move_id.move_type in ['out_invoice', 'out_refund', 'out_receipt', 'entry']:
                line.supplierinfo_id = False

            elif line.supplierinfo_id and line.supplierinfo_id.product_id == line.product_id and \
                    line.supplierinfo_id.partner_id == line.move_id.partner_id:
                pass
            elif line.product_id and line.move_id.partner_id:
                line.supplierinfo_id = line.product_id._select_seller(
                    partner_id=line.move_id.partner_id,
                    quantity=1)
            else:
                line.supplierinfo_id = False

    @api.depends('product_id', 'move_id.move_type', 'move_id.partner_id', 'move_id.state')
    def get_product_uom_id(self):
        """ Return the unit to use to invoice (unit or Kg), unit can't be changing"""
        for line in self:
            if line.move_id.state in ['cancel', 'posted'] and line.product_uom_id:
                continue
            elif line.product_id:
                if line.move_id.move_type in ['out_invoice', 'out_refund', 'out_receipt', 'entry']:
                    line.product_uom_id = line.product_id.uos_id or self.env.ref('uom.product_uom_unit')
                elif line.move_id.move_type in ['in_invoice', 'in_refund', 'in_receipt']:
                    if line.supplierinfo_id:
                        line.product_uom_id = line.supplierinfo_id.product_uos or line.product_id.uos_id or self.env.ref('uom.product_uom_unit')
                    else:
                        line.product_uom_id = line.product_id.uos_id or self.env.ref('uom.product_uom_unit')
                else:
                    line.product_uom_id = line.product_id.uos_id or self.env.ref('uom.product_uom_unit')
            else:
                line.product_uom_id = self.env.ref('uom.product_uom_unit')

    @api.constrains('product_uom_id')
    def _check_product_uom_category_id(self):
        """ Not used"""
        pass

    def update_stock_move(self):
        """ Update information based on picking"""
        for invoice_line in self:
            stock_move_ids = self.env['stock.move']
            for sale_line in invoice_line.sale_line_ids:
                stock_move_ids |= sale_line.move_ids
            for purchase_line in invoice_line.purchase_line_id:
                stock_move_ids |= purchase_line.move_ids

            invoice_line.stock_move_ids |= stock_move_ids


    @api.depends('product_uom_id', 'weight', 'uom_qty', 'move_id.state')
    def get_quantity(self):
        """ get supplier info to define price, unit and packing"""
        uom_weight = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()

        for line in self:
            if line.move_id.state in ['cancel', 'posted']:
                continue
            elif line.product_uom_id == uom_weight:
                line.quantity = line.weight * line.uom_qty
            else:
                line.quantity = line.uom_qty

    def init_stock_move(self):
        """ Init stock_move to restart evaluation"""
        self.stock_move_ids = False

    @api.depends('price_unit', 'discount')
    def _compute_price_net(self):
        for line in self:
            line.price_net = line.price_unit - (line.price_unit * line.discount / 100)

    @api.onchange('supplierinfo_id')
    def onchange_supplierinfo(self):
        """ Load value"""
        for line in self:
            if line.supplierinfo_id:
                line.discount1 = line.supplierinfo_id.discount1
                line.discount2 = line.supplierinfo_id.discount2
                line.initial_price = line.supplierinfo_id.base_price
                if line.supplierinfo_id.product_name:
                    line.name = line.supplierinfo_id.product_name
                if line.supplierinfo_id.product_code:
                    line.name = "[{}] {}".format(line.supplierinfo_id.product_code, line.supplierinfo_id.product_name)
                if line.supplierinfo_id.type == "add":
                    line.price_unit = line.supplierinfo_id.base_price * \
                        (1 - ((line.supplierinfo_id.discount1 + line.supplierinfo_id.discount2) / 100.0))
                else:
                    line.price_unit = line.supplierinfo_id.base_price * \
                        (1 - (line.supplierinfo_id.discount1 / 100.0)) * (1 - (line.supplierinfo_id.discount2 / 100.0))
            else:
                line.discount1 = line.supplierinfo_id.discount2 = 0.0
