

from odoo import _, api, fields, models
from odoo.tools import float_compare, float_is_zero
from collections import defaultdict
#from odoo.tools.float_utils import float_round, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    """ Add the possibility to invoice by weight price.
    Get information in stock.move
    weight, quantity, lot
    """

    _inherit = "account.move.line"

    # To check, doublon
    price_net = fields.Float(string='Prix net', compute='_compute_price_net')
    product_uos = fields.Many2one('uom.uom', string="Udv")
    histo_cost_price = fields.Float()

    # import_V7
    number_of_pack = fields.Float(string='Nb pack')
    number_of_unit = fields.Float(string='Nb unit')
    prodlot_id = fields.Many2one('stock.lot', string='Production lot')
    product_packaging = fields.Many2one(
        'product.packaging',
        string='Packaging',
        )

    type = fields.Char()
    cadeau = fields.Float(string='Remise Total')
    cost_price = fields.Float(string='Prix de revient')
    margin = fields.Float(string='Marge total')
    margin_percent = fields.Float(string='Marge %')

    # purchase add
    initial_price = fields.Float(string='Price')
    discount1 = fields.Float(string='R1 %')
    discount2 = fields.Float(string='R2 %')
    promotion = fields.Float(string='Promo %')

    # Validated V16

    default_code = fields.Char('Code', related='product_id.default_code', store=True)
    account_move_line_lot_ids = fields.One2many('account.move.line.lot', 'account_move_line_id',
                                                copy=True, string="Detailed lot")

    lot = fields.Char("lot")

    supplierinfo_id = fields.Many2one('product.supplierinfo',
                                      compute='get_supplierinfo_id',
                                      string="Supplier info", store=True)
    product_uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string='Unit',
        compute='get_product_uom_id', store=True, readonly=True,
        domain="[]",
        ondelete="restrict",
    )
    uom_qty = fields.Float(
        string="Qty",
        compute='get_uom_qty',
        inverse="put_uom_qty", readonly=False,
        store=True, precompute=False,
        )

    quantity = fields.Float(
        string='UDV qty',
        compute='get_quantity', store=True, readonly=True, precompute=False,
        digits='Product Unit of Measure',
        help="Invoiced quantity in kg or unit."
    )
    manual_weight = fields.Float("Manual Weight") # DELETE if not used
    weight = fields.Float(
        string="Weight",
        compute='get_weight',
        inverse="put_weight", readonly=False,
        store=True, precompute=False,
        digits='Stock Weight',
    )
    price_unit = fields.Float(
        string='Unit Price',
        compute=False, store=True, readonly=False, precompute=False,
        digits='Product Price',
    )
    invoice_filter_type_domain = fields.Char('invoice filter type', related="move_id.invoice_filter_type_domain")

    def _get_out_and_not_invoiced_qty(self, in_moves):
        self.ensure_one()
        if not in_moves:
            return 0
        aml_qty = self.uom_qty
        invoiced_qty = 0.0
        for line in self.purchase_line_id.invoice_lines - self:
            invoiced_qty += line.product_qty

        layers = in_moves.stock_valuation_layer_ids
        layers_qty = sum(layers.mapped('quantity'))
        out_qty = layers_qty - sum(layers.mapped('remaining_qty'))
        total_out_and_not_invoiced_qty = max(0, out_qty - invoiced_qty)
        out_and_not_invoiced_qty = min(aml_qty, total_out_and_not_invoiced_qty)
        return out_and_not_invoiced_qty

    @api.depends('product_id', 'move_id.move_type', 'move_id.partner_id', 'move_id.state')
    def get_supplierinfo_id(self):
        """ get supplier info to define price, unit and packing"""

        for line in self:
            if line.move_id.state in ['cancel', 'posted'] or line.move_id.piece_comptable:
                continue
            elif line.move_id.move_type not in ['in_invoice', 'in_refund']:
                line.supplierinfo_id = False

            elif line.supplierinfo_id and line.supplierinfo_id.product_id == line.product_id and \
                    line.supplierinfo_id.partner_id == line.move_id.partner_id:
                # OK, it's good, already doing
                pass
            elif line.product_id and line.move_id.partner_id:
                line.supplierinfo_id = line.product_id._select_seller(
                    partner_id=line.move_id.partner_id,
                    quantity=1)
            else:
                line.supplierinfo_id = False

    @api.depends('product_id', 'move_id.move_type', 'move_id.state')
    def get_product_uom_id(self):
        """ Return the unit to use to invoice (unit or Kg), unit can't be changing"""

        for line in self:
            if line.product_uos:
                line.product_uom_id = line.product_uos
            elif line.move_id.state in ['cancel', 'posted']:
                line.product_uom_id = line.product_uom_id
            elif line.product_id:
                if line.move_id.move_type in ['out_invoice', 'out_refund', 'out_receipt', 'entry']:
                    line.product_uom_id = line.product_id.uos_id or self.env.ref('uom.product_uom_unit')
                elif line.move_id.move_type in ['in_invoice', 'in_refund', 'in_receipt']:
                    if line.supplierinfo_id:
                        line.product_uom_id = line.supplierinfo_id.product_uos or line.product_id.uos_id or self.env.ref('uom.product_uom_unit')
                    else:
                        line.product_uom_id = line.product_id.uos_id or self.env.ref('uom.product_uom_unit')
                else:
                    line.product_uom_id = line.product_id.uos_id or self.env.ref('uom.product_uom_unit')
            else:
                line.product_uom_id = self.env.ref('uom.product_uom_unit')

    @api.constrains('product_uom_id')
    def _check_product_uom_category_id(self):
        """ Not used"""
        pass

    def update_stock_move(self):
        """ Update information based on picking"""
        for invoice_line in self:
            if invoice_line.move_id.state in ['cancel', 'posted'] or invoice_line.move_id.piece_comptable:
                continue
            stock_move_ids = self.env['stock.move']
            for sale_line in invoice_line.sale_line_ids:
                stock_move_ids |= sale_line.move_ids
            for purchase_line in invoice_line.purchase_line_id:
                stock_move_ids |= purchase_line.move_ids

            for stock_move in stock_move_ids:
                if stock_move.state in ['draft']:
                    stock_move_ids -= stock_move

            stock_move_line_ids = invoice_line.account_move_line_lot_ids.mapped('stock_move_line_id')
            to_delete = self.env['account.move.line.lot']

            for stock_move_line_lot in invoice_line.account_move_line_lot_ids:
                if stock_move_line_lot.state == "cancel":
                    to_delete |= stock_move_line_lot
                if stock_move_line_lot.state == "manual" and invoice_line.product_id.type != 'service':
                    to_delete |= stock_move_line_lot

            to_delete.unlink()

            for stock_move_line in stock_move_ids.move_line_ids:
                if stock_move_line.state == 'cancel':
                    continue
                vals = {
                    'stock_move_line_id': stock_move_line.id,
                    'lot_id': stock_move_line.lot_id.id,
                    'weight': stock_move_line.weight,
                }
                if invoice_line.product_id.base_unit_count > 1.0:
                    vals['uom_qty'] = stock_move_line.qty_done / invoice_line.product_id.base_unit_count
                else:
                    vals['uom_qty'] = stock_move_line.qty_done

                if stock_move_line not in stock_move_line_ids:
                    vals['account_move_line_id'] = invoice_line.id
                    invoice_line.account_move_line_lot_ids.create(vals)
                else:
                    invoice_line.account_move_line_lot_ids.filtered(
                        lambda a: a.stock_move_line_id == stock_move_line).write(vals)
        self.get_quantity()

    def put_uom_qty(self):
        """ Create account_move_line_lot_ids to save value"""
        for line in self:
            line_lot_vals = {'uom_qty': line.uom_qty}

            if not line.weight and line.product_id.weight:
                line_lot_vals['weight'] = line.product_id.weight * line.uom_qty

            if not line.account_move_line_lot_ids:
                line_lot_vals['account_move_line_id'] = line.id
                line_lot_vals['state'] = 'manual'
                line.account_move_line_lot_ids.create(line_lot_vals)
            elif len(line.account_move_line_lot_ids) == 1:
                line.account_move_line_lot_ids.update(line_lot_vals)
            else:
                raise ValidationError(_("this line has multiples production lot, uses the detailed view to update"))

    def put_weight(self):
        """ Create account_move_line_lot_ids to save value"""
        for line in self:
            line_lot_vals = {'weight': line.weight}

            if not line.account_move_line_lot_ids:
                line_lot_vals['account_move_line_id'] = line.id
                line_lot_vals['state'] = 'manual'
                line.account_move_line_lot_ids.create(line_lot_vals)
            elif len(line.account_move_line_lot_ids) == 1:
                line.account_move_line_lot_ids.update(line_lot_vals)
            else:
                raise ValidationError(_("this line has multiples production lot, uses the detailed view to update"))

    @api.depends('account_move_line_lot_ids.quantity')
    def get_quantity(self):
        """ get quantity"""
        uom_weight = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()

        for line in self:
            if line.account_move_line_lot_ids:
                if line.move_id.state in ['cancel', 'posted']:
                    continue
                quantity = 0.0
                for account_move_line_lot in line.account_move_line_lot_ids:
                    quantity += account_move_line_lot.quantity
                line.quantity = quantity

    @api.depends('account_move_line_lot_ids.uom_qty')
    def get_uom_qty(self):
        """ Get uom_qty"""
        for line in self:
            if line.move_id.state in ['cancel', 'posted']:
                continue

            if not line.product_id or not line.account_move_line_lot_ids:
                line.uom_qty = 1.0
            else:
                uom_qty = 0.0
                for stock_move_line_lot in line.account_move_line_lot_ids:
                    if stock_move_line_lot.state not in ['draft', 'cancel']:
                        uom_qty += stock_move_line_lot.uom_qty

                line.uom_qty = uom_qty

    @api.depends('account_move_line_lot_ids.weight')
    def get_weight(self):
        """ Get uom_qty"""
        for line in self:
            if line.move_id.state in ['cancel', 'posted']:
                continue

            if not line.product_id or not line.account_move_line_lot_ids:
                line.weight = 1.0
            else:
                weight = 0.0
                for stock_move_line_lot in line.account_move_line_lot_ids:
                    if stock_move_line_lot.state not in ['draft', 'cancel']:
                        weight += stock_move_line_lot.weight
                line.weight = weight

    def weight_exception(self):
        """ Exception product line with no weight"""
        _logger.warning('This line has no weight: %s' % self)
        pass

    def init_stock_move(self):
        """ Init stock_move to restart evaluation"""
        self.stock_move_ids = False

    @api.depends('price_unit', 'discount')
    def _compute_price_net(self):
        for line in self:
            line.price_net = line.price_unit - (line.price_unit * line.discount / 100.0)

    @api.onchange('supplierinfo_id')
    def onchange_supplierinfo(self):
        """ Load value"""
        self.ensure_one()
        res = {}
        if self.move_id.state in ['cancel', 'posted']:
            pass
        elif self.supplierinfo_id:
            res["discount1"] = self.supplierinfo_id.discount1
            res["discount2"] = self.supplierinfo_id.discount2
            res["initial_price"] = self.supplierinfo_id.base_price
            if self.supplierinfo_id.product_name:
                res["name"] = self.supplierinfo_id.product_name
            if self.supplierinfo_id.product_code:
                res["name"] = "[{}] {}".format(self.supplierinfo_id.product_code,
                                               self.supplierinfo_id.product_name or self.product_id.name)
            if self.supplierinfo_id.type == "add":
                res["price_unit"] = res["initial_price"] * \
                    (1.0 - ((res["discount1"] + res["discount2"]) / 100.0))
            else:
                res["price_unit"] = self.supplierinfo_id.base_price * \
                    (1.0 - (res["discount1"] / 100.0)) * (1.0 - (res["discount2"] / 100.0))
        else:
            res["discount1"] = 0.0
            res["discount2"] = 0.0
            res["initial_price"] = 0.0
            res["price_unit"] = 0.0

        self.update(res)

    def _generate_price_difference_vals(self, layers):
        """
        The method will determine which layers are impacted by the AML (`self`) and, in case of a price difference, it
        will then return the values of the new AMLs and SVLs
        """
        self.ensure_one()
        po_line = self.purchase_line_id
        product_uom = self.product_id.uos_id

        # `history` is a list of tuples: (time, aml, layer)
        # aml and layer will never be both defined
        # we use this to get an order between posted AML and layers
        history = [(layer.create_date, False, layer) for layer in layers]
        am_state_field = self.env['ir.model.fields'].search([('model', '=', 'account.move'), ('name', '=', 'state')], limit=1)
        for aml in po_line.invoice_lines:
            move = aml.move_id
            if move.state != 'posted':
                continue
            state_trackings = move.message_ids.tracking_value_ids.filtered(lambda t: t.field == am_state_field).sorted('id')
            time = state_trackings[-1:].create_date or move.create_date  # `or` in case it has been created in posted state
            history.append((time, aml, False))
        # Sort history based on the datetime. In case of equality, the prority is given to SVLs, then to IDs.
        # That way, we ensure a deterministic behaviour
        history.sort(key=lambda item: (item[0], bool(item[1]), (item[1] or item[2]).id))

        # the next dict is a matrix [layer L, invoice I] where each cell gives two info:
        # [initial qty of L invoiced by I, remaining invoiced qty]
        # the second info is usefull in case of a refund
        layers_and_invoices_qties = defaultdict(lambda: [0, 0])

        # the next dict will also provide two info:
        # [total qty to invoice, remaining qty to invoice]
        # we need the total qty to invoice, so we will be able to deduce the invoiced qty before `self`
        qty_to_invoice_per_layer = defaultdict(lambda: [0, 0])

        # Replay the whole history: we want to know what are the links between each layer and each invoice,
        # and then the links between `self` and the layers
        history.append((False, self, False))  # time was only usefull for the sorting
        for _time, aml, layer in history:
            if layer:
                total_layer_qty_to_invoice = abs(layer.quantity)
                initial_layer = layer.stock_move_id.origin_returned_move_id.stock_valuation_layer_ids
                if initial_layer:
                    # `layer` is a return. We will cancel the qty to invoice of the returned layer
                    # /!\ we will cancel the qty not yet invoiced only
                    initial_layer_remaining_qty = qty_to_invoice_per_layer[initial_layer][1]
                    common_qty = min(initial_layer_remaining_qty, total_layer_qty_to_invoice)
                    qty_to_invoice_per_layer[initial_layer][0] -= common_qty
                    qty_to_invoice_per_layer[initial_layer][1] -= common_qty
                    total_layer_qty_to_invoice = max(0, total_layer_qty_to_invoice - common_qty)
                if float_compare(total_layer_qty_to_invoice, 0, precision_rounding=product_uom.rounding) > 0:
                    qty_to_invoice_per_layer[layer] = [total_layer_qty_to_invoice, total_layer_qty_to_invoice]
            else:
                invoice = aml.move_id
                impacted_invoice = False
                aml_qty = aml.product_uom_id._compute_quantity(aml.quantity, product_uom)
                if aml.is_refund:
                    reversed_invoice = aml.move_id.reversed_entry_id
                    if reversed_invoice:
                        sign = -1
                        impacted_invoice = reversed_invoice
                        # it's a refund, therefore we can only consume the quantities invoiced by
                        # the initial invoice (`reversed_invoice`)
                        layers_to_consume = []
                        for layer in layers:
                            remaining_invoiced_qty = layers_and_invoices_qties[(layer, reversed_invoice)][1]
                            layers_to_consume.append((layer, remaining_invoiced_qty))
                    else:
                        # the refund has been generated because of a stock return, let's find and use it
                        sign = 1
                        layers_to_consume = []
                        for layer in qty_to_invoice_per_layer:
                            if layer.stock_move_id._is_out():
                                layers_to_consume.append((layer, qty_to_invoice_per_layer[layer][1]))
                else:
                    # classic case, we are billing a received quantity so let's use the incoming SVLs
                    sign = 1
                    layers_to_consume = []
                    for layer in qty_to_invoice_per_layer:
                        if layer.stock_move_id._is_in():
                            layers_to_consume.append((layer, qty_to_invoice_per_layer[layer][1]))
                while float_compare(aml_qty, 0, precision_rounding=product_uom.rounding) > 0 and layers_to_consume:
                    layer, total_layer_qty_to_invoice = layers_to_consume[0]
                    layers_to_consume = layers_to_consume[1:]
                    if float_is_zero(total_layer_qty_to_invoice, precision_rounding=product_uom.rounding):
                        continue
                    common_qty = min(aml_qty, total_layer_qty_to_invoice)
                    aml_qty -= common_qty
                    qty_to_invoice_per_layer[layer][1] -= sign * common_qty
                    layers_and_invoices_qties[(layer, invoice)] = [common_qty, common_qty]
                    layers_and_invoices_qties[(layer, impacted_invoice)][1] -= common_qty

        # Now we know what layers does `self` use, let's check if we have to create a pdiff SVL
        # (or cancel such an SVL in case of a refund)
        invoice = self.move_id
        svl_vals_list = []
        aml_vals_list = []
        for layer in layers:
            # use the link between `self` and `layer` (i.e. the qty of `layer` billed by `self`)
            invoicing_layer_qty = layers_and_invoices_qties[(layer, invoice)][1]
            if float_is_zero(invoicing_layer_qty, precision_rounding=product_uom.rounding):
                continue
            # We will only consider the total quantity to invoice of the layer because we don't
            # want to invoice a part of the layer that has not been invoiced and that has been
            # returned in the meantime
            total_layer_qty_to_invoice = qty_to_invoice_per_layer[layer][0]
            remaining_qty = layer.remaining_qty
            out_layer_qty = total_layer_qty_to_invoice - remaining_qty
            if self.is_refund:
                sign = -1
                reversed_invoice = invoice.reversed_entry_id
                if not reversed_invoice:
                    # this is a refund for a returned quantity, we don't have anything to do
                    continue
                initial_invoiced_qty = layers_and_invoices_qties[(layer, reversed_invoice)][0]
                initial_pdiff_svl = layer.stock_valuation_layer_ids.filtered(lambda svl: svl.account_move_line_id.move_id == reversed_invoice)
                if not initial_pdiff_svl or float_is_zero(initial_invoiced_qty, precision_rounding=product_uom.rounding):
                    continue
                # We have an already-out quantity: we must skip the part already invoiced. So, first,
                # let's compute the already invoiced quantity...
                previously_invoiced_qty = 0
                for item in history:
                    previous_aml = item[1]
                    if not previous_aml or previous_aml.is_refund:
                        continue
                    previous_invoice = previous_aml.move_id
                    if previous_invoice == reversed_invoice:
                        break
                    previously_invoiced_qty += layers_and_invoices_qties[(layer, previous_invoice,)][1]
                # ... Second, skip it:
                out_qty_to_invoice = max(0, out_layer_qty - previously_invoiced_qty)
                qty_to_correct = max(0, invoicing_layer_qty - out_qty_to_invoice)
                if out_qty_to_invoice:
                    # In case the out qty is different from the one posted by the initial bill, we should compensate
                    # this quantity with debit/credit between stock_in and expense, but we are reversing an initial
                    # invoice and don't want to do more than the original one
                    out_qty_to_invoice = 0
                aml = initial_pdiff_svl.account_move_line_id
                parent_layer = initial_pdiff_svl.stock_valuation_layer_id
                layer_price_unit = parent_layer.value / parent_layer.quantity
            else:
                sign = 1
                # get the invoiced qty of the layer without considering `self`
                invoiced_layer_qty = total_layer_qty_to_invoice - qty_to_invoice_per_layer[layer][1] - invoicing_layer_qty
                remaining_out_qty_to_invoice = max(0, out_layer_qty - invoiced_layer_qty)
                out_qty_to_invoice = min(remaining_out_qty_to_invoice, invoicing_layer_qty)
                qty_to_correct = invoicing_layer_qty - out_qty_to_invoice
                layer_price_unit = layer.value / layer.quantity
                aml = self

            aml_gross_price_unit = aml._get_gross_unit_price()
            aml_price_unit = aml.currency_id._convert(aml_gross_price_unit, aml.company_id.currency_id, aml.company_id, aml.date, round=False)
            aml_price_unit = aml.product_uom_id._compute_price(aml_price_unit, product_uom)

            unit_valuation_difference = aml_price_unit - layer_price_unit

            # Generate the AML values for the already out quantities
            unit_valuation_difference_curr = self.company_id.currency_id._convert(unit_valuation_difference, self.currency_id, self.company_id, self.date, round=False)
            unit_valuation_difference_curr = product_uom._compute_price(unit_valuation_difference_curr, self.product_uom_id)
            out_qty_to_invoice = product_uom._compute_quantity(out_qty_to_invoice, self.product_uom_id)
            if not float_is_zero(unit_valuation_difference_curr * out_qty_to_invoice, precision_rounding=self.currency_id.rounding):
                aml_vals_list += self._prepare_pdiff_aml_vals(out_qty_to_invoice, unit_valuation_difference_curr)

            # Generate the SVL values for the on hand quantities (and impact the parent layer)
            po_pu_curr = po_line.currency_id._convert(po_line.price_unit, self.currency_id, self.company_id, self.date, round=False)
            price_difference_curr = po_pu_curr - aml_gross_price_unit
            if not float_is_zero(unit_valuation_difference * qty_to_correct, precision_rounding=self.company_id.currency_id.rounding):
                svl_vals = self._prepare_pdiff_svl_vals(layer, sign * qty_to_correct, unit_valuation_difference, price_difference_curr)
                layer.remaining_value += svl_vals['value']
                svl_vals_list.append(svl_vals)
        return svl_vals_list, aml_vals_list

    def action_show_details(self):
        """ Returns an action that will open a form view (in a popup) allowing to work on all the
        move lines of a particular account move line. This form view is used choose lot.
        """
        self.ensure_one()
        view = self.env.ref('customize_account.account_move_line_custom_form_view')
        action = {
            'name': _('Detailed Operations'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move.line',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': self.id,
            'context': dict(self.env.context),
        }
        if self.move_id.state == "posted":
            action['flags'] = {'mode': 'readonly'}
        return action