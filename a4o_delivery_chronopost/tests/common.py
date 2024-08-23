# This file is part of an Adiczion's Module.
# The COPYRIGHT and LICENSE files at the top level of this repository
# contains the full copyright notices and license terms.
from odoo.addons.base.tests.common import TransactionCase
from datetime import datetime


class TestChronopostCommon(TransactionCase):
    ''' Setup with chronopost test configuration. '''
    @classmethod
    def setUpClass(cls):
        super(TestChronopostCommon, cls).setUpClass()

        cls.url_base = "https://ws.chronopost.fr"

        cls.today = datetime.today()
        cls.today_isoweek = cls.today.isoweekday()

        cls.company_data = {
            'account_number': "19869502",
            'account_passwd': "255562",
            'shipping_url': (
                "%s/shipping-cxf/ShippingServiceWS?wsdl" % cls.url_base),
            'tracking_url': (
                "%s/tracking-cxf/TrackingServiceWS?wsdl" % cls.url_base),
            'relaypoint_url': (
                "%s/recherchebt-ws-cxf/PointRelaisServiceWS?wsdl"
                % cls.url_base),
            'default_pricelist': cls.env['product.pricelist'].create({
                'name': 'default_pricelist',
                'currency_id': cls.env.company.currency_id.id,
                }),
            'product_category': cls.env['product.category'].create({
                'name': 'Test category',
                }),
            }

        cls.sender = cls.env['res.partner'].create({
            'name': 'Adiczion',
            'street': '1 avenue Louis COIRARD',
            'street2': 'Rés. les Hespérides',
            'city': 'Aix en Provence',
            'zip': '13090',
            'country_id': cls.env['res.country'].search([
                ('code', '=', 'FR')]).id,
            'email': 'contact@adiczion.com',
            'phone': '+33950693113',
            'company_id': False,
            })
        cls.europe_customer = cls.env['res.partner'].create({
            'name': 'Customer in Belgium',
            'street': 'Jean Joseph Piret 45',
            'city': 'Joncret',
            'zip': '6280',
            'country_id': cls.env['res.country'].search([
                ('code', '=', 'BE')]).id,
            'company_id': False,
            })
        cls.france_customer = cls.env['res.partner'].create({
            'name': 'Adiczion (desk)',
            'street': '8 rue Jean DARET',
            'street2': 'Bât 10',
            'city': 'Aix en provence',
            'zip': '13090',
            'country_id': cls.env['res.country'].search([
                ('code', '=', 'FR')]).id,
            'company_id': False,
            })

        cls.package = cls.env['product.packaging'].search([
                ('name', '=', 'Chronopost Custom Parcel'),
                ])

        cls.product = cls.env['product.product'].create({
            'name': 'Product to order',
            'categ_id': cls.company_data['product_category'].id,
            'standard_price': 235.0,
            'list_price': 280.0,
            'type': 'consu',
            'weight': 0.01,
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'uom_po_id': cls.env.ref('uom.product_uom_unit').id,
            'default_code': 'FURN_9999',
            'invoice_policy': 'order',
            'expense_policy': 'no',
            'taxes_id': [(6, 0, [])],
            'supplier_taxes_id': [(6, 0, [])],
            })
