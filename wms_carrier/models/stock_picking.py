
from odoo import models, fields ,api


class StockPicking(models.Model):
    _inherit = "stock.picking"

    carrier_order_id = fields.Many2one('delivery.carrier.order',string='Carrier order')
    nb_container = fields.Integer('Nb container')
    nb_pallet = fields.Integer('Nb pallet')
    number_of_packages = fields.Integer('Nb packages')
    nb_pallet_europe = fields.Integer('Nb Pallets europe')
    nb_pallet_perdu = fields.Integer('Nb Pallets Perdu')

    def check_carrier(self):
        context = {}
        carrier_obj = self.env['delivery.carrier.order']
        carrier_ids = []
        for picking in self:
            if picking.id not in carrier_ids:
                carrier_ids.append(picking.id)
        carrier_obj.check_state(carrier_ids)

        return True

    def action_confirm(self):
        carrier_order_obj = self.env['delivery.carrier.order']
        for picking in self:
            if picking.carrier_id:
                date_picking = picking.scheduled_date.date()

                carrier_order_id = carrier_order_obj.search([('carrier_id', '=', picking.carrier_id.id),
                                                             ('date_expected2','=',date_picking)])
                if carrier_order_id:
                    picking.carrier_order_id = carrier_order_id.id
                else:
                    carrier_order_name = picking.carrier_id.name
                    date_expected = picking.carrier_id.get_delivery_hours(picking.scheduled_date)
                    carrier_order_vals = {
                        'name': carrier_order_name or "",
                        'carrier_id': picking.carrier_id.id,
                        'date_expected': date_expected,
                        'warehouse_id': 1,
                        'nb_picking': 1,
                        'nb_line': len(picking.move_line_ids),
                        'weight': picking.weight,
                        'state': 'confirmed'
                        }
                    carrier_order_id = carrier_order_obj.create(carrier_order_vals)
                    picking.carrier_order_id = carrier_order_id.id
        return super(StockPicking, self).action_confirm()
