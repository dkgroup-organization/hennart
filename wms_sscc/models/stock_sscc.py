import math

from odoo import fields, api
from odoo import models


def ean_checksum(eancode):
    oddsum = 0
    evensum = 0
    for i in range(len(eancode)):
        if i % 2 == 0:
            oddsum += int(eancode[i])
        else:
            evensum += int(eancode[i])
    total = (oddsum * 3) + evensum

    check = int(10 - math.ceil(total % 10)) % 10
    return str(check)


class stock_sscc(models.Model):
    _name = "stock.sscc"
    _description = "SSCC Label"
    _order = "name"

    @api.depends('serial', 'cnuf', 'identifier')
    def _update_info(self):

        for label in self:
            sscc = "%s%s%s" % (label.prefixe, label.cnuf, label.serial)
            label.name = "%s%s%s" % (label.identifier, sscc, ean_checksum(sscc))

    number = fields.Integer('Colis Numero:')
    picking_id = fields.Many2one('stock.picking', string='Picking')
    name = fields.Char(compute="_update_info", string='SSCC', store=True, index=True)
    identifier = fields.Char('IDENTIFIER', default='00')
    prefixe = fields.Char('PREFIXE', default='0')
    cnuf = fields.Char('CNUF', default='7002221')
    serial = fields.Char('SERIAL', default='/')

    @api.model
    def create(self, vals):
        obj = super(stock_sscc, self).create(vals)
        if obj.serial == '/':
            number = self.env['ir.sequence'].get('stock.sscc.code') or '/'
            obj.write({'serial': number})
        return obj
