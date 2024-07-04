# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models, api


class StockMove(models.Model):
    _inherit = "stock.move"

    whs_id = fields.Many2one('stock.warehouse', string='Source WH',
                             related='location_id.warehouse_id', store=True, index=True)
    whd_id = fields.Many2one('stock.warehouse', string='Destination WH',
                             related='location_dest_id.warehouse_id', store=True, index=True)
    wh_filter = fields.Boolean('In/Out move', compute="get_wh_in_out", store=True, index=True)
    product_tmpl_id = fields.Many2one(
        'product.template', 'Product Template',
        related='product_id.product_tmpl_id', store=True,
        help="Technical: used in views")

    @api.depends('location_id', 'location_dest_id', 'state', 'product_qty', 'product_id')
    def get_wh_in_out(self):
        """ filter the move to use in report quantity and prevision"""
        for move in self:
            if move.state in ['cancel', 'draft', 'done']:
                move.wh_filter = False
            elif move.product_id.product_tmpl_id.type != 'product':
                move.wh_filter = False
            elif move.product_qty == 0.0:
                move.wh_filter = False
            elif move.location_id.usage in ['internal', 'transit'] or \
                    move.location_dest_id.usage in ['internal', 'transit']:
                if move.location_id.warehouse_id != move.location_dest_id.warehouse_id:
                    move.wh_filter = True
                else:
                    move.wh_filter = False
            else:
                move.wh_filter = False

    def action_open_origin(self):
        """ Open the form view of the move's reference document, if one exists, otherwise open form view of self
        """
        self.ensure_one()
        action = {}
        for check_fields in ['picking_id', 'inventory_id', 'production_id', 'raw_material_production_id']:
            if hasattr(self, check_fields):
                source = getattr(self, check_fields )
                if source and source.check_access_rights('read', raise_exception=False):
                    action =  {
                        'res_model': source._name,
                        'type': 'ir.actions.act_window',
                        'views': [[False, "form"]],
                        'target': 'new',
                        'res_id': source.id,
                    }
                    break
        action = action or {
            'res_model': self._name,
            'type': 'ir.actions.act_window',
            'views': [[False, "form"]],
            'target': 'new',
            'res_id': self.id,
        }
        return action
