
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from collections import defaultdict
import datetime
import time

DEFAULT_EXPIRATION_TIME = 15

class StockLot(models.Model):
    _inherit = 'stock.lot'

    company_id = fields.Many2one('res.company', 'Company',
                                 required=True,
                                 store=True,
                                 index=True,
                                #  added default to not violates not-null constraint at db_synchro
                                 default=lambda self: self.env.company)

    date = fields.Date(string='Date de création')
    ref = fields.Char('Internal Reference', compute="put_ref", readonly=False, index=True, store=True,
                      help="Internal reference with incremente index ")
    life_date = fields.Date(string='Date limite de consommation')
    temp_old_barcode = fields.Char(string='migration Barcode 1', index=True)
    temp2_old_barcode = fields.Char(string='migration Barcode 2', index=True)
    barcode = fields.Char(string='Barcode', compute="get_barcode", store=True, index=True)
    barcode_ext = fields.Char(string='Barcode (ESPERA)', compute="get_barcode", store=True, index=True)
    barcode_ext2 = fields.Char(string='Barcode (DIGI)', compute="get_barcode", store=True, index=True)
    use_expiration_date = fields.Boolean('use_expiration_date', store=True, default=True, compute="freeze_value")
    blocked = fields.Boolean('Blocked', help="Block the possibility of reserve this lot")
    expiration_date = fields.Datetime(
        string='Expiration Date', compute=False, store=True, readonly=False, default=False,
        help='This is the date on which the goods with this Serial Number may become dangerous and must not be consumed.')
    date_label = fields.Char("label date text:", compute="get_date_text")

    kg_price = fields.Float('Price Kg')
    unit_price = fields.Float('Price Unit')

    downstream_picking = fields.Many2many('stock.picking', string='Customer picking', compute='get_downstream_picking')
    upstream_picking = fields.Many2many('stock.picking', string='Supplier picking', compute='get_upstream_picking')

    def get_downstream_lot(self):
        """ Get all linked in production """
        res = self.env['stock.lot']
        mrp_in_move_line = self.env['stock.move.line'].search([('lot_id', 'in', self.ids), ('production_id', '!=', False)])
        mrp_out_move_line = self.env['stock.move.line'].search([('production_from_id', 'in', mrp_in_move_line.production_id.ids)])
        for line in mrp_out_move_line:
            if line.lot_id:
                res |= line.lot_id.get_downstream_lot()
        res |= self
        return res

    @api.depends('name')
    def _compute_sale_order_ids(self):
        """ count the sale in downstream """
        for lot in self:
            sale_order_ids = self.env['sale.order']
            for picking in lot.get_downstream_picking():
                sale_order_ids |= picking.group_id.sale_id
            lot.sale_order_ids = sale_order_ids
            lot.sale_order_count = len(lot.sale_order_ids)

    def get_downstream_picking(self):
        """ Get tracking of this lot """
        res = self.env['stock.picking']

        for lot in self:
            lot_ids = lot.get_downstream_lot()
            outgoing_move_line = self.env['stock.move.line'].search([('lot_id', '=', lot_ids.ids),
                                                                     ('picking_type_code', '=', 'outgoing')])
            downstream_picking = self.env['stock.picking']
            for line in outgoing_move_line:
                downstream_picking |= line.picking_id
            lot.downstream_picking = downstream_picking
            res |= downstream_picking
        return res

    def _compute_delivery_ids(self):
        """ count customer with this lot """
        for lot in self:
            lot.delivery_count = len(lot.downstream_picking)

    def action_lot_open_transfers(self):
        self.ensure_one()

        action = {
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
            'name': _("Delivery orders of %s", self.display_name),
            'domain': [('id', 'in', self.downstream_picking.ids)],
            'view_mode': 'tree,form'
        }
        return action

    def get_upstream_lot(self):
        """ Get all linked in production """
        res = self.env['stock.lot']
        mrp_out_move_line = self.env['stock.move.line'].search([('lot_id', 'in', self.ids), ('production_from_id', '!=', False)])
        mrp_in_move_line = self.env['stock.move.line'].search([('production_id', 'in', mrp_out_move_line.production_from_id.ids)])
        for line in mrp_in_move_line:
            if line.lot_id:
                res |= line.lot_id.get_upstream_lot()
        res |= self
        return res

    def get_upstream_picking(self):
        """ Get tracking of this lot """
        res = self.env['stock.picking']

        for lot in self:
            lot_ids = lot.get_upstream_lot()
            incoming_move_line = self.env['stock.move.line'].search([('lot_id', '=', lot_ids.ids),
                                                                     ('picking_type_code', '=', 'incoming')])
            upstream_picking = self.env['stock.picking']
            for line in incoming_move_line:
                upstream_picking |= line.picking_id
            lot.upstream_picking = upstream_picking
            res |= upstream_picking
        return res

    def update_imported_date(self):
        """ Some time the date is not set """
        for lot in self:
            if not lot.expiration_date:
                lot.expiration_date = lot.use_date or lot.alert_date or lot.removal_date or lot.date

    def get_date_text(self):
        """ Define the legal text to put on label, best before or expiration dates"""
        for lot in self:
            if lot.product_id.life_date:
                text = _("Expiration date:")
            elif lot.product_id.use_date:
                text = _("Best before date:")
            else:
                text = _("Date:")

            CODE_CP850 = {'Ç': '\80', 'ü': '\81', 'é': '\82', 'â': '\83', 'ä': '\84', 'à': '\85', 'å': '\86',
                          'ç': '\87', 'ê': '\88', 'ë': '\89',
                          'è': '\8A', 'ï': '\8B', 'î': '\8C', 'ì': '\8D', 'Ä': '\8E', 'Å': '\8F', '°': '\F8'}
            for key in CODE_CP850.keys():
                if key in text:
                    text = text.replace(key, CODE_CP850[key])
            lot.date_label = text

    def name_get(self):
        res = []
        for lot in self:
            lot_name = "{}".format(lot.ref or '?')
            if lot.expiration_date:
                lot_name += " {:%d/%m/%Y}".format(lot.expiration_date)
            res.append((lot.id, lot_name))
        return res

    def freeze_value(self):
        """ Freeze configuration"""
        for line in self:
            line.use_expiration_date = True

    @api.constrains('name', 'ref', 'product_id', 'company_id')
    def _check_unique_lot(self):
        domain = [('product_id', 'in', self.product_id.ids),
                  ('company_id', 'in', self.company_id.ids),
                  ('name', 'in', self.mapped('name'))]
        fields = ['company_id', 'product_id', 'name', 'ref']
        groupby = ['company_id', 'product_id', 'name', 'ref']
        records = self._read_group(domain, fields, groupby, lazy=False)
        error_message_lines = []
        for rec in records:
            if rec['__count'] != 1:
                product_name = self.env['product.product'].browse(rec['product_id'][0]).display_name
                error_message_lines.append(_(" - Product: %s, Serial Number: %s", product_name, rec['name']))
        if error_message_lines:
            raise ValidationError(_('The combination of serial number and product must be unique across a company.\nFollowing combination contains duplicates:\n') + '\n'.join(error_message_lines))

    @api.depends('name')
    def put_ref(self):
        """ Write ref on lot"""
        for lot in self:
            # Search doubloon, format name
            format_name = ''.join(filter(str.isalnum, lot.name))
            format_name = format_name.upper().zfill(6)
            ref_index = 1
            for another_lot in self.search([('ref', '=ilike', format_name + '-%%')]):
                ref = another_lot.ref.split('-')
                if len(ref) == 2 and ref[1].isnumeric() and int(ref[1]) >= ref_index:
                    ref_index = int(ref[1]) + 1

            lot_ref = lot.name + "-" + "{}".format(ref_index).zfill(2)
            while self.search([('ref', '=', lot_ref)]):
                ref_index += 1
                lot_ref = lot.name + "-" + "{}".format(ref_index).zfill(2)
            lot.ref = lot_ref

    @api.onchange('name')
    def onchange_name(self):
        """ change ref"""
        self.put_ref()

    @api.model
    def create_production_lot(self, product):
        """ Production lot name like HENNART standard """
        def search_free_name(product, condition=None):
            """ return free name """
            if condition is None:
                condition = []
            prodlot_y = time.strftime('%y')[1:]
            prodlot_j = time.strftime('%j').zfill(3)
            lot_search = 'XXXXXX'

            for i in range(1, 99):
                lot_search = prodlot_y + prodlot_j + str(i).zfill(2)
                condition_name = condition + [('name', '=', lot_search)]
                lot_ids = self.search(condition_name)
                if i == 99:
                    # The counter is on max value
                    if not condition:
                        # only 99 lots by product per day
                        lot_search = search_free_name(product, condition=[('product_id', '=', product.id)])
                    else:
                        raise ValidationError('Not possible to attribute a new lot number, create one manually')
                    break
                elif not lot_ids:
                    break
            return lot_search

        lot_search = search_free_name(product=product)
        expiration_time = product.expiration_time or product.use_time or DEFAULT_EXPIRATION_TIME
        expiration_date = fields.Datetime.now() + datetime.timedelta(days=expiration_time)

        vals_lot = {
            'name': lot_search,
            'product_id': product.id,
            'expiration_date': expiration_date,
        }
        new_lot = self.env['stock.lot'].create(vals_lot)
        return new_lot

    @api.depends('ref', 'expiration_date', 'product_id')
    def get_barcode(self):
        """ define the barcode of lot
        the barcode is composite with:
        5 char: product code
        8 char: stock.lot.id
        1 char: product code type
        6 char: expiration date
        6 char: weight
        """
        for lot in self:
            # format product code with length of 6
            if lot.product_id and len(lot.product_id.default_code) == 5:
                product_code = lot.product_id.default_code + 'X'
            elif lot.product_id and len(lot.product_id.default_code) == 6:
                product_code = lot.product_id.default_code or ''
            else:
                product_code = '00000X'

            label_dlc = lot.expiration_date or lot.use_date
            if label_dlc:
                if label_dlc.hour < 12:
                    # timezone adjustement
                    label_dlc += datetime.timedelta(hours=11)
                label_dlc_new = label_dlc.strftime("%d%m%y")
                label_dlc_old = label_dlc.strftime("%d%m%Y")
                label_dlc_old2 = label_dlc.strftime("%y%m%d")
            else:
                label_dlc_new = '000000'
                label_dlc_old = '00000000'
                label_dlc_old2 = '000000'

            lot.barcode = product_code[:5] + '-' + str(lot.id).zfill(7) + product_code[5] + label_dlc_new + '000000'
            lot.barcode_ext = product_code[:5] + lot.name + product_code[5] + label_dlc_old + '000000'
            lot.barcode_ext2 = product_code[:5] + lot.name[:6] + product_code[5] + label_dlc_old2 + '000000'
