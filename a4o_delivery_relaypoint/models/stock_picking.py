# This file is part of an Adiczion's Module.
# The COPYRIGHT and LICENSE files at the top level of this repository
# contains the full copyright notices and license terms.
from odoo import api, models, fields, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class StockQuantPackage(models.Model):
    _inherit = "stock.quant.package"

    mandatory_weight = fields.Boolean(string='Mandatory Shipping Weight',
        compute='_compute_mandatory_weight')

    @api.depends('package_type_id')
    def _compute_mandatory_weight(self):
        for record in self:
            result = False
            if record.package_type_id:
                method_name = ('%s_compute_mandatory_weight'
                    % record.package_type_id.package_carrier_type)
                if hasattr(record, method_name):
                    result = getattr(record, method_name)()
            record.mandatory_weight = result


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_new_picking_values(self):
        result = super()._get_new_picking_values()
        if result:
            original = (self.group_id
                and self.group_id.sale_id
                and self.group_id.sale_id.original_partner_shipping_id)
            result.update({'original_partner_id': original.id})
        return result


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    relaypoint_delivery = fields.Boolean(
        related='carrier_id.relaypoint_delivery', readonly=True)
    original_partner_id = fields.Many2one('res.partner', 'Original Partner',
        readonly=True)

    def button_validate(self):
        self.ensure_one()
        if (self.relaypoint_delivery and not self.partner_id.code_relaypoint):
            raise UserError(_("You cannot choose a relay point delivery "
                "without choosing a relay point! Go to the 'additional info' "
                "page to select the relay point!"))
        return super().button_validate()

    def action_get_relaypoint(self):
        context = dict(self.env.context or {})
        # Get addresses
        addr = self.partner_id.parent_id or self.partner_id
        address_ids = [addr.id] + [x.id for x in addr.child_ids]
        context.update({
            'picking_id': self.id,
            'address_ids': address_ids,
            'default_address': self.partner_id.id,
            })
        return {
            'name': _('Select the address'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'delivery.carrier.relaypoint',
            'view_id': self.env.ref(
                'a4o_delivery_relaypoint.select_relaypoint_view_form').id,
            'type': 'ir.actions.act_window',
            'context': context,
            'target': 'new'
        }

    @api.depends('sale_id')
    def get_delivery_price(self):
        for record in self:
            if not record.sale_id:
                return 0.0
            return sum([
                    l.price_total
                    for l in record.sale_id.order_line
                    if l.is_delivery
                    ])