# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.fields import Command

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    weight = fields.Float('weight', compute="compute_uos", store=True)
    product_uos = fields.Many2one('uom.uom', compute="compute_uos", store=True)
    product_uos_qty = fields.Float('Sale Qty', compute="compute_uos", store=True)
    product_uos_price = fields.Float('Sale Qty', compute="compute_uos", store=True)
    cadence = fields.Html(string="Cadencier", compute="compute_cadence", readonly=True)

    @api.depends('product_id')
    def compute_cadence(self):
        """ get the sale frequency of the product"""

        for line in self:

            date_from = datetime.today() - timedelta(weeks=13)
            order_lines = self.env['sale.order.line'].search([
                ('order_id.partner_id', '=', line.order_id.partner_id.id),
                ('order_id.date_order', '>=', date_from.date())
            ])
            product = line.product_id

            qty_by_week = {}
            # Loop through the past 13 weeks
            if product:
                for week in range(1, 14):
                    date_to = datetime.today() - timedelta(weeks=week - 1)
                    date_from = datetime.today() - timedelta(weeks=week)
                    # Get the quantity sold for the product for the current week
                    qty = sum(order_lines.filtered(lambda l: l.product_id.id == product.id and date_from.date() <= l.order_id.date_order.date() <= date_to.date()).mapped(
                        'product_uom_qty'))
                    # If the quantity is not zero, add it to the quantity by week dictionary
                    if qty != 0:
                        qty_by_week['{}'.format(week)] = qty

                    # If there is data for the product, create a table to display the quantity sold by week

            cadence_table = '<table style="border-collapse: collapse; width: 100%; table-layout: fixed;"><tr>'
            style_td = "border-left: 1px solid grey; width:7.6%; padding-left: 5px; padding-right: 5px;"
            style_text = " font-weight: bold; text-align: center;"
            for week in range(1, 14):
                qty = qty_by_week.get('{}'.format(week), '')
                if qty != '':
                    qty_str = str(int(qty))
                    cadence_table += '<td style="{}">{}</td>'.format(style_td + style_text, qty_str)
                else:
                    cadence_table += '<td style="{}"></td>'.format(style_td)
            cadence_table += '</tr></table>'
            line.cadence = cadence_table

    def _compute_customer_lead(self):
        """ The customer lead is more complexe in this project, It depend on location of customer """
        self.customer_lead = 0.0

    @api.depends('product_id', 'product_uom_qty', 'state')
    def compute_uos(self):
        """ compute the value of uos"""
        uom_weight = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()

        for line in self:
            if line.state in ['cancel', 'done']:
                continue

            if not line.product_id:
                line.weight = 0.0
                line.product_uos_qty = 0.0
                line.product_uos = self.env.ref('uom.product_uom_unit')
                line.product_uos_price = 0.0
            else:
                line.product_uos = line.product_id.uos_id

                if line.product_id.type == 'service' or line.is_delivery or line.display_type or line.is_downpayment:
                    line.weight = 0.0
                    line.product_uos_qty = line.product_uom_qty
                    line.product_uos_price = line.price_unit
                else:
                    line.weight = line.product_id.weight * line.product_uom_qty
                    if line.product_id.uos_id == uom_weight:
                        line.product_uos_qty = line.weight
                        line.product_uos_price = line.price_unit
                    else:
                        line.product_uos_qty = line.product_uom_qty * line.product_id.base_unit_count
                        line.product_uos_price = line.price_unit / (line.product_id.base_unit_count or 1.0)

    def _convert_to_tax_base_line_dict(self):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one()
        res = self.env['account.tax']._convert_to_tax_base_line_dict(
            self,
            partner=self.order_id.partner_id,
            currency=self.order_id.currency_id,
            product=self.product_id,
            taxes=self.tax_id,
            price_unit=self.product_uos_price,
            quantity=self.product_uos_qty,
            discount=self.discount,
            price_subtotal=self.price_subtotal,
        )
        return res

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            tax_results = self.env['account.tax']._compute_taxes([line._convert_to_tax_base_line_dict()])
            totals = list(tax_results['totals'].values())[0]
            amount_untaxed = totals['amount_untaxed']
            amount_tax = totals['amount_tax']

            line.update({
                'price_subtotal': amount_untaxed,
                'price_tax': amount_tax,
                'price_total': amount_untaxed + amount_tax,
            })

    @api.depends('state', 'price_reduce', 'product_id', 'untaxed_amount_invoiced', 'qty_delivered', 'product_uom_qty')
    def _compute_untaxed_amount_to_invoice(self):
        """ Total of remaining amount to invoice on the sale order line (taxes excl.) as
                total_sol - amount already invoiced
            where Total_sol depends on the invoice policy of the product.

            Note: Draft invoice are ignored on purpose, the 'to invoice' amount should
            come only from the SO lines.
        """
        for line in self:
            amount_to_invoice = 0.0
            if line.state in ['sale', 'done']:
                # Note: do not use price_subtotal field as it returns zero when the ordered quantity is
                # zero. It causes problem for expense line (e.i.: ordered qty = 0, deli qty = 4,
                # price_unit = 20 ; subtotal is zero), but when you can invoice the line, you see an
                # amount and not zero. Since we compute untaxed amount, we can use directly the price
                # reduce (to include discount) without using `compute_all()` method on taxes.
                price_subtotal = 0.0
                uom_qty_to_consider = line.qty_delivered if line.product_id.invoice_policy == 'delivery' else line.product_uom_qty
                price_reduce = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                price_subtotal = price_reduce * uom_qty_to_consider
                if len(line.tax_id.filtered(lambda tax: tax.price_include)) > 0:
                    # As included taxes are not excluded from the computed subtotal, `compute_all()` method
                    # has to be called to retrieve the subtotal without them.
                    # `price_reduce_taxexcl` cannot be used as it is computed from `price_subtotal` field. (see upper Note)
                    price_subtotal = line.tax_id.compute_all(
                        price_reduce,
                        currency=line.currency_id,
                        quantity=uom_qty_to_consider,
                        product=line.product_id,
                        partner=line.order_id.partner_shipping_id)['total_excluded']
                inv_lines = line._get_invoice_lines()
                if any(inv_lines.mapped(lambda l: l.discount != line.discount)):
                    # In case of re-invoicing with different discount we try to calculate manually the
                    # remaining amount to invoice
                    amount = 0
                    for l in inv_lines:
                        if len(l.tax_ids.filtered(lambda tax: tax.price_include)) > 0:
                            amount += l.tax_ids.compute_all(l.currency_id._convert(l.price_unit, line.currency_id, line.company_id, l.date or fields.Date.today(), round=False) * l.quantity)['total_excluded']
                        else:
                            amount += l.currency_id._convert(l.price_unit, line.currency_id, line.company_id, l.date or fields.Date.today(), round=False) * l.quantity

                    amount_to_invoice = max(price_subtotal - amount, 0)
                else:
                    amount_to_invoice = price_subtotal - line.untaxed_amount_invoiced

            line.untaxed_amount_to_invoice = amount_to_invoice


    def _prepare_invoice_line(self, **optional_values):
        """Prepare the values to create the new invoice line for a sales order line.

        :param optional_values: any parameter that should be added to the returned invoice line
        :rtype: dict
        """
        self.ensure_one()
        res = {
            'display_type': self.display_type or 'product',
            'sequence': self.sequence,
            'name': self.name,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom.id,
            'product_uos': self.product_uos.id,
            'product_uos_qty': self.product_uos_qty,
            'product_uos_price': self.product_uos_price,
            'quantity': self.qty_to_invoice,
            'discount': self.discount,
            'price_unit': self.price_unit,
            'tax_ids': [Command.set(self.tax_id.ids)],
            'sale_line_ids': [Command.link(self.id)],
            'is_downpayment': self.is_downpayment,
        }
        analytic_account_id = self.order_id.analytic_account_id.id
        if self.analytic_distribution and not self.display_type:
            res['analytic_distribution'] = self.analytic_distribution
        if analytic_account_id and not self.display_type:
            if 'analytic_distribution' in res:
                res['analytic_distribution'][analytic_account_id] = res['analytic_distribution'].get(analytic_account_id, 0) + 100
            else:
                res['analytic_distribution'] = {analytic_account_id: 100}
        if optional_values:
            res.update(optional_values)
        if self.display_type:
            res['account_id'] = False
        return res