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


class StockSSCC(models.Model):
    _name = "stock.sscc"
    _description = "SSCC Label"
    _order = "name"

    picking_id = fields.Many2one('stock.picking', string='Picking', index=True)
    nb_sscc = fields.Integer('Nb', compute='compute_nb_sscc', store=False)
    nb_total_sscc = fields.Integer(related='picking_id.nb_total_sscc')
    name = fields.Char(compute="compute_name", string='SSCC', store=True, index=True)
    identifier = fields.Char('IDENTIFIER', default='00')
    prefixe = fields.Char('PREFIXE', default='0')
    cnuf = fields.Char('CNUF', default='7002221')
    serial = fields.Char('SERIAL', default='/')

    def compute_nb_sscc(self):
        """ get numerotation of sscc """
        for label in self:
            label_ids = self.search([('picking_id', '=', label.picking_id.id)])
            number = 1
            for label_check in label_ids:
                if label_check == label:
                    break
                else:
                    number += 1
            label.nb_sscc = number

    @api.depends('serial', 'cnuf', 'identifier')
    def compute_name(self):
        """ Compute the number of the SSCC """
        for label in self:
            sscc = "%s%s%s" % (label.prefixe, label.cnuf, label.serial)
            label.name = "%s%s%s" % (label.identifier, sscc, ean_checksum(sscc))

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.serial == '/':
                serial = self.env['ir.sequence'].get('stock.sscc.code') or '/'
                record.update({'serial': serial})
        return records
