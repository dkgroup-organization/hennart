# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from datetime import date, timedelta, datetime
from odoo import api, fields, models, Command, _
from odoo.exceptions import UserError, ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    date_delivered = fields.Datetime("delivered date", help="Customer delivered date")
    commitment_date = fields.Datetime("Warehouse date", help="The date when the delivery is available on warehouse")

    @api.model
    def timezone_2_utc(self, date, time, timezone="Europe/Paris"):
        """ return datetime with time (in float) with conversion in  timezone to UTC
        use partner.crm.appointment.timezone_2_utc function"""
        return self.env['partner.crm.appointment'].timezone_2_utc(date, time, timezone=timezone)

    def onchange_partner_id_dates(self):
        """ update commitment_date """
        self.ensure_one()
        res = {}
        today1 = datetime.now()
        if self.partner_id.appointment_delivery_ids:
            app = self.partner_id.appointment_delivery_ids[0]
            res['carrier_id'] = self.partner_id.appointment_delivery_ids[0].carrier_id.id
            load_time = self.partner_id.appointment_delivery_ids[0].load_time

            if today1 > self.timezone_2_utc(today1, 12):
                today1 += timedelta(days=1)

            while today1.weekday() != int(app.load_day):
                # 0 for monday
                today1 += timedelta(days=1)
            date_entrepot = today1
            today2 = date_entrepot

            while today2.weekday() != int(app.delivery_day):
                today2 += timedelta(days=1)
            delivered_date = today2

            res['date_delivered'] = self.timezone_2_utc(delivered_date, load_time)
            res['commitment_date'] = self.timezone_2_utc(date_entrepot, load_time)
        return res

    def onchange_partner_id_address(self):
        """ update commitment_date """
        self.ensure_one()

        if self.partner_id:
            res = {'partner_shipping_id': self.partner_id.id, 'partner_invoice_id': self.partner_id.id}
        else:
            res = {'partner_shipping_id': False, 'partner_invoice_id': False}

        for contact in self.partner_id.child_ids:
            if contact.type == 'delivery':
                res['partner_shipping_id'] = contact.id
            if contact.type == 'invoice':
                res['partner_invoice_id'] = contact.id
        return res

    @api.onchange('partner_id')
    def onchange_partner_id_cadence(self, date_order=None):
        # Clear the history lines when the partner is changed
        # If the partner is not null, get the order lines for the past 13 weeks
        nb_week = 12

        self.ensure_one()
        line_vals = []
        res = self.onchange_partner_id_dates()
        res.update(self.onchange_partner_id_address())
        commitment_date = res.get('commitment_date') or datetime.today()

        if self.partner_shipping_id.is_company:
            partner_shipping_id = self.partner_shipping_id
        elif self.partner_shipping_id.parent_id:
            partner_shipping_id = self.partner_shipping_id.parent_id
        else:
            partner_shipping_id = self.partner_shipping_id

        if self.state == 'draft' and self.partner_id:
            date_start = commitment_date - timedelta(days=commitment_date.weekday())  # monday
            date_from = date_start - timedelta(weeks=nb_week)
            order_lines = self.env['account.move.line'].search([
                '&',
                '|', ('move_id.partner_id', 'child_of', self.partner_id.id),
                ('move_id.partner_shipping_id', 'child_of', partner_shipping_id.ids),
                '&', ('move_id.invoice_date', '<=', date_start),
                '&', ('move_id.invoice_date', '>=', date_from),
                '&', ('move_id.move_type', '=', 'out_invoice'),
                '&', ('product_id.type', '=', 'product'),
                '&', ('uom_qty', '>=', 1.0),
                ('move_id.state', '=', 'posted')
            ])
            # Get the product ids of the order lines
            product_ids = (order_lines.mapped('product_id') - self.order_line.mapped('product_id')).sorted(key='name')

            for product in product_ids:
                product = product
                if product.sale_ok:
                    line_vals.append(Command.create({
                        'product_id': product.id,
                        'name': product.name,
                        'product_template_id': product.product_tmpl_id.id,
                        'product_uom_qty': 0.0,
                    }))
        if line_vals:
            res.update({'order_line': line_vals})

        self.update(res)

    def action_confirm(self):
        """ Check the sale order before confirmation"""
        self.check_discount()
        self.check_line()

        # unlink void line
        for line in self.order_line:
            if not line.product_uom_qty:
                line.unlink()

        res = super().action_confirm()

        # Check mrp.mo to order
        self.create_mo()

        return res

    def create_mo(self):
        """ Check mo to create, copy produced lot on picking """
        for sale in self:
            for picking in sale.picking_ids:
                picking.action_mrp()

    def button_test(self):
        """ TEST """
        for sale in self:
            for line in sale.order_line:
                print(line.product_id.name, line.product_id.production_forcasting)

    def check_discount(self):
        """ Check discount, futur"""
        pass

    def check_line(self):
        """ Check the line """
        for sale in self:
            check_line = {}
            for line in sale.order_line:
                if line.product_uom_qty == 0.0:
                    continue
                # Double same line
                key = "{}-{}-{}".format(line.product_id.id, line.price_unit, line.discount)
                if not key in check_line:
                    check_line[key] = line
                else:
                    raise ValidationError(_(
                        "There are 2 line with the same product and price. Please, group them:\n{}".format(
                            line.product_id.name)))

                # No stock available
                if line.free_qty_at_date < line.product_uom_qty:
                    raise ValidationError(_(
                        "There is not enough stock. Please, change quantity:\n{}".format(
                            line.product_id.name)))

    def create_custom_invoice(self):
        """ futur function"""
        pass

    @api.onchange('commitment_date')
    def _onchange_commitment_date(self):
        if self.commitment_date:
            promotions = self.env['sale.promotion'].search([
                ('date_start', '<=', self.commitment_date),
                ('date_end', '>=', self.commitment_date)
            ])

            new_lines = []
            for promo in promotions:
                if promo.qty_executed >= promo.quantity:
                    continue
                line = self.order_line.filtered(lambda l: l.product_id == promo.product_id)

                if line:
                    line.discount = promo.discount
                else:
                    new_lines.append(Command.create({
                        'product_id': promo.product_id.id,
                        'product_uom_qty': 0,
                        'discount': promo.discount,
                        'price_unit': promo.product_id.list_price,
                    }))

            if new_lines:
                self.update({'order_line': new_lines})

    def _prepare_invoice(self):
        """
        Change the partner beceause there is some holding to invoice
        """
        res = super()._prepare_invoice()
        if self.partner_id.parent_id:
            parent =  self.partner_id.parent_id
            if parent.third_account_customer and not self.partner_id.third_account_customer:
                res['partner_id'] = parent.id
            if parent.third_account_customer != self.partner_id.third_account_customer:
                pass
            if parent.third_account_customer == self.partner_id.third_account_customer:
                res['partner_id'] = parent.id
        return res
