# This file is part of an Adiczion's Module.
# The COPYRIGHT and LICENSE files at the top level of this repository
# contains the full copyright notices and license terms.
from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.tools import pdf
from .chronopost_request import (ChronopostRequest, LABEL_FORMAT, 
    PRODUCT_SERVICE)
import re
import logging

_logger = logging.getLogger(__name__)

#class RelayPointChronopost(models.Model):
#    _inherit = 'delivery.carrier.relaypoint'
#
#    cpst_url_google_maps = fields.Char(
#        string='URL Google Maps', groups="base.group_system")

class Module(models.Model):
    _inherit = "ir.module.module"

    def button_immediate_upgrade(self):
        super().button_immediate_upgrade()
        for module in list(self):
            if module.name == 'a4o_delivery_chronopost':
                return self._button_immediate_function(type(self).button_upgrade)


class ChronopostService(models.Model):
    _name = 'delivery.carrier.chronopost_service'
    _description = 'Chronopost Service List'

    name = fields.Char('Service Name', translate=True)
    code = fields.Char('Service code')
    category = fields.Char('Chronopost Product Category',
        help="Service category of Chronopost products")


class ProviderChronopost(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(
        selection_add=[('chronopost', "Chronopost")],
        ondelete={'chronopost': 'set default'})
    product_code = fields.Char(
        string='Product Code', groups="base.group_system", size=2,
        help="Product code defined on the contract signed with Chronopost")
    cpst_product_category = fields.Char('Chronopost Product Category',
        help="Product code category to apply the correct selection of "
             "services (technical field).")
    cpst_service_type = fields.Selection([
            ('relaypoint', 'Relay point'),
            ('other', 'Other'),
            ], string='Service type', default='other',
        help="Indicates whether the product code used corresponds to a relay "
             "point or not.")
    cpst_service = fields.Many2one('delivery.carrier.chronopost_service',
        string='Service',
        help="Depending on the product, delivery day requested or "
             "characteristic of the type of service.")
    cpst_service_computed = fields.Boolean('Computed Service ?', default=False,
        help="Indicates whether the service will be calculated or selected "
             "from the updated list based on the product code (technical "
             "fields)")
    cpst_prod_account_number = fields.Char(
        string='Account Number (prod.)', groups="base.group_system", size=8,
        help="Production account number, will be used when this carrier has "
             "gone 'into production'.")
    cpst_prod_sub_account = fields.Char(
        string='Sub Account (prod.)', default='000', size=3,
        groups="base.group_system",
        help="Production sub-account number, can remain empty.")
    cpst_prod_passwd = fields.Char(
        string='Password (prod.)', groups="base.group_system", size=6,
        help="Production password, will be used when this carrier has gone "
             "'into production'.")
    cpst_test_account_number = fields.Char(
        string='Account Number (test)', groups="base.group_system", size=8,
        help="Test account number, will be used when this carrier has gone "
             "'into test'.")
    cpst_test_sub_account = fields.Char(
        string='Sub Account (test)', default='000', size=3,
        groups="base.group_system",
        help="Test sub-account number, can remain empty.")
    cpst_test_passwd = fields.Char(
        string='Password (test)', groups="base.group_system", size=6,
        help="Test password, will be used when this carrier has gone "
             "'into test'.")
    cpst_label_format = fields.Selection(LABEL_FORMAT, string="Label Format",
        required=True, default='PDF')
    cpst_remove_label = fields.Boolean(
        'Remove attached label', default=False,
        help="When canceling a shipment, remove the attached labels.")
    cpst_shipping_url = fields.Char(
        string='Shipping URL', groups="base.group_system",
        help="WSDL url for shipping.")
    cpst_tracking_url = fields.Char(
        string='Tracking URL', groups="base.group_system",
        help="WSDL url for tracking and cancelling.")
    cpst_relaypoint_url = fields.Char(
        string='Relay Point URL', groups="base.group_system",
        help="WSDL url for searching relay point.")
    cpst_max_point = fields.Integer(
        string="Relay Points Max", default=5,
        help="Max number of relay points returned by the search request.")
    cpst_distance_search = fields.Integer(
        string="Search distance", default=10,
        help="Maximum search distance of relay points in the request.")
    cpst_direct_printing = fields.Boolean('Direct Printing', default=False,
        help="Directly print the label when the delivery is validate,"
             "if the module : report_base_to_printer is installed")
    cpst_printer_name = fields.Char()
    cpst_printer = fields.Char("Selected printer",
        help="Display the name of the selected printer.")
    cpst_printer_id = fields.Many2one('printing.printer',
        string='Chronopost Printer',
        compute='cpst_compute_printer_id',
        help="printer")

    @api.onchange('cpst_direct_printing')
    def _onchange_cpst_direct_printing(self):
        User = self.env['res.users']
        result = {}
        if self.cpst_direct_printing:
            if not hasattr(User, 'printing_printer_id'):
                _logger.error('Please install and configure module :'
                              'base_report_to_printer')
                self.cpst_direct_printing = False
                result.update({'warning': {
                    'title': _('Error!'),
                    'message': _('Please install and configure module :'
                                 'base_report_to_printer')
                    }})
                return result
        else:
            # Reset the printer info.
            self.cpst_printer_name = None
            self.cpst_printer = None

    @api.depends('cpst_printer_name')
    def cpst_compute_printer_id(self):
        User = self.env['res.users']
        for record in self:
            record.cpst_printer_id = None
            if (record.cpst_printer_name
                    and hasattr(User, 'printing_printer_id')):
                record.cpst_printer_id = int(
                    record.cpst_printer_name.split(',')[1])

    def cpst_action_get_printer(self):
        context = dict(self.env.context or {})
        # Get printer
        context.update({
            'carrier_id': self.id,
            'default_printer_id': (self.cpst_printer_id
                and self.cpst_printer_id.id
                or None),
            })
        return {
            'name': _('Select the printer'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'cpstselect.printer',
            'view_id': self.env.ref(
                'a4o_delivery_chronopost.cpst_select_printer_view_form').id,
            'type': 'ir.actions.act_window',
            'context': context,
            'target': 'new'
        }

    def _check_value(self, value, size):
        if len(value) != size:
            raise UserError(_('This field must have to %s characters!') % size)
        if re.search("[^0-9]", value):
            raise UserError(_('Only digit chars are authorised in this field!'))
        return value

    @api.onchange('cpst_prod_account_number')
    def onchange_cpst_prod_account_number(self):
        if self.cpst_test_account_number:
            self.cpst_prod_account_number = self._check_value(
                self.cpst_prod_account_number, 8)

    @api.onchange('cpst_test_account_number')
    def onchange_cpst_test_account_number(self):
        if self.cpst_test_account_number:
            self.cpst_test_account_number = self._check_value(
                self.cpst_test_account_number, 8)

    @api.onchange('cpst_prod_passwd')
    def onchange_cpst_prod_passwd(self):
        if self.cpst_prod_passwd:
            self.cpst_prod_passwd = self._check_value(
                self.cpst_prod_passwd, 6)

    @api.onchange('cpst_test_passwd')
    def onchange_cpst_test_passwd(self):
        if self.cpst_test_passwd:
            self.cpst_test_passwd = self._check_value(
                self.cpst_test_passwd, 6)

    @api.onchange('product_code')
    def onchange_product_code(self):
        self.cpst_product_category = self.get_cpst_product_category()
        self.cpst_service = None
        self.cpst_service_computed = False
        services = self.env['delivery.carrier.chronopost_service'].search([
            ('category', '=', self.cpst_product_category),
            ])
        if len(services) == 1:
            self.cpst_service = services[0]
            if services[0].code == 'computed':
                self.cpst_service_computed = True

    def chronopost_send_shipping(self, pickings):
        _logger.debug("chronopost_send_shipping: begin")
        res = []
        cpst = ChronopostRequest(self.prod_environment, self.log_xml)
        for picking in pickings:
            package_count = len(picking.package_ids)
            if not package_count:
                raise UserError(_('No packages for this picking!'))
            shipping = cpst.shipping_request(**{
                'carrier': self.sudo(),
                'picking': picking,
                })
            carrier_tracking_ref = shipping['tracking_number']

            currency = (
                picking.sale_id.currency_id or picking.company_id.currency_id)
            if currency.name == shipping['currency']:
                carrier_price = float(shipping['price'])
            else:
                quote_currency = self.env['res.currency'].search([
                    ('name', '=', shipping['currency']),
                    ], limit=1)
                carrier_price = quote_currency._convert(
                    float(shipping['price']), currency, picking.company_id,
                    picking.sale_id.date_order or fields.Date.today())

            package_labels = cpst.get_label()
            log_message = (
                _("Shipment created into Chronopost<br/> "
                    "<b>Tracking Numbers:</b> %s<br/>"
                    "<b>Packages:</b> %s") % (
                        carrier_tracking_ref,
                        ', '.join([pl[0] for pl in package_labels])))

            attachments = []
            if picking.carrier_id.cpst_label_format == 'PDF':
                labels = pdf.merge_pdf([pl[1] for pl in package_labels])
                attachments = [(
                        _('Label_Chronopost.pdf'), labels)]
                if picking.carrier_id.cpst_direct_printing:
                    self._print_document(labels,
                        picking.carrier_id.cpst_printer_id)
            else:
                for idx, label in enumerate([pl[1] for pl in package_labels]):
                    attachments.append((
                            _('Label_Chronopost-%s.%s') % (idx,
                                self.cpst_label_format),
                            label))
                    if picking.carrier_id.cpst_direct_printing:
                        self._print_document(label,
                            picking.carrier_id.cpst_printer_id)
            picking.message_post(body=log_message, attachments=attachments)

            shipping_data = {
                'exact_price': carrier_price,
                'tracking_number': carrier_tracking_ref,
                }
            res += [shipping_data]
        return res

    def chronopost_cancel_shipment(self, picking):
        cpst = ChronopostRequest(self.prod_environment, self.log_xml)
        result = cpst.cancel_request(picking, self.sudo())
        if result:
            # Remove attachment ...
            if self.cpst_remove_label:
                attachments = self.env['ir.attachment'].search([
                    ('res_model', '=', picking._name),
                    ('res_id', '=', picking.id),
                    ('name', 'like', '_Chronopost'),
                    ])
                if attachments:
                    attachments.unlink()
            picking.message_post(
                body=_("Chronopost expedition with tracking number %s "
                    "canceled!") % (picking.carrier_tracking_ref))
            picking.write({
                'carrier_tracking_ref': '',
                'carrier_price': 0.0,
                })

    def chronopost_get_tracking_link(self, picking):
        lang = 'en'
        if self.env.context.get('lang') == 'fr_FR':
            lang = 'fr'
        return ('http://www.chronopost.fr/tracking-no-cms/suivi-page?langue=%s'
                '&listeNumerosLT=%s' % (lang, picking.carrier_tracking_ref))

    def chronopost_rate_shipment(self, order):
        res = {
            'success': False,
            'price': 0.0,
            'warning_message': _("Don't forget to check the price!"),
            'error_message': None,
            }
        vals = self.base_on_rule_rate_shipment(order)
        if vals.get('success'):
            price = vals['price']
            res.update({
                'success': True,
                'price': price,
                })
        return res

    @api.depends('cpst_service_type')
    def chronopost_get_delivery_relaypoint(self):
        self = self.sudo()
        if self.cpst_service_type == 'relaypoint':
            return True
        return False
        
    def chronopost_select_relaypoint(self, **kwargs):
        _logger.debug('chronopost_select_relaypoint:' % kwargs)
        relaypoints = []
        cpst = ChronopostRequest(self.prod_environment, self.log_xml)
        kwargs.update({'carrier': self.sudo()})
        return cpst.relaypoint_request(**kwargs)

    @api.depends('product_code')
    def get_cpst_product_category(self):
        service_category = 'STD'
        for key, value in PRODUCT_SERVICE.items():
            if self.product_code and self.product_code in key:
                service_category = value
        return service_category
