

from odoo import api, fields, models, _



class sale_order(models.Model):
    _inherit = "sale.order"

    image_late = fields.Binary(related="partner_id.image_late_paiement", string='Image for late paiement')


