# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.fields import Command
from collections import defaultdict
from odoo.exceptions import UserError, ValidationError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    default_code = fields.Char('Code', related="product_id.default_code", store=True, index=True)
    weight = fields.Float('weight', compute="compute_uos", store=True, digits="Stock Weight",
                          compute_sudo=True)

    product_uos = fields.Many2one('uom.uom', string="Unit", related="product_id.uos_id", readonly=True)
    product_uos_name = fields.Char(string="Unit", related="product_id.uos_id.name", readonly=True)
    scheduled_date = fields.Datetime(compute='_compute_qty_at_date', store=True)

    product_uos_qty = fields.Float('Qty', compute="compute_uos", store=True, compute_sudo=True)
    product_uos_price = fields.Float('Price', compute="compute_uos", store=True, compute_sudo=True)
    product_uom_readonly = fields.Boolean("UOM readonly", default=True)
    cadence = fields.Html(string="Cadencier", compute="compute_cadence", readonly=True, compute_sudo=True)
    display_qty_widget = fields.Boolean("display widget", store=True, compute='_compute_display_qty_widget')
    free_qty_at_date = fields.Float('Stock', compute='_compute_free_qty_at_date')
    logistic_discount = fields.Float('logistical discount')

    @api.depends('product_id', 'product_uom_qty', 'product_uom', 'order_id.commitment_date')
    def _compute_free_qty_at_date(self):
        """ Compute the quantity at date and remove qty needed by other order after this date
        It is not exactly the reality, it is a simple secure way to reserved enough qty
        more precision need a lot of compute and are slowing
        """
        for line in self:
            if line.product_id.type == 'product' and line.order_id.state in ['draft', 'send']:
                futur_lines = self.search([
                    ('scheduled_date', '>=', line.scheduled_date),
                    ('order_id', '!=', line.order_id.id),
                    ('state', 'in', ['sale']),
                    ('product_id', '=', line.product_id.id),
                    ])
                futur_outgoing_qty = sum(futur_lines.mapped('product_uom_qty'))
                free_qty_at_date = line.virtual_available_at_date - futur_outgoing_qty
                if free_qty_at_date < 0.0:
                    free_qty_at_date = 0.0
                line.free_qty_at_date = free_qty_at_date
            else:
                line.free_qty_at_date = line.product_uom_qty

    @api.depends('state')
    def _compute_product_uom_readonly(self):
        for line in self:
            # line.ids checks whether it's a new record not yet saved
            line.product_uom_readonly = line.ids and line.state in ['sale', 'done', 'cancel']

    @api.depends('product_id', 'state')
    def _compute_display_qty_widget(self):
        """ Always display product in stock with kit and bom"""
        for line in self:
            if line.state != 'draft':
                line.display_qty_widget = False
            elif line.product_id.bom_ids:
                line.display_qty_widget = True
            elif line.product_id.type == "product":
                line.display_qty_widget = True
            else:
                line.display_qty_widget = False

    @api.depends('product_type', 'product_uom_qty', 'qty_delivered', 'state', 'move_ids', 'product_uom')
    def _compute_qty_to_deliver(self):
        """Compute the visibility of the inventory widget."""
        for line in self:
            line.qty_to_deliver = line.product_uom_qty - line.qty_delivered

    @api.depends('product_id', 'order_id.partner_id', 'order_id.date_delivered')
    def compute_cadence(self):
        """ get the sale frequency of the product"""

        for line in self:
            date_start = line.order_id.date_delivered or datetime.now()
            date_start = date_start - timedelta(days=date_start.weekday())  # monday
            date_from = datetime.now() - timedelta(weeks=13)
            condition = [
                ('product_id', '=', line.product_id.id),
                ('move_id.partner_id', 'child_of', line.order_id.partner_id.id),
                ('move_id.invoice_date', '<', date_start),
                ('move_id.invoice_date', '>=', date_from),
                ('move_id.state', '!=', 'cancel'),
                ('move_id.move_type', '=', 'out_invoice'),
            ]
            invoice_lines = self.env['account.move.line'].search(condition)
            product = line.product_id

            qty_by_week = {}
            # Loop through the past 13 weeks
            if product:
                pack = product.base_unit_count if product.base_unit_count> 0.0 else 1
                for week in range(0, 12):
                    date_to = date_start - timedelta(weeks=week - 1)
                    date_from = date_start - timedelta(weeks=week)
                    # Get the quantity sold for the product for the current week
                    qty = sum(invoice_lines.filtered(lambda l: l.product_id.id == product.id and date_from.date() <= l.move_id.invoice_date <= date_to.date()).mapped(
                        'uom_qty'))
                    # If the quantity is not zero, add it to the quantity by week dictionary
                    if qty != 0:
                        qty_by_week['{}'.format(week)] = qty / pack

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
        """ The customer lead is more complexe in this project, It depends on location of customer: 1, 2 or 3 days """
        self.customer_lead = 0.0

    def _get_outgoing_incoming_moves(self):
        """ """
        outgoing_moves = self.env['stock.move']
        incoming_moves = self.env['stock.move']
        # TODO: import the weight, import the kit

        moves = self.move_ids.filtered(lambda r: r.state != 'cancel' and not r.scrapped and
                    (self.product_id == r.product_id or self.product_id == r.bom_line_id.bom_id.product_id))
        if self._context.get('accrual_entry_date'):
            moves = moves.filtered(lambda r: fields.Date.context_today(r, r.date) <= self._context['accrual_entry_date'])

        for move in moves:
            if move.location_dest_id.usage == "customer":
                if not move.origin_returned_move_id or (move.origin_returned_move_id and move.to_refund):
                    outgoing_moves |= move
            elif move.location_dest_id.usage != "customer" and move.to_refund:
                incoming_moves |= move

        return outgoing_moves, incoming_moves

    def create_mo(self):
        """ Create MO for needed product to manufacture """
        # Normal BOM forecast
        normal_mo = self.product_id.action_normal_mrp()

        def data_production(order, product, product_uom_qty):
            """ Save data production to do """
            lot = self.env['stock.lot'].create_production_lot(product)
            production_vals = {
                'product_id': product.id,
                'origin': order.name,
                'product_qty': product_uom_qty,
                'bom_id': product.bom_ids[0].id,
                'lot_producing_id': lot.id,
                'procurement_group_id': order.procurement_group_id.id,
                'date_planned_start': order.commitment_date,
            }
            return production_vals

        # Make to order, order_id.procurement_group_id, move.group_id
        group_prod = {}
        for line in self:
            product = line.product_id
            bom = product.bom_ids and product.bom_ids[0] or product.bom_ids

            if bom and bom.type == 'kit':
                # liste the product in BOM
                for bom_line in bom.bom_line_ids:
                    sub_product = bom_line.product_id
                    if sub_product.bom_ids and sub_product.to_personnalize:
                        sub_bom = sub_product.bom_ids[0]
                        if sub_bom.type == 'normal':
                            if sub_product not in list(group_prod.keys()):
                                group_prod[sub_product] = data_production(
                                    line.order_id, sub_product, line.product_uom_qty * bom_line.product_qty)
                            else:
                                group_prod[sub_product]['product_qty'] += line.product_uom_qty * bom_line.product_qty
                        else:
                            raise ValidationError(_("This product is not correctly configured."
                                                    "Only one kit BOM per line.\n") + line.product_id.name)

            elif bom and product.to_personnalize and product not in list(group_prod.keys()):
                group_prod[product] = data_production(line.order_id, product, line.product_uom_qty)
            elif bom and product.to_personnalize and product in list(group_prod.keys()):
                group_prod[product]['product_qty'] += line.product_uom_qty
            else:
                pass

        for mo_vals in list(group_prod.values()):
                new_mo = self.env['mrp.production'].create(mo_vals)
                new_mo.action_confirm()
                new_mo.move_raw_ids.put_quantity_done()

    @api.depends('move_ids.state', 'move_ids.scrapped', 'move_ids.product_uom_qty', 'move_ids.product_uom', 'order_id.delivery_status')
    def _compute_qty_delivered(self):
        super(SaleOrderLine, self)._compute_qty_delivered()

        for line in self:
            qty = 0.0
            if line.qty_delivered_method == 'stock_move':
                outgoing_moves, incoming_moves = line._get_outgoing_incoming_moves()
                for move in outgoing_moves:
                    if move.state != 'done':
                        continue
                    if move.bom_line_id.bom_id.type == 'phantom':
                        qty += move.product_uom_qty / move.bom_line_id.product_qty
                    else:
                        qty += move.product_uom_qty
                for move in incoming_moves:
                    if move.state != 'done':
                        continue
                    if move.bom_line_id.bom_id.type == 'phantom':
                        qty -= move.product_uom_qty / move.bom_line_id.product_qty
                    else:
                        qty -= move.product_uom_qty

            if line.product_id.type == 'service' and line.order_id.delivery_status != 'pending':
                qty = line.product_uom_qty

            line.qty_delivered = qty

    @api.depends('invoice_lines.move_id.state', 'invoice_lines.quantity')
    def _compute_qty_invoiced(self):
        """
        Compute the quantity invoiced. If case of a refund, the quantity invoiced is decreased. Note
        that this is the case only if the refund is generated from the SO and that is intentional: if
        a refund made would automatically decrease the invoiced quantity, then there is a risk of reinvoicing
        it automatically, which may not be wanted at all. That's why the refund has to be created from the SO
        """
        for line in self:
            qty_invoiced = 0.0
            for invoice_line in line._get_invoice_lines():
                if invoice_line.move_id.state != 'cancel' or invoice_line.move_id.payment_state == 'invoicing_legacy':
                    if invoice_line.move_id.move_type == 'out_invoice':
                        qty_invoiced += invoice_line.uom_qty
                    elif invoice_line.move_id.move_type == 'out_refund':
                        qty_invoiced -= invoice_line.uom_qty
            line.qty_invoiced = qty_invoiced

    @api.depends('product_id', 'product_uom_qty', 'price_unit', 'state')
    def compute_uos(self):
        """ compute the value of uos"""
        uom_weight = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()

        for line in self:
            if line.state in ['cancel', 'done']:
                continue

            if not line.product_id:
                line.weight = 0.0
                line.product_uos_qty = 0.0
                line.product_uos_price = 0.0
            else:
                #line.product_uos = line.product_id.uos_id
                line.product_uos_price = line.price_unit

                if line.product_id.type == 'service' or line.is_delivery or line.display_type or line.is_downpayment:
                    line.weight = 0.0
                    line.product_uos_qty = line.product_uom_qty
                else:
                    line.weight = line.product_id.weight * line.product_uom_qty
                    if line.product_id.uos_id == uom_weight:
                        line.product_uos_qty = line.weight
                    else:
                        line.product_uos_qty = line.product_uom_qty * (line.product_id.base_unit_count or 1.0)

    @api.depends(
        'product_id', 'customer_lead', 'product_uom_qty', 'product_uom', 'order_id.commitment_date',
        'move_ids', 'move_ids.forecast_expected_date', 'move_ids.forecast_availability')
    def _compute_qty_at_date(self):
        """ Compute the quantity forecasted of product at delivery date. There are
        two cases:
         1. The quotation has a commitment_date, we take it as delivery date
         2. The quotation hasn't commitment_date, we compute the estimated delivery
            date based on lead time"""

        treated = self.browse()
        # If the state is already in sale the picking is created and a simple forecasted quantity isn't enough
        # Then used the forecasted data of the related stock.move
        for line in self.filtered(lambda l: l.state == 'sale'):
            if not line.display_qty_widget:
                continue
            moves = line.move_ids.filtered(lambda m: m.product_id == line.product_id)
            line.forecast_expected_date = max(moves.filtered("forecast_expected_date").mapped("forecast_expected_date"), default=False)
            line.qty_available_today = 0
            line.free_qty_today = 0
            for move in moves:
                line.qty_available_today += move.product_uom._compute_quantity(move.reserved_availability, line.product_uom)
                line.free_qty_today += move.product_id.uom_id._compute_quantity(move.forecast_availability, line.product_uom)
            line.scheduled_date = line.order_id.commitment_date or line.order_id.date_order
            line.virtual_available_at_date = False
            treated |= line

        qty_processed_per_product = defaultdict(lambda: 0)
        grouped_lines = defaultdict(lambda: self.env['sale.order.line'])
        # We first loop over the SO lines to group them by warehouse and schedule
        # date in order to batch the read of the quantities computed field.
        for line in self.filtered(lambda l: l.state in ('draft', 'sent')):
            if not (line.product_id and line.display_qty_widget):
                continue
            grouped_lines[(line.warehouse_id.id, line.order_id.commitment_date or line._expected_date())] |= line

        for (warehouse, scheduled_date), lines in grouped_lines.items():
            product_qties = lines.mapped('product_id').with_context(to_date=scheduled_date, warehouse=warehouse).read([
                'qty_available',
                'free_qty',
                'virtual_available',
            ])
            qties_per_product = {
                product['id']: (product['qty_available'], product['free_qty'], product['virtual_available'])
                for product in product_qties
            }
            for line in lines:
                line.scheduled_date = scheduled_date
                qty_available_today, free_qty_today, virtual_available_at_date = qties_per_product[line.product_id.id]
                line.qty_available_today = qty_available_today - qty_processed_per_product[line.product_id.id]
                line.free_qty_today = free_qty_today - qty_processed_per_product[line.product_id.id]
                line.virtual_available_at_date = virtual_available_at_date - qty_processed_per_product[line.product_id.id]
                line.forecast_expected_date = False
                product_qty = line.product_uom_qty
                if line.product_uom and line.product_id.uom_id and line.product_uom != line.product_id.uom_id:
                    line.qty_available_today = line.product_id.uom_id._compute_quantity(line.qty_available_today, line.product_uom)
                    line.free_qty_today = line.product_id.uom_id._compute_quantity(line.free_qty_today, line.product_uom)
                    line.virtual_available_at_date = line.product_id.uom_id._compute_quantity(line.virtual_available_at_date, line.product_uom)
                    product_qty = line.product_uom._compute_quantity(product_qty, line.product_id.uom_id)
                qty_processed_per_product[line.product_id.id] += product_qty
            treated |= lines
        remaining = (self - treated)
        remaining.virtual_available_at_date = False
        remaining.scheduled_date = False
        remaining.forecast_expected_date = False
        remaining.free_qty_today = False
        remaining.qty_available_today = False

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

    @api.depends('state', 'price_reduce', 'product_id', 'untaxed_amount_invoiced', 'qty_delivered', 'product_uom_qty')
    def _compute_untaxed_amount_to_invoice(self):
        """ Total of remaining amount to invoice on the sale order line (taxes excl.) as
                total_sol - amount already invoiced
            where Total_sol depends on the invoice policy of the product.

            Note: Draft invoice are ignored on purpose, the 'to invoice' amount should
            come only from the SO lines.
        """
        uom_weight = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()

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

                if line.product_id.uos_id == uom_weight:
                    uos_qty_to_consider = uom_qty_to_consider * line.product_id.weight
                else:
                    uos_qty_to_consider = uom_qty_to_consider * (line.product_id.base_unit_count or 1.0)

                price_subtotal = price_reduce * uos_qty_to_consider

                if len(line.tax_id.filtered(lambda tax: tax.price_include)) > 0:
                    # As included taxes are not excluded from the computed subtotal, `compute_all()` method
                    # has to be called to retrieve the subtotal without them.
                    # `price_reduce_taxexcl` cannot be used as it is computed from `price_subtotal` field. (see upper Note)
                    price_subtotal = line.tax_id.compute_all(
                        price_reduce,
                        currency=line.currency_id,
                        quantity=uos_qty_to_consider,
                        product=line.product_id,
                        partner=line.order_id.partner_shipping_id)['total_excluded']
                inv_lines = line._get_invoice_lines()
                if any(inv_lines.mapped(lambda l: l.discount != line.discount)):
                    # In case of re-invoicing with different discount we try to calculate manually the
                    # remaining amount to invoice
                    amount = 0
                    for l in inv_lines:
                        if line.product_id.uos_id == uom_weight:
                            uos_qty = l.weight
                        else:
                            uos_qty = l.quantity * (l.product_id.base_unit_count or 1.0)

                        if len(l.tax_ids.filtered(lambda tax: tax.price_include)) > 0:
                            amount += l.tax_ids.compute_all(l.currency_id._convert(l.price_unit, line.currency_id, line.company_id, l.date or fields.Date.today(), round=False) * uos_qty)['total_excluded']
                        else:
                            amount += l.currency_id._convert(l.price_unit, line.currency_id, line.company_id, l.date or fields.Date.today(), round=False) * uos_qty

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
        uom_weight = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()

        res = {
            'display_type': self.display_type or 'product',
            'sequence': self.sequence,
            'name': self.name,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uos.id,
            'quantity': self.qty_to_invoice,
            'uom_qty': self.qty_to_invoice,
            'discount': self.discount,
            'price_unit': self.price_unit,
            'tax_ids': [Command.set(self.tax_id.ids)],
            'sale_line_ids': [Command.link(self.id)],
            'is_downpayment': self.is_downpayment,
        }
        if self.product_uos == uom_weight:
            res['quantity'] = self.qty_to_invoice * self.product_id.weight
        if self.product_id.base_unit_count > 1:
            res['quantity'] = self.qty_to_invoice * self.product_id.base_unit_count

        analytic_account_id = self.order_id.analytic_account_id.id
        if self.analytic_distribution and not self.display_type:
            res['analytic_distribution'] = self.analytic_distribution
        if analytic_account_id and not self.display_type:
            analytic_account_id = str(analytic_account_id)
            if 'analytic_distribution' in res:
                res['analytic_distribution'][analytic_account_id] = res['analytic_distribution'].get(analytic_account_id, 0) + 100
            else:
                res['analytic_distribution'] = {analytic_account_id: 100}
        if optional_values:
            res.update(optional_values)
        if self.display_type:
            res['account_id'] = False
        return res
