import logging
from collections import defaultdict
from datetime import date

from dateutil.relativedelta import relativedelta
from stdnum.vatin import is_valid

from odoo import _, api, fields, models
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.tools import float_is_zero

_logger = logging.getLogger(__name__)


class IntrastatProductDeclaration(models.Model):
    _inherit = "intrastat.product.declaration"

    def _prepare_invoice_domain(self):
        """ filtered invoice         """
        domain = super()._prepare_invoice_domain()
        domain.append(("partner_id.exclude_from_intrastat", "!=", True))
        return domain

    def _is_product(self, invoice_line):
        """ filtered product         """
        res = super()._is_product(invoice_line)
        if invoice_line.product_id.exclude_from_intrastat:
            return False
        else:
            return res


    def _gather_invoices(self, notedict):
        lines = []
        qty_prec = self.env["decimal.precision"].precision_get(
            "Product Unit of Measure"
        )
        accessory_costs = self.company_id.intrastat_accessory_costs
        eu_countries = self.env.ref("base.europe").country_ids

        self._gather_invoices_init(notedict)
        domain = self._prepare_invoice_domain()
        order = "journal_id, name"
        invoices = self.env["account.move"].search(domain, order=order)
        logistical_discount_product = self.env['product.pricelist.discount'].get_discount_product()

        for invoice in invoices:

            lines_current_invoice = []
            total_inv_accessory_costs_cc = 0.0  # in company currency
            total_inv_product_cc = 0.0  # in company currency
            total_inv_weight = 0.0
            notedict["inv_origin"] = invoice.name
            for line_nbr, inv_line in enumerate(
                invoice.invoice_line_ids.filtered(
                    lambda x: x.display_type == "product"
                ),
                start=1,
            ):
                # add logistical discount management
                if inv_line.product_id in logistical_discount_product:
                    continue

                notedict["invline_origin"] = _("%(invoice)s line %(line_nbr)s") % {
                    "invoice": invoice.name,
                    "line_nbr": line_nbr,
                }
                inv_intrastat_line = invoice.intrastat_line_ids.filtered(
                    lambda r: r.invoice_line_id == inv_line
                )

                if (
                    accessory_costs
                    and inv_line.product_id
                    and inv_line.product_id.is_accessory_cost
                ):
                    acost = invoice.currency_id._convert(
                        inv_line.price_subtotal,
                        self.company_id.currency_id,
                        self.company_id,
                        invoice.date,
                    )
                    total_inv_accessory_costs_cc += acost

                    continue

                if float_is_zero(inv_line.quantity, precision_digits=qty_prec):
                    _logger.info(
                        "Skipping invoice line %s qty %s "
                        "of invoice %s. Reason: qty = 0"
                        % (inv_line.name, inv_line.quantity, invoice.name)
                    )
                    continue

                partner_country = self._get_partner_country(
                    inv_line, notedict, eu_countries
                )
                # When the country is the same as the company's country must be skipped.
                if partner_country == self.company_id.country_id:
                    _logger.info(
                        "Skipping invoice line %s qty %s "
                        "of invoice %s. Reason: partner_country = "
                        "company country"
                        % (inv_line.name, inv_line.quantity, invoice.name)
                    )
                    continue

                if inv_intrastat_line:
                    hs_code = inv_intrastat_line.hs_code_id
                elif inv_line.product_id and self._is_product(inv_line):
                    hs_code = inv_line.product_id.get_hs_code_recursively()
                    if not hs_code:
                        msg = _("Missing <em>H.S. Code</em>")
                        notedict["product"][inv_line.product_id.display_name][msg].add(
                            notedict["invline_origin"]
                        )
                        continue
                else:
                    _logger.info(
                        "Skipping invoice line %s qty %s "
                        "of invoice %s. Reason: no product nor Intrastat Code"
                        % (inv_line.name, inv_line.quantity, invoice.name)
                    )
                    continue

                intrastat_transaction = self._get_intrastat_transaction(
                    inv_line, notedict
                )

                if inv_intrastat_line:
                    weight = inv_intrastat_line.transaction_weight
                    suppl_unit_qty = inv_intrastat_line.transaction_suppl_unit_qty
                else:
                    weight, suppl_unit_qty = self._get_weight_and_supplunits(
                        inv_line, hs_code, notedict
                    )
                total_inv_weight += weight

                sign = invoice.move_type in ("in_invoice", "out_refund") and 1 or -1

                # Add logistical discount on sub_total
                logistical_discount = 1.0
                if invoice.total_logistical_discount != 0.0 and (invoice.amount_untaxed_signed - invoice.total_logistical_discount) != 0.0:
                    logistical_discount = invoice.amount_untaxed_signed / (invoice.amount_untaxed_signed - invoice.total_logistical_discount)
                amount_company_currency = sign * inv_line.balance * logistical_discount

                total_inv_product_cc += amount_company_currency

                if inv_intrastat_line:
                    product_origin_country = (
                        inv_intrastat_line.product_origin_country_id
                    )
                else:
                    product_origin_country = self._get_product_origin_country(
                        inv_line, notedict
                    )

                region_code = self._get_region_code(inv_line, notedict)
                region = self.env["intrastat.region"]
                if not region_code:
                    region = self._get_region(inv_line, notedict)

                partner = self._get_partner_and_warn_vat(inv_line, notedict)

                line_vals = {
                    "parent_id": self.id,
                    "invoice_line_id": inv_line.id,
                    "src_dest_country_id": partner_country.id,
                    "product_id": inv_line.product_id.id,
                    "hs_code_id": hs_code.id,
                    "weight": weight,
                    "suppl_unit_qty": suppl_unit_qty,
                    "amount_company_currency": amount_company_currency,
                    "amount_accessory_cost_company_currency": 0.0,
                    "transaction_id": intrastat_transaction.id,
                    "product_origin_country_id": product_origin_country.id or False,
                    "region_code": region_code or region.code,
                    "region_id": region and region.id or False,
                    "partner_id": partner.id,
                }

                # extended declaration
                if self.reporting_level == "extended":
                    transport = self._get_transport(inv_line, notedict)
                    line_vals.update({"transport_id": transport.id})

                self._update_computation_line_vals(inv_line, line_vals, notedict)

                if line_vals:
                    lines_current_invoice.append(line_vals)

            self._handle_invoice_accessory_cost(
                invoice,
                lines_current_invoice,
                total_inv_accessory_costs_cc,
                total_inv_product_cc,
                total_inv_weight,
            )

            for line_vals in lines_current_invoice:
                if (
                    not line_vals["amount_company_currency"]
                    and not line_vals["amount_accessory_cost_company_currency"]
                ):
                    inv_line = self.env["account.move.line"].browse(
                        line_vals["invoice_line_id"]
                    )
                    _logger.info(
                        "Skipping invoice line %s qty %s "
                        "of invoice %s. Reason: price_subtotal = 0 "
                        "and accessory costs = 0",
                        inv_line.name,
                        inv_line.quantity,
                        inv_line.move_id.name,
                    )
                    continue
                lines.append(line_vals)

        return lines
