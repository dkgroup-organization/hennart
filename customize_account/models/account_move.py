from odoo import fields, models, api, Command
import logging
import datetime
from dateutil.relativedelta import relativedelta
logger = logging.getLogger('wms_scanner')

from odoo.exceptions import UserError, ValidationError
_logger = logging.getLogger(__name__)

PAYMENT_STATE_SELECTION = [
        ('not_paid', 'Not Paid'),
        ('in_payment', 'In Payment'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('reversed', 'Reversed'),
        ('invoicing_legacy', 'Invoicing App Legacy'),
]


class AccountMove(models.Model):
    _inherit = "account.move"

    def _default_incoterm_date(self):
        if self._context.get('default_picking_id') and self._context.get('default_picking_id').date_expected:
            timedate_date_port = fields.Datetime.from_string(self._context.get('default_picking_id').date_expected)
            timedate_date_port += relativedelta(days=1)
            return timedate_date_port.date()
        return False

    partner_shipping_id = fields.Many2one(
        comodel_name='res.partner',
        string='Delivery Address',
        compute='_compute_partner_shipping_id', store=True, readonly=False, precompute=True, index=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="Delivery address for current invoice.",
    )

    picking_id = fields.Char(string="Bon de livraison")
    incoterm_port = fields.Char(string="Port of entry")
    incoterm_date = fields.Date(string="Date of arrival in UK", default=_default_incoterm_date, copy=False)
    payment_method_id = fields.Many2one(related="partner_id.payment_method_id")

    total_ht = fields.Float(string='Total HT', copy=False)
    total_tva = fields.Float(string='Total TVA', copy=False)
    total_ttc = fields.Float(string='Total TTC', copy=False)
    total_logistical_discount = fields.Float(string='Total logistical discount', compute='compute_total_logistical_discount', store=True)
    piece_comptable = fields.Char(string='ID piece comptable', copy=False)
    imported_state = fields.Char('Imported status')

    account_id = fields.Many2one(
        'account.account',
        string='Account',
    )

    picking_ids = fields.Many2many('stock.picking', string='Pickings')

    payment_state = fields.Selection(
        selection=PAYMENT_STATE_SELECTION,
        string="Payment Status",
        compute=False, store=True, readonly=False,
        copy=False,
        default='not_paid',
        tracking=True,
    )

    suitable_journal_ids = fields.Many2many(
        'account.journal',
        compute='_compute_suitable_journal2_ids',
    )

    partner_shipping_id = fields.Many2one(
        comodel_name='res.partner',
        string='Delivery Address',
        compute='_compute_partner_shipping_id', store=True, readonly=False, precompute=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        index=True,
        help="Delivery address for current invoice.",
    )
    user2_id = fields.Many2one('res.users', string='Manager', compute='compute_user2', readonly="False", store=True)

    @api.depends('line_ids.price_subtotal')
    def compute_total_logistical_discount(self):
        """ save total of logistical discount """
        logistical_discount_product = self.env['product.pricelist.discount'].get_discount_product()

        for invoice in self:
            total_logistical_discount = 0.0
            for line in invoice.line_ids:
                if line.product_id in logistical_discount_product:
                    total_logistical_discount += line.price_subtotal
            invoice.total_logistical_discount = total_logistical_discount

    def compute_user2(self):
        """ Compute the sale manager """
        for move in self:
            if move.partner_shipping_id.user2_id:
                user2_id = move.partner_shipping_id.user2_id
            else:
                user2_id = move.partner_id.user2_id or move.partner_id.parent_id.user2_id
            move.user2_id = user2_id

    def get_max_subtotal_tax(self):
        """ return subtotal and tax"""
        discount_product_ids = self.env['product.pricelist.discount'].search(
            [('product_discount_id', '!=', False)]).mapped('product_discount_id')

        subtotal_by_tax = {}

        for line in self.invoice_line_ids:
            if line.product_id in discount_product_ids or line.product_id.type == "service":
                continue

            tax = line.tax_ids
            subtotal = line.price_subtotal
            if tax in subtotal_by_tax:
                subtotal_by_tax[tax] += subtotal
            else:
                subtotal_by_tax[tax] = subtotal

        if subtotal_by_tax:
            max_subtotal_tax = max(subtotal_by_tax, key=subtotal_by_tax.get)
            return max_subtotal_tax, subtotal_by_tax[max_subtotal_tax]
        else:
            return False, 0.0

    def update_discount_stock(self):
        """ check the sale line logistical discount """
        line_discount_data = []
        for invoice in self:
            for invoice_line in invoice.invoice_line_ids:
                invoice_line.update_stock_move()
                for sale_line in invoice_line.sale_line_ids:
                    if sale_line.logistic_discount > 0.0:
                        line_discount_data.append(
                            {'invoice_line': invoice_line, 'logistic_discount': sale_line.logistic_discount})

        for line_discount in line_discount_data:
            invoice = line_discount['invoice_line'].move_id
            tax, total_HT = invoice.get_max_subtotal_tax()
            line_discount['invoice_line'].tax_ids = tax
            line_discount['invoice_line'].price_unit = - total_HT * line_discount['logistic_discount'] / 100.0
            line_discount['invoice_line'].uom_qty = 1.0

        for invoice in self:
            if invoice.state != 'draft':
                continue
            tax_repartition_line = {}
            sign = invoice.direction_sign

            for line in invoice.line_ids:
                line._compute_all_tax()
                line._compute_totals()

                if line.display_type == 'tax':
                    line.compute_all_tax = {}
                    line.compute_all_tax_dirty = False
                    continue
                if line.display_type == 'product' and line.move_id.is_invoice(True):
                    amount_currency = sign * line.price_unit * (1 - line.discount / 100)
                    handle_price_include = True
                    quantity = line.quantity
                else:
                    amount_currency = line.amount_currency
                    handle_price_include = False
                    quantity = 1
                compute_all_currency = line.tax_ids.compute_all(
                    amount_currency,
                    currency=line.currency_id,
                    quantity=quantity,
                    product=line.product_id,
                    partner=line.move_id.partner_id or line.partner_id,
                    is_refund=line.is_refund,
                    handle_price_include=handle_price_include,
                    include_caba_tags=line.move_id.always_tax_exigible,
                    fixed_multiplicator=sign,
                )

                for taxe in compute_all_currency.get('taxes'):
                    tax_repartition_line_id = taxe.get('tax_repartition_line_id')
                    amount = taxe.get('amount')
                    if tax_repartition_line_id not in list(tax_repartition_line.keys()):
                        tax_repartition_line[tax_repartition_line_id] = amount
                    else:
                        tax_repartition_line[tax_repartition_line_id] += amount

                if line.tax_repartition_line_id.id in list(tax_repartition_line.keys()):


                    if sign * tax_repartition_line[line.tax_repartition_line_id.id] >= 0.0:
                        if invoice.move_type in ['in_invoice', 'in_refund', 'in_receipt']:
                            line.debit = sign * tax_repartition_line[line.tax_repartition_line_id.id]
                        else:
                            line.credit = sign * tax_repartition_line[line.tax_repartition_line_id.id]
                    else:
                        if invoice.move_type in ['in_invoice', 'in_refund', 'in_receipt']:
                            line.credit = -1 * sign * tax_repartition_line[line.tax_repartition_line_id.id]
                        else:
                            line.debit = -1 * sign * tax_repartition_line[line.tax_repartition_line_id.id]

            invoice._compute_tax_totals()
            invoice._compute_amount()

    def update_origin(self):
        """ check order and picking origin"""
        for invoice in self:
            origin = ''
            stock_move_ids = self.env['stock.move']
            if invoice.piece_comptable:
                continue

            if invoice.ref and invoice.ref not in origin:
                origin = invoice.ref

            for invoice_line in invoice.invoice_line_ids:
                for sale_line in invoice_line.sale_line_ids:
                    stock_move_ids |= sale_line.move_ids

                for purchase_line in invoice_line.purchase_line_id:
                    stock_move_ids |= purchase_line.move_ids

                for picking in stock_move_ids.mapped('picking_id'):
                    if picking.partner_origin and picking.partner_origin not in origin:
                        origin += ' ' + picking.partner_origin

                for picking in stock_move_ids.mapped('picking_id'):
                    if picking.name not in origin:
                        origin += ' ' + picking.name

            invoice.invoice_origin = origin

    @api.depends('company_id', 'invoice_filter_type_domain', 'src_dest_country_id')
    def _compute_suitable_journal2_ids(self):
        for m in self:
            journal_type = m.invoice_filter_type_domain or 'general'
            company_id = m.company_id.id or self.env.company.id
            domain = [('company_id', '=', company_id), ('type', '=', journal_type)]
            if journal_type == 'sale':
                if m.src_dest_country_id:
                    domain += [('country_ids', 'in', m.src_dest_country_id.ids)]
                else:
                    domain += [('country_ids', '=', False)]
            m.suitable_journal_ids = self.env['account.journal'].search(domain)

    @api.onchange('partner_id')
    def onchange_partner2_id(self):
        """ select journal by country"""
        self.ensure_one()
        res = {}
        if self.suitable_journal_ids:
            if self.journal_id not in self.suitable_journal_ids:
                res['journal_id'] = self.suitable_journal_ids[0]
        else:
            res['journal_id'] = False

        self.compute_user2()
        self.update(res)

    def _must_check_constrains_date_sequence(self):
        # OVERRIDES sequence.mixin
        if self.env.context.get('force_sequence'):
            return False
        else:
            return not self.quick_edit_mode

    def action_valide_imported(self):
        """ Valid a imported move, there is some correction todo"""

        uom_weight = self.env['product.template'].sudo()._get_weight_uom_id_from_ir_config_parameter()
        remote_server = self.env['synchro.server'].search([])
        sync_obj = remote_server[0].obj_ids.search([('model_name', '=', 'account.invoice.line')])
        #self.env['synchro.obj'].search([('model_name', '=', 'account.invoice')]).unlink_local_void()
        invoice_name = self.env['account.move'].get_duplicate_invoices()

        for move in self:
            if move.name in invoice_name:
                move.imported_state = 'doublon'
                continue
            if move.invoice_date < datetime.date(2017, 1, 1):
                if move.state != 'draft':
                    move.button_draft()
                if move.state == 'draft':
                    move.unlink()
                    continue

            if move.state != 'draft' or not move.piece_comptable or not move.fiscal_position_id:
                continue

            if not move.invoice_line_ids:
                # Import the line
                piece_comptable = eval(move.piece_comptable)
                if len(piece_comptable):
                    domain = [('invoice_id.move_id', '=', piece_comptable[0])]
                    remote_ids = sync_obj.remote_search(domain)
                    remote_values = sync_obj.remote_read(remote_ids)
                    sync_obj.write_local_value(remote_values)
            else:
                move.action_reload_imported()

            move.invoice_line_ids.update_imported_line()

            for line in move.invoice_line_ids:
                if not line.price_unit:
                    continue

                price_unit = line.price_unit * (1.0 - (line.discount / 100.0))
                if price_unit == 0.0:
                    pass
                elif line.histo_subtotal != line.price_subtotal:
                    if line.product_uom_id == uom_weight:
                        line.weight = line.histo_subtotal / price_unit
                        line.quantity = line.weight

                    else:
                        line.uom_qty = line.histo_subtotal / price_unit / line.product_id.base_unit_count
                        line.quantity = line.histo_subtotal / price_unit

            if move.piece_comptable and round(move.total_ttc, 2) == round(move.amount_total, 2):
                if move.fiscal_position_id and move.piece_comptable:
                    try:
                        move.sudo().with_context(force_sequence=True).action_post()
                        if round(move.total_ttc, 2) == round(move.amount_total, 2):
                            move.payment_state = 'paid'

                    except Exception as e:
                        move.imported_state = e

            else:
                move.imported_state = 'Amount KO'

        return True

    def action_write_lot_imported(self):
        """ write the imported lot on the invoice """
        for move in self:
            move.invoice_line_ids.update_imported_line()

    def action_reload_imported(self):
        """ An error is on this invoice, check some action to correct this situation """
        synchro_obj_line = self.env['synchro.obj'].search([('model_name', '=', 'account.invoice.line')])

        for move in self:
            mapping_line = self.env['synchro.obj.line'].search(
                [('local_id', 'in', move.invoice_line_ids.ids), ('obj_id', '=', synchro_obj_line.id)])
            mapping_line.update_values()
            move.invoice_line_ids.update_imported_line()

    def _get_last_sequence_domain(self, relaxed=False):
        # Need to have the same calculation for all sale journal
        self.ensure_one()
        if not self.journal_id:
            return "WHERE FALSE", {}
        journal_ids = self.env['account.journal'].search([('type', '=', self.journal_id.type)])

        where_string = "WHERE journal_id in %(journal_ids)s AND name != '/'"
        param = {'journal_ids': tuple(journal_ids.ids)}
        is_payment = self.payment_id or self._context.get('is_payment')

        if not relaxed:
            domain = [('journal_id', '=', self.journal_id.id), ('id', '!=', self.id or self._origin.id), ('name', 'not in', ('/', '', False))]
            if self.journal_id.refund_sequence:
                refund_types = ('out_refund', 'in_refund')
                domain += [('move_type', 'in' if self.move_type in refund_types else 'not in', refund_types)]
            if self.journal_id.payment_sequence:
                domain += [('payment_id', '!=' if is_payment else '=', False)]
            reference_move_name = self.search(domain + [('date', '<=', self.date)], order='date desc', limit=1).name
            if not reference_move_name:
                reference_move_name = self.search(domain, order='date asc', limit=1).name
            sequence_number_reset = self._deduce_sequence_number_reset(reference_move_name)

        if self.journal_id.refund_sequence:
            if self.move_type in ('out_refund', 'in_refund'):
                where_string += " AND move_type IN ('out_refund', 'in_refund') "
            else:
                where_string += " AND move_type NOT IN ('out_refund', 'in_refund') "
        elif self.journal_id.payment_sequence:
            if is_payment:
                where_string += " AND payment_id IS NOT NULL "
            else:
                where_string += " AND payment_id IS NULL "

        return where_string, param

    @api.depends('name', 'journal_id')
    def _compute_made_sequence_hole(self):

        self.env.cr.execute("""
            SELECT this.id
              FROM account_move this
              JOIN res_company company ON company.id = this.company_id
         LEFT JOIN account_move other ON this.move_type = other.move_type
                                     AND this.sequence_prefix = other.sequence_prefix
                                     AND this.sequence_number = other.sequence_number + 1
             WHERE other.id IS NULL
                AND this.invoice_date > '2022-12-31'
               AND this.sequence_number != 1
               AND this.name != '/'
               AND this.id = ANY(%(move_ids)s)
        """, {
            'move_ids': self.ids,
        })
        made_sequence_hole = set(r[0] for r in self.env.cr.fetchall())
        for move in self:
            move.made_sequence_hole = move.id in made_sequence_hole

    def update_picking(self):
        for invoice in self:
            # Get the list of picking
            picking_ids = invoice.picking_ids
            if not picking_ids:
                for invoice_line in invoice.invoice_line_ids:
                    for sale_line in invoice_line.sale_line_ids:
                        for stock_move in sale_line.move_ids:
                            picking_ids |= stock_move.picking_id
                invoice.picking_ids = picking_ids

    @api.model
    def get_duplicate_invoices(self):
        # Requête pour regrouper par le champ 'name' et filtrer les doublons
        self.env.cr.execute("""
            SELECT name 
            FROM account_move 
            WHERE state = 'draft'
            GROUP BY name 
            HAVING COUNT(id) > 1
        """)

        # Récupérer tous les 'name' en double
        duplicate_names = [row[0] for row in self.env.cr.fetchall()]
        return duplicate_names

    def update_statistic(self):
        """ Update value to use in statistic """
        uom_weight = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()

        for invoice in self:

            if invoice.piece_comptable:
                continue
            for line in invoice.line_ids:
                # Update lot information
                line.account_move_line_lot_ids.lot_id.sudo().compute_cost_price()
                line.account_move_line_lot_ids.lot_id.sudo().get_partner_supplier()

                if not line.cost_price:
                    line.cost_price = line.product_id.workshop_cost_price

                if line.discount <= 0.0 or not line.discount:
                    cadeau = 0.0
                elif line.discount > 100.0:
                    cadeau = - line.move_id.direction_sign * line.price_subtotal
                else:
                    cadeau = - line.move_id.direction_sign * line.price_subtotal * line.discount / (100.0 - line.discount)

                if cadeau <= 0.0:
                    cadeau = 0.0
                elif cadeau > line.price_subtotal:
                    cadeau = line.price_subtotal
                line.cadeau = - line.move_id.direction_sign * cadeau

                # margin
                if invoice.move_type in ['in_invoice', 'in_refund', 'in_receipt']:
                    line.margin = 0.0
                else:
                    line.margin = line.price_subtotal - line.cost_price * line.quantity

    def action_post(self):
        """ post invoice , update the invoice with the real weight and recompute tax """
        if self.env.context.get('update_discount_stock'):
            self.sudo().update_discount_stock()
        self.sudo().update_statistic()
        self.update_origin()
        return super().action_post()

