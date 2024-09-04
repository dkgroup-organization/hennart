# This file is part of an Adiczion's Module.
# The COPYRIGHT and LICENSE files at the top level of this repository
# contains the full copyright notices and license terms.
from odoo.tests import tagged
from .common import TestChronopostCommon


@tagged('post_install', '-at_install')
class Test2ShopInternationnal(TestChronopostCommon):
    ''' Test the order of a sale with a chronopost shipping method.
        ./base/odoo-bin -c test.conf -i a4o_delivery_chronopost
        --test-tags /a4o_delivery_chronopost -d db_test --stop-after-init
    '''
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.delivery_method = cls.env['delivery.carrier'].create({
            'name': "Chronopost - 2Shop EU",
            'product_id': cls.env['product.product'].search([
                ('default_code', '=', 'chrono01'),
                ])[0].id,
            'product_code': "5H",
            'delivery_type': "chronopost",
            'cpst_service_type': "relaypoint",
            'cpst_service': (cls.env['delivery.carrier.chronopost_service']
                .search([('code', '=', "345")])[0].id),
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
            'partner_id': cls.europe_customer.id,
            'partner_invoice_id': cls.europe_customer.id,
            'partner_shipping_id': cls.europe_customer.id,
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

    def test_shipping(self):
        """ Test the flow of sales orders through to shipment with
            the chronopost carrier between two shop in France
            and the product code 5H.
        """
        self.sale_order.order_line.read(
            ['name', 'price_unit', 'product_uom_qty', 'price_total'])
        self.sale_order.carrier_id = self.delivery_method.id
        self.assertEqual(self.sale_order.amount_total,
            560.0, 'Sale: total amount is wrong')

        # confirm quotation
        self.sale_order.action_confirm()
        self.assertTrue(self.sale_order.picking_ids,
            'Sale Stock: no picking created for "invoice on delivery"'
                'storable products')
        self.assertTrue(self.sale_order.state == 'sale')
        self.assertTrue(self.sale_order.invoice_status == 'to invoice')

        # order delivery
        self.assertEqual(self.sale_order.delivery_count,
            1.0, 'Delivery: the number of deliveries is wrong')
        self.assertEqual(self.sale_order.picking_ids.carrier_id.name,
            'Chronopost - 2Shop EU',
            'Delivery: the delivery carrier is wrong')
        self.assertTrue(self.sale_order.picking_ids.state == 'assigned')

        # pack the order
        pack = self.sale_order.picking_ids.action_put_in_pack()
        pack['context'].update({
            # Packaging Chronopost
            'shipping_weight': 5.0,
            'delivery_packaging_id': self.package,
            'picking_ids': self.sale_order.picking_ids,
        })
        wiz_pack = self.env['choose.delivery.package'].with_context(
            pack['context']).create({})
        wiz_pack.action_put_in_pack()
        self.assertTrue(self.sale_order.picking_ids.package_ids,
            'Picking: no packages ready to this shipment')
        self.assertEqual(len(self.sale_order.picking_ids.package_ids),
            1.0, 'Picking: number of package made is wrong')

        # choose a relaypoint
        wiz = self.sale_order.picking_ids.action_get_relaypoint()
        relaypoint = self.env['delivery.carrier.relaypoint'].with_context(
            wiz['context']).create({})
        relaypoint.get_relaypoint()
        relaypoint = relaypoint.lines[0].set_destination()
        self.sale_order.picking_ids.relaypoint_delivery = relaypoint

        # validate the delivery
        self.sale_order.picking_ids.button_validate()
        self.assertTrue(self.sale_order.picking_ids.state == 'done')
        self.assertTrue(self.sale_order.picking_ids.carrier_tracking_ref,
            'Tracking number: No tracking number for this shipment')
