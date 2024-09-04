# This file is part of an Adiczion's Module.
# The COPYRIGHT and LICENSE files at the top level of this repository
# contains the full copyright notices and license terms.
from odoo.tests import tagged
from .common import TestChronopostCommon


@tagged('post_install', '-at_install')
class TestDeliveryAvailable(TestChronopostCommon):
    ''' Test the availibility feature on the chronopost shipping method.
        ./base/odoo-bin -c test.conf -i a4o_delivery_chronopost
        --test-tags /a4o_delivery_chronopost -d db_test --stop-after-init
    '''
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.delivery_method = cls.env['delivery.carrier'].create({
            'name': "Chronopost: Chrono 13H",
            'product_id': cls.env['product.product'].search([
                ('default_code', '=', 'chrono01'),
                ])[0].id,
            'product_code': "01",
            'delivery_type': "chronopost",
            'availability_day': "interval",
            'from_day': str(cls.today_isoweek),
            'from_time': 0.0,
            'to_day': str(cls.today_isoweek + 2),
            'to_time': 0.0,
            'cpst_service_type': "other",
            'cpst_service': (cls.env['delivery.carrier.chronopost_service']
                .search([('code', '=', "1")])[0].id),
            'sender_id': cls.sender.id,
            # Test login proposed by the Chronopost API
            'cpst_test_account_number': cls.company_data['account_number'],
            'cpst_test_passwd': cls.company_data['account_passwd'],
            'cpst_shipping_url': cls.company_data['shipping_url'],
            'cpst_tracking_url': cls.company_data['tracking_url'],
            'cpst_relaypoint_url': cls.company_data['relaypoint_url'],
            })

        SaleOrder = cls.env['sale.order'].with_context(tracking_disable=True)
        # create a generic Sale Order with all classical products
        cls.sale_order = SaleOrder.create({
            'partner_id': cls.france_customer.id,
            'partner_invoice_id': cls.france_customer.id,
            'partner_shipping_id': cls.france_customer.id,
            'pricelist_id': cls.company_data['default_pricelist'].id,
        })
        cls.sale_order_line_1 = cls.env['sale.order.line'].create({
            'name': cls.product.name,
            'product_id': cls.product.id,
            'product_uom_qty': 2,
            'product_uom': cls.product.uom_id.id,
            'price_unit': cls.product.list_price,
            'order_id': cls.sale_order.id,
            'tax_id': False,
        })

    def test_delivery_available(self):
        ''' Test that the avalibility of the delivery method is true.
        '''
        # Method of delivery created is available today
        self.sale_order.order_line.read(
            ['name', 'price_unit', 'product_uom_qty', 'price_total'])
        self.assertEqual(self.sale_order.amount_total,
            560.0, 'Sale: total amount is wrong')

        # Check that the delivery method is available to the user
        add_carrier = self.sale_order.action_open_delivery_wizard()
        wiz = self.env['choose.delivery.carrier'].with_context(
            add_carrier['context']).create({})
        wiz.available_carrier_ids
        self.assertTrue(self.delivery_method in wiz.available_carrier_ids)

    def test_delivery_unavailable(self):
        ''' Test that the avalibility of the delivery method is false.
        '''
        # Method of delivery created is from tomorrow
        self.delivery_method.from_day = str(self.today_isoweek + 1)
        self.sale_order.order_line.read(
            ['name', 'price_unit', 'product_uom_qty', 'price_total'])
        self.assertEqual(self.sale_order.amount_total,
            560.0, 'Sale: total amount is wrong')

        # Check that the delivery method is unavailable to the user
        add_carrier = self.sale_order.action_open_delivery_wizard()
        wiz = self.env['choose.delivery.carrier'].with_context(
            add_carrier['context']).create({})
        wiz.available_carrier_ids
        self.assertTrue(self.delivery_method not in wiz.available_carrier_ids)
