# See LICENSE file for full copyright and licensing details.

import logging
_logger = logging.getLogger(__name__)
log = _logger.info
from odoo import api, fields, models
from datetime import timedelta
from odoo.tools.translate import _
import threading
import time


class BaseSynchroServer(models.Model):
    """Class to store the information regarding server."""
    _inherit = "synchro.server"

    date_start = fields.Date("Start date", default="2020-01-01")
    date_stop = fields.Date("Stop date", default="2020-12-31")
    account_file = fields.Char("account file path",
        default="/mnt/extra-addons/sirius_synchro_account/datas/account_account.csv")

    def intialize_all(self):
        "initialize all data"
        sql = """
delete from account_partial_reconcile;
delete from  account_move_line;
delete from  account_move;
delete from account_payment;
delete from account_full_reconcile;
delete from purchase_order_line;
delete from purchase_order;
delete from sale_order_line;
delete from sale_order;
delete from stock_quant;
delete from stock_move_line;
delete from stock_move;
delete from stock_picking;
delete from stock_valuation_layer;
"""

        self.env.cr.execute(sql)
        product_ids = self.env['product.template'].search([])
        product_ids.write({'standard_price': 0.0})

        #sql2 = "select id from product_template where default_code = name"
        #self.env.cr.execute(sql2)
        #sql_reponse = self.env.cr.fetchall()
        #_logger.info('\n%s' % sql_reponse)
        #product_ids = self.env['product.template'].search([('id', 'in', sql_reponse)])

    def migrate_sale_product(self, remote_ids):
        "Migrate the product before sale"
        self.ensure_one()

        sale_line_obj = self.get_obj('sale.order.line')
        remote_company_ids = self.remote_company_ids()

        groupby_domain = [
                    ('company_id', 'in', remote_company_ids),
                    ('order_id', 'in', remote_ids)]
        product_remote_ids = sale_line_obj.read_groupby_ids(
                        'product_id', groupby_domain)
        self.migrate_simple_product(product_remote_ids)

    def migrate_invoice_product(self, remote_ids):
        "Migrate the product before invoice"
        self.ensure_one()

        invoice_line_obj = self.get_obj('account.invoice.line')
        remote_company_ids = self.remote_company_ids()

        groupby_domain = [
                    ('company_id', 'in', remote_company_ids),
                    ('invoice_id', 'in', remote_ids)]
        product_remote_ids = invoice_line_obj.read_groupby_ids(
                        'product_id', groupby_domain)
        self.migrate_simple_product(product_remote_ids)

    def migrate_simple_product(self, remote_ids):
        " Migrate product with no variant, check doublon with default_code"
        self.ensure_one()

        product_obj = self.get_obj('product.product')
        product_tmpl_obj = self.get_obj('product.template')

        remote_values = product_obj.remote_read(remote_ids)

        for remote_value in remote_values:

            product_tmpl_id = remote_value.get('product_tmpl_id')
            default_code = remote_value.get('default_code', '') or ''
            default_code = default_code.replace('"', '').replace(' ', '')
            barcode = remote_value.get('barcode', '') or ''
            remote_id = remote_value.get('id')

            # Check if the product is already migrate
            if product_obj.get_local_id(remote_id,
                                        no_create=True, no_search=True):
                continue

            # Check if there are doublon in the base
            product_ids = self.env['product.product'].search(
                    [('default_code', '=', default_code)])
            if not product_ids and not default_code and barcode:
                # Specifique to historical data of arc
                default_code = barcode
                product_ids = self.env['product.product'].search(
                                    ['|', ('default_code', '=', default_code),
                                     ('barcode', '=', barcode)])
            # If doublon check the linking id
            if default_code and product_ids:
                local_id = product_ids[0].id
                local_tmpl_id = product_ids[0].product_tmpl_id.id
                # check mapping id for product
                condition = [
                    ('local_id', '=', local_id),
                    ('remote_id', '=', remote_id),
                    ('obj_id', '=', product_obj.id)]
                line_ids = self.env['synchro.obj.line'].search(condition)
                if not line_ids:
                    line_vals = {
                        'local_id': local_id,
                        'remote_id': remote_id,
                        'obj_id': product_obj.id}
                    line_ids.create(line_vals)

                # check mapping id for product template
                condition = [
                    ('local_id', '=', local_tmpl_id),
                    ('remote_id', '=', product_tmpl_id[0]),
                    ('obj_id', '=', product_tmpl_obj.id)]
                line_ids = self.env['synchro.obj.line'].search(condition)
                if not line_ids:
                    line_vals = {
                        'local_id': local_tmpl_id,
                        'remote_id': product_tmpl_id[0],
                        'obj_id': product_tmpl_obj.id}
                    line_ids.create(line_vals)
            # if not doublon create product
            else:
                product_tmpl_local_id = product_tmpl_obj.get_local_id(
                                            product_tmpl_id[0])

                product_tmpl_local = self.env['product.template'].browse(
                                            product_tmpl_local_id)

                # TODO, if futur project with variant, change the rule here
                local_product_id = product_tmpl_local.product_variant_id.id

                condition = [
                    ('remote_id', '=', remote_id),
                    ('obj_id', '=', product_obj.id)]
                local_ids = self.env['synchro.obj.line'].search(condition)
                if local_ids:
                    if local_ids[0].local_id != local_product_id:
                        local_ids[0].local_id = local_product_id
                else:
                    vals_line = {
                        'obj_id': product_obj.id,
                        'remote_id': remote_id,
                        'local_id': local_product_id}
                    local_ids.create(vals_line)

                product_obj.write_local_value([remote_value])

    @api.model
    def cron_migrate_invoice(self):
        "sheduled invoice migration"
        # _logger.info('\n-------cron_migrate_invoice--------\n')
        start_time = time.time()

        for server in self.search([]):
            invoice_obj = server.get_obj('account.invoice')
            already_ids = invoice_obj.get_synchronazed_remote_ids()
            remote_company_ids = server.remote_company_ids()
            domain = eval(invoice_obj.domain or [])
            sync_limit = invoice_obj.sync_limit or 1

            condition = [
                ('company_id', 'in', remote_company_ids),
                ('id', 'not in', already_ids),
                ('state', 'not in', ['draft', 'cancel'])]
            if server.date_start:
                condition.append(('date_invoice', '>=', server.date_start))
            if server.date_stop:
                condition.append(('date_invoice', '<=', server.date_stop))

            invoice_ids = invoice_obj.remote_search(condition + domain)

            if len(invoice_ids) > sync_limit:
                invoice_ids = invoice_ids[:sync_limit]

            server.migrate_invoice_product(invoice_ids)
            _logger.info("------migrate_invoice_product------%1.0f s" % (time.time() - start_time))

            server.migrate_invoice(invoice_ids)
            _logger.info("------migrate_invoice-----%1.0f s" % (time.time() - start_time))

            invoice_obj.synchronize_date = fields.Datetime.now()

        self.reload_invoice()
        _logger.info("----------time--------------%1.0f s" % (time.time() - start_time))

    @api.model
    def reload_invoice(self, limit=5):
        "In some case, the invoice has to be reloading"
        limit = self.env.context.get('limit', 0) or limit

        # Wait some minutes before update a cron task
        update_date = fields.Datetime.now() - timedelta(minutes=10)
        local_invoice_ids = self.env['account.invoice'].search([
                    '&', '&', '&',
                    ('create_date', '<', update_date),
                    ('invoice_line_ids', '=', False),
                    ('move_id.state', '=', 'draft'),
                    '|', ('state_void_line', '=', False),
                    ('state_void_line', '=', 'to_check')
                    ])

        for server in self.search([]):
            condition = [('server_id', '=', server.id),
                         ('obj_id.model_id.model', '=', 'account.invoice'),
                         ('local_id', 'in', local_invoice_ids.ids)]

            line_ids = self.env['synchro.obj.line'].search(condition, limit=limit)
            invoice_ids = line_ids.mapped('remote_id')
            server.migrate_invoice_product(invoice_ids)

            server.migrate_invoice(invoice_ids)

    def migrate_invoice(self, invoice_ids):
        "migrate invoice for server < 13"
        self.ensure_one()
        res = []

        invoice_obj = self.get_obj('account.invoice')
        move_obj = self.get_obj('account.move')

        invoice_vals = invoice_obj.remote_read(invoice_ids)
        import_model_ids = invoice_obj.check_ids_many2x(invoice_vals)

        move_ids = list(import_model_ids.get('account.move', []))
        move_vals = move_obj.remote_read(move_ids)

        move_obj.write_local_value(move_vals)
        invoice_obj.write_local_value(invoice_vals)

        for invoice_id in invoice_ids:

            local_id = invoice_obj.get_local_id(invoice_id)
            local_invoice = self.env['account.invoice'].browse(local_id)
            local_invoice.move_id.move_type = local_invoice.type
            local_invoice.move_id.market_place = local_invoice.market_place
            local_invoice.move_id.reconciliation_shopping_feed = local_invoice.reconciliation_shopping_feed
            local_invoice.move_id.invoice_user_id = local_invoice.user_id
            local_invoice.move_id.invoice_date = local_invoice.date_invoice
            local_invoice.move_id.invoice_date_due = local_invoice.date_due

            remote_move_id = move_obj.get_remote_id(local_invoice.move_id.id)
            if remote_move_id not in move_ids:
                move_ids.append(remote_move_id)
            _logger.info('Synchronize Invoice: %s' % str(local_invoice.number))
            res.append(local_invoice.id)

        domain_line = [('invoice_id', 'in', invoice_ids)]
        invoice_line_obj = self.get_obj('account.invoice.line')
        invoice_line_ids = invoice_line_obj.remote_search(domain_line)
        invoice_line_vals = invoice_line_obj.remote_read(invoice_line_ids)
        invoice_line_obj.write_local_value(invoice_line_vals)

        domain_tax = [('invoice_id', 'in', invoice_ids)]
        tax_line_obj = self.get_obj('account.invoice.tax')
        tax_line_ids = tax_line_obj.remote_search(domain_tax)
        tax_line_vals = tax_line_obj.remote_read(tax_line_ids)
        tax_line_obj.write_local_value(tax_line_vals)

        domain_line = [
                    '&',
                    ('move_id', 'in', move_ids), '|',
                    ('credit', '!=', 0.0), ('debit', '!=', 0.0)]
        move_line_obj = self.get_obj('account.move.line')
        move_line_ids = move_line_obj.remote_search(domain_line)
        move_line_vals = move_line_obj.remote_read(move_line_ids)
        move_line_obj.with_context(check_move_validity=False).write_local_value(move_line_vals)

        for local_id in res:
            local_invoice = self.env['account.invoice'].browse(local_id)
            local_invoice.recompute_invoice()

        return res

    def button_import_account(self):
        "Check account by csv file"
        self.ensure_one()
        csvfile = open(self.account_file, 'r')
        content = csvfile.read()
        csvfile.close()

        # Check if code is 8 digit
        account_ids = self.env['account.account'].search([])
        for account in account_ids:
            if account.code == '530001':
                account.code = '53000001'
            if account.code == '512001':
                account.code = '51200001'

            if account.code.isdigit() and len(account.code) < 8:
                account.code = account.code.ljust(8, '0')

        for line in content.split('\n'):

            if line:
                line = line.split(';')
                code = line[0]
                description = line[1]
                code_copy = line[2]

                condition = [('code', '=', code)]
                account_ids = self.env['account.account'].search(condition)

                if account_ids:
                    account_ids[0].name = description
                    account_ids[0].note = code
                else:
                    if code_copy:
                        condition = [('code', '=', code_copy)]
                        account_ids = self.env['account.account'].search(condition)
                    if account_ids:
                        vals = {'code': code, 'name': description, 'note': account_ids[-1].code}
                        account_ids[-1].copy(vals)
                    else:
                        for i in [7, 6, 5, 4, 3]:
                            parent_code = (code[:i]).ljust(8, '0')
                            condition2 = [('code', '=', parent_code)]
                            account_ids = self.env['account.account'].search(condition2)
                            if account_ids:
                                vals = {'code': code, 'name': description, 'note': account_ids[0].code}
                                account_ids[0].copy(vals)
                                break
                            else:
                                account_min = str(parent_code)
                                for i in range(1, 10):
                                    account_max = str(parent_code)
                                    account_max = (account_max[:i] + str(i)).ljust(8, '0')
                                    condition3 = [('code', '>', account_min), ('code', '<=', account_max)]
                                    account_ids = self.env['account.account'].search(condition3)
                                    if account_ids:
                                        break
                                if account_ids:
                                    vals = {'code': code, 'name': description, 'note': account_ids[0].code}
                                    account_ids[0].copy(vals)
                                    break
                if not account_ids:
                    _logger.info("------- %s" % (code))



