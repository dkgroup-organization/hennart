
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class Stock_lot(models.Model):
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
    barcode_ext = fields.Char(string='Barcode (external)', compute="get_barcode", store=True, index=True)
    use_expiration_date = fields.Boolean('use_expiration_date', compute="freeze_value")
    blocked = fields.Boolean('Blocked', help="Block the possibility of reserve this lot")
    expiration_date = fields.Datetime(
        string='Expiration Date', compute=False, store=True, readonly=False, default=False,
        help='This is the date on which the goods with this Serial Number may become dangerous and must not be consumed.')

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
            lot.ref = lot.name + "-" + "{}".format(ref_index).zfill(2)

    @api.onchange('name')
    def onchange_name(self):
        """ change ref"""
        self.put_ref()

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

            label_dlc = lot.expiration_date or lot.use_date or False
            label_dlc_new = label_dlc and label_dlc.strftime("%d%m%y") or '000000'
            label_dlc_old = label_dlc and label_dlc.strftime("%d%m%Y") or '000000'

            lot.barcode = product_code[:5] + '-' + str(lot.id).zfill(7) + product_code[5] + label_dlc_new + '000000'

            if lot.temp_old_barcode:
                lot.barcode_ext = lot.temp_old_barcode
            else:
                lot.barcode_ext = product_code[:5] + lot.name[:6] + product_code[5] + label_dlc_old + '000000'