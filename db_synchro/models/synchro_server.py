# See LICENSE file for full copyright and licensing details.

import logging
from odoo import api, fields, models, _
from . import synchro_data
from datetime import datetime, timedelta

OPTIONS_OBJ = synchro_data.OPTIONS_OBJ


class BaseSynchroServer(models.Model):
    """Class to store the information regarding server."""
    _name = "synchro.server"
    _description = "Synchronized server"

    name = fields.Char('Server name', required=True)
    server_protocol = fields.Selection(
        [('http', 'HTTP'),
         ('https', 'HTTPS'),
         ('https_1', 'HTTPS TLSv1'),
         ('https_1_1', 'HTTPS TLSv1_1'),
         ('https_1_2', 'HTTPS TLSv1_2'),
         ],
        string='Protocol', default='http', required=True)
    server_url = fields.Char('Server URL', required=True)
    server_port = fields.Integer('Server Port', required=True, default=8069)
    server_db = fields.Char('Server Database', required=True)
    login = fields.Char('User Name', required=True)
    password = fields.Char('Password', required=True)
    obj_ids = fields.One2many('synchro.obj', 'server_id')
    server_version = fields.Selection(
        [('6', 'Version 6.1'),
         ('7', 'Version 7.0'),
         ('8', 'Version 8.0'),
         ('9', 'Version 9.0'),
         ('10', 'Version 10.0'),
         ('11', 'Version 11.0'),
         ('12', 'Version 12.0'),
         ('13', 'Version 13.0'),
         ('14', 'Version 14.0'),
         ('15', 'Version 15.0'),
         ('16', 'Version 16.0'),
         ],
        string='Version', default='16', required=True)

    def get_obj(self, model_name=''):
        "return the object with model_name"
        self.ensure_one()
        obj_condition = [('model_id.model', '=', model_name),
                         ('server_id', '=', self.id)]
        obj_ids = self.env['synchro.obj'].search(obj_condition)

        if not obj_ids:
            obj_ids = self.create_obj([model_name])
        elif len(obj_ids) > 1:
            for state in ['synchronise', 'auto', 'manual', 'draft']:
                for obj_test in obj_ids:
                    if obj_test.state == state:
                        return obj_test

        return obj_ids

    def create_obj(self, object_list):
        "create object to synchronyze"
        res = self.env['synchro.obj']
        for server in self:
            for model_name in object_list:
                if not server.obj_ids.search([
                                    ('model_id.model', '=', model_name),
                                    ('server_id', '=', server.id)]):

                    model_condition = [('model', '=', model_name)]
                    model_ids = self.env['ir.model'].search(model_condition)
                    if model_ids:
                        obj_vals = {
                            'name': model_name,
                            'model_name': model_name,
                            'server_id': server.id,
                            'sequence': model_ids[0].id,
                            'model_id': model_ids[0].id,
                            }
                        new_obj = self.env['synchro.obj'].create(obj_vals)

                        options = OPTIONS_OBJ.get(model_name, {})
                        for field_name in list(options.keys()):
                            if hasattr(new_obj, field_name):
                                setattr(new_obj, field_name, options[field_name])

                        new_obj.update_field()
                        res |= new_obj
                    else:
                        raise Warning(_('This object is not available: %s' % (model_name)))
        return res

    def remote_company_ids(self):
        "initialized domain for remote company, used when there are multicompany"
        # Domain company
        self.ensure_one()
        obj_company_ids = self.obj_ids.search([
                    ('model_id.model', '=', 'res.company'),
                    ('server_id', '=', self.id)])

        if not obj_company_ids:
            obj_company_ids = self.migrate_obj('res.company')
            obj_company_ids.get_local_id(1)

        company_ids = []
        for obj in obj_company_ids:
            for line in obj.line_id:
                if line.local_id:
                    company_ids.append(line.remote_id)

        return company_ids

    def migrate_obj(self, obj_name, options={}):
        "migrate standard objet"
        self.ensure_one()
        options = options or OPTIONS_OBJ.get(obj_name, {})
        obj_obj = self.get_obj(obj_name)

        for field_name in list(options.keys()):
            if hasattr(obj_obj, field_name):
                setattr(obj_obj, field_name, options[field_name])

        obj_obj.check_childs()
        return obj_obj

    def migrate_base(self):
        "migrate base object"
        self.ensure_one()

        company_obj = self.migrate_obj('res.company')
        self.migrate_obj('ir.module.module')
        self.migrate_obj('res.currency')
        bank_obj = self.migrate_obj('res.bank')
        self.migrate_obj('res.partner.bank')
        self.migrate_obj('res.groups')

        remote_company_ids = self.remote_company_ids()
        company_values = company_obj.remote_read(remote_company_ids)
        company_obj.write_local_value(company_values)

        bank_ids = bank_obj.remote_search([])
        for bank_id in bank_ids:
            bank_obj.get_local_id(bank_id)
            
    def migrate_stock(self):
        "migrate stock quant"
        for server in self.search([]):

            obj_ids = server.obj_ids.search([('model_name', '=', 'stock_product_by_location_tracking_prodlot')])
            for obj in obj_ids:
                obj.line_id.unlink()

            quants = self.env['stock.quant'].search([])
            for quant in quants:
                quant.quantity = 0
                quant.sudo().unlink()

            if len(obj_ids) == 1:
                obj_ids[0].load_remote_record(limit=-1)

            update_lot_ids = self.env['stock.lot'].search([('quant_ids', '!=', False)])
            for lot in update_lot_ids:
                lot.expiration_date = lot.life_date or lot.use_date or lot.removal_date or lot.alert_date

            update_lot_ids = self.env['stock.lot'].search([('use_expiration_date', '=', False)])
            update_lot_ids.write({'use_expiration_date': True})

    def migrate_partner(self, limit=50):
        """ partner migration, look after active and used partner, don't load unused partner"""

        for server in self:
            partner_obj = server.get_obj('res.partner')
            if not partner_obj or partner_obj.state != 'synchronise':
                continue
            remote_company_ids = server.remote_company_ids()
            partner_loading_ids = partner_obj.get_synchronazed_remote_ids()
            partner_remote_ids = []
            partner_obj.auto_create = True
            partner_obj.auto_search = False

            list_model = ['res.users', 'sale.order', 'purchase.order', 'account.move']

            for model_name in list_model:
                if self.env['ir.model'].search([('model', '=', model_name)]):
                    # search the partner used
                    model_obj = server.get_obj(model_name)
                    groupby_domain = [('company_id', 'in', remote_company_ids)]

                    if hasattr(self.env[model_obj.model_id.model], 'active'):
                        groupby_domain.append(('active', '=', True))
                    partner_search_ids = model_obj.read_groupby_ids('partner_id', groupby_domain)

                    # limit the number of load
                    for partner_id in partner_search_ids:
                        if partner_id not in partner_loading_ids and partner_id not in partner_remote_ids:
                            partner_remote_ids.append(partner_id)

                        if limit and len(partner_remote_ids) > limit:
                            break

            obj_vals = partner_obj.remote_read(partner_remote_ids)
            partner_obj.write_local_value(obj_vals)

            remote_child_ids = partner_obj.remote_search([('parent_id', 'in', partner_loading_ids),
                                                          ('id', 'not in', partner_loading_ids)])

            obj_vals = partner_obj.remote_read(remote_child_ids)
            partner_obj.write_local_value(obj_vals)

    @api.model
    def cron_migrate(self):
        """ Scheduled migration"""
        for server in self.search([]):
            obj_ids = server.obj_ids.search([('state', '=', 'synchronise')], order='sequence')
            for obj in obj_ids:
                if obj.model_id.model in ["res.partner"]:
                    server.migrate_partner()
                else:
                    obj.load_remote_record()

    @api.model
    def cron_update(self):
        """ Schedule update, check if older line have to be updated """
        for server in self.search([]):
            obj_ids = server.obj_ids.search([('state', 'in', ['synchronise', 'auto']),
                                             ('auto_update', '=', True)], order='sequence')
            for obj in obj_ids:
                obj.get_last_update()

    @api.model
    def cron_migrate_invoices(self):
        """ Scheduled migration for invoices"""
        for server in self.search([]):
            obj_ids = server.obj_ids.search([('model_name', '=', 'account.invoice')])
            for obj in obj_ids:
                obj.load_remote_record()

    @api.model
    def cron_valid_invoice(self, limit=100):
        """ Scheduled migration for invoices"""

        # Create all account_move_line_lot
        sql = """
        insert into account_move_line_lot (account_move_line_id, lot_id, uom_qty, quantity, weight, state) 
        select aml.id, aml.prodlot_id, aml.uom_qty, aml.quantity, aml.weight, 'manual'
        from account_move_line aml
        left join account_move_line_lot amll on aml.id = amll.account_move_line_id
        where amll.state is null;
        """
        self.env.cr.execute(sql)
        sql = """
        update stock_lot set expiration_date = COALESCE(use_date, alert_date, removal_date, date) 
        where expiration_date is null;
        """
        self.env.cr.execute(sql)

        self.env.cr.commit()
        self.env['stock.lot'].invalidate_recordset(['expiration_date'])
        self.env['account.move.line'].invalidate_model()

        # Start update
        started_delay = datetime.now() - timedelta(minutes=10)
        job_ids = self.env['queue.job'].search([('state', '=', 'started'),
                                                ('date_started', '<', started_delay)])
        job_ids.button_done()

        requeue_delay = datetime.now() - timedelta(hours=1)
        job_ids = self.env['queue.job'].search([('state', '=', 'pending'),
                                                ('date_created', '<', requeue_delay)])
        job_ids.button_done()
        job_ids = self.env['queue.job'].search([('state', 'in', ['pending', 'started'])])

        nb_invoice = 0
        pool_invoice = 5 * limit
        synchro_line_ids = self.env['synchro.obj.line']

        if len(job_ids) < pool_invoice:
            while nb_invoice < pool_invoice:

                if not synchro_line_ids:
                    synchro_line_ids = self.env['synchro.obj.line'].search(
                        [('obj_id.model_id.model', '=', 'account.move'), ('local_id', '>', 0)],
                        order='update_date asc', limit=5*limit)

                for line in synchro_line_ids:
                    invoice = self.env['account.move'].browse(line.local_id)

                    if invoice.piece_comptable and invoice.state == 'draft' and invoice.fiscal_position_id:
                        invoice.with_delay().action_valide_imported()
                        nb_invoice += 1

                    line.update_date = fields.Datetime().now()
                    synchro_line_ids -= line

                    if nb_invoice >= pool_invoice:
                        break
