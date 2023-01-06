# See LICENSE file for full copyright and licensing details.

import time
import logging
# import threading
from odoo import api, fields, models
from odoo.models import MAGIC_COLUMNS
from . import odoo_proxy
from . import synchro_data

OPTIONS_OBJ = synchro_data.OPTIONS_OBJ

_logger = logging.getLogger(__name__)


class BaseSynchroObjDepend(models.Model):
    """Class many2many hierarchy depend on object."""
    _name = "synchro.obj.depend"
    _description = "Relation order between object"

    name = fields.Char('not used')
    child_id = fields.Many2one('synchro.obj', 'child')
    parent_id = fields.Many2one('synchro.obj', 'parent')


class BaseSynchroObj(models.Model):
    """Class to store the migration configuration by object."""
    _name = "synchro.obj"
    _description = "synchro.obj"
    _order = 'sequence'

    name = fields.Char(string='Name', required=True)
    auto_create = fields.Boolean(string='Create')
    auto_update = fields.Boolean(string='Update')
    auto_search = fields.Boolean(string='Search')
    domain = fields.Char(string='Remote Domain', required=True, default='[]')
    search_field = fields.Char(string='Search field', default="name",
                               help='define a search field if it is not name, example: code, default_code...')
    server_id = fields.Many2one('synchro.server', string='Server', required=True)
    model_id = fields.Many2one('ir.model', string='Object to synchronize', required=True, ondelete='cascade')
    model_name = fields.Char('Remote Object name', required=True)
    sequence = fields.Integer('Sequence')
    level = fields.Integer('level')
    active = fields.Boolean('Active', default=True)
    synchronize_date = fields.Datetime('Latest Synchronization')
    line_id = fields.One2many('synchro.obj.line', 'obj_id', string='IDs Affected')
    avoid_ids = fields.One2many('synchro.obj.avoid', 'obj_id', string='All fields.')
    field_ids = fields.One2many('synchro.obj.avoid', 'obj_id', domain=[('synchronize', '=', True)],
                                string='Fields to synchronize')
    child_ids = fields.Many2many(
        comodel_name='synchro.obj',
        relation='synchro_obj_depend',
        column1='parent_id',
        column2='child_id',
        string='Childs',
        )

    note = fields.Html("Notes")

    default_value = fields.Text("Defaults values")
    sync_limit = fields.Integer("Load limite by cron", default=1)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('manual', 'Manual'),
        ('auto', 'Auto'),
        ('synchronise', 'Synchronise'),
        ('cancel', 'Cancelled')
        ], string='State', index=True, default='draft')

    def unlink(self):
        "unlink line before"
        for obj in self:
            obj.field_ids.unlink()
            obj.avoid_ids.unlink()
            obj.line_id.unlink()

        ret = super().unlink()
        return ret

    def get_default_value(self):
        " Use default_get"
        for obj in self:
            list_fields = []
            for field_line in obj.field_ids:
                list_fields.append(field_line.field_id.name)
            values = obj.model_id.default_get(list_fields)
            obj.default_value = "%s" % (values)

    @api.onchange('model_id')
    def onchange_field(self):
        "return the name"
        self.model_name = self.model_id.model or ''
        if not self.name:
            self.name = self.model_id.model or ''

    def get_map_fields(self):
        """ Return a mapping field to do by odoo object, it's a pre-configuration by version
            see synchro_data.py for information
        """
        self.ensure_one()
        if self.server_id.server_version:
            return synchro_data.MAP_FIELDS.get(self.server_id.server_version, {})
        else:
            return {}

    def get_default_option(self):
        """ Return a default value field by odoo object, it's a pre-configuration by version
            see synchro_data.py for information
        """
        self.ensure_one()
        return synchro_data.OPTIONS_OBJ.get(self.model_id.model, {})

    def get_except_fields(self):
        """ Return a default value field by odoo object, it's a pre-configuration by version
            see synchro_data.py for information
        """
        self.ensure_one()
        options = synchro_data.OPTIONS_OBJ.get(self.model_id.model, {})
        return options.get('except_fields', [])

    def update_field(self):
        "update the list of local field"
        for obj in self:
            # load preconfiguration mapping fields, see synchro_data.py
            dic_option = obj.get_default_option()
            for name_field in list(dic_option.keys()):
                if hasattr(obj, name_field):
                    setattr(obj, name_field, dic_option[name_field])

            map_fields = obj.get_map_fields()
            check_avoid_ids = self.env['synchro.obj.avoid']

            for field_rec in obj.model_id.field_id:
                if field_rec.store and field_rec.name not in MAGIC_COLUMNS:

                    name_VX = field_rec.name
                    if obj.name in list(map_fields.keys()):
                        if name_VX in list(map_fields[obj.name].keys()):
                            name_VX = map_fields[obj.name][name_VX]
                    
                    condition = [('obj_id', '=', obj.id), ('field_id', '=', field_rec.id)]
                    avoid_ids = self.env['synchro.obj.avoid'].search(condition)
                    
                    if not avoid_ids:
                        field_value = {
                            'obj_id': obj.id,
                            'field_id': field_rec.id,
                            'name': name_VX,
                            }
                        check_avoid_ids |= self.env['synchro.obj.avoid'].create(field_value)
                    else:
                        check_avoid_ids |= avoid_ids
            (obj.avoid_ids - check_avoid_ids).unlink()

    def update_remote_field(self, except_fields=[]):
        "update the field who can be synchronized"

        for obj in self:
            remote_odoo = odoo_proxy.RPCProxy(obj.server_id)
            remote_fields = remote_odoo.get(self.model_name).fields_get()
            except_fields = obj.get_except_fields()

            for local_field in obj.avoid_ids | obj.field_ids:
                if local_field.name in list(remote_fields.keys()):
                    local_field.check_remote = True
                    local_field.remote_type = remote_fields[local_field.name]['type']
                    if local_field.remote_type not in ['one2many']:
                        local_field.synchronize = True
                    if local_field.name in except_fields:
                        local_field.synchronize = False

    def unlink_mapping(self):
        for obj in self:
            obj.line_id.unlink()

    def load_remote_record(self, limit=50):
        "Load remote record"
        limit = self.env.context.get('limit', 0) or limit

        for obj in self:
            already_ids = obj.get_synchronazed_remote_ids()
            domain = [('id', 'not in', already_ids)]

            remote_domain = eval(obj.domain)
            if remote_domain:
                domain += remote_domain

            remote_ids = obj.remote_search(domain)
            remote_ids.sort()

            if limit and limit < 0:
                pass
            elif limit and len(remote_ids) > limit:
                remote_ids = remote_ids[:limit]

            remote_values = obj.remote_read(remote_ids)
            print('\n', remote_values)
            if obj.model_id.model == 'product.product':
                obj.load_remote_product(remote_values)
            else:
                obj.write_local_value(remote_values)

            if obj.model_id.model == 'product.template':
                obj.load_remote_product_template(remote_values)

            obj.synchronize_date = fields.Datetime.now()

    def load_remote_user(self, remote_values={}):
        """ exception for user, create partner and user in the same time"""
        self.ensure_one()
        if self.model_id.model == 'res.users':
            for remote_value in remote_values:
                remote_partner_id = remote_value.get('partner_id')
                partner_obj = self.server_id.get_obj('res.partner')
                partner_local_id = partner_obj.get_local_id(remote_partner_id[0])

    def load_remote_product(self, remote_values={}):
        """ exception for product, create template and variant in the same time"""
        self.ensure_one()

        if self.model_id.model == 'product.product':
            for remote_value in remote_values:
                remote_tmpl_id = remote_value.get('product_tmpl_id')
                remote_id = remote_value.get('id')

                if self.get_local_id(remote_id, no_create=True, no_search=True):
                    continue
                elif self.auto_create or self.env.context.get('auto_create'):
                    product_tmpl_obj = self.server_id.get_obj('product.template')
                    product_tmpl_local_id = product_tmpl_obj.get_local_id(remote_tmpl_id[0])
                    product_tmpl_local = self.env['product.template'].browse(product_tmpl_local_id)
                    local_product_id = product_tmpl_local.product_variant_id.id

                    condition = [
                        ('remote_id', '=', remote_id),
                        ('obj_id', '=', self.id)]
                    local_ids = self.env['synchro.obj.line'].search(condition)
                    if local_ids:
                        if local_ids[0].local_id != local_product_id:
                            local_ids[0].local_id = local_product_id
                    else:
                        vals_line = {
                            'obj_id': self.id,
                            'remote_id': remote_id,
                            'local_id': local_product_id}
                        local_ids.create(vals_line)
            self.write_local_value(remote_values)

    def load_remote_product_template(self, remote_values={}):
        """ exception for product, create template and variant in the same time"""
        self.ensure_one()

        if self.model_id.model == 'product.template':
            for remote_value in remote_values:
                remote_tmpl_id = remote_value.get('id')
                domain = [('product_tmpl_id', '=', remote_tmpl_id)]
                product_obj = self.server_id.get_obj('product.product')
                remote_ids = product_obj.remote_search(domain)
                remote_values2 = product_obj.remote_read(remote_ids)
                product_obj.load_remote_product(remote_values2)


    def check_childs(self):
        "check the child of this object"
        for obj in self:
            object_list = []
            child_ids = self.env['synchro.obj']
            for rec_field in obj.field_ids:
                if rec_field.field_id.ttype in ['many2one', 'many2many']:
                    obj_name = rec_field.field_id.relation
                    condition = [('model_id.model', '=', obj_name),
                                 ('server_id', '=', obj.server_id.id)]
                    obj_ids = self.search(condition)
                    child_ids |= obj_ids
                    if not obj_ids:
                        object_list.append(obj_name)
            child_ids |= obj.server_id.create_obj(object_list)
            obj.write({'child_ids': [(6, 1, child_ids.ids)]})

    def action_order(self):
        """ Order by recursive dependence """

        def deeper_sequence(obj, res):
            """ check if there are child, if not start sequence = 100, else add 100 by level"""
            # obj Already checked
            if obj in res:
                return res

            if not obj.child_ids:
                obj.check_childs()

            res |= obj

            if not obj.child_ids and obj.level != 1:
                obj.level = 1
            else:
                for obj_child in obj.child_ids:
                    res |= deeper_sequence(obj_child, res=res)

                obj.level = max(obj.child_ids.mapped('level') or [0]) + 1

            return res

        res = self.env['synchro.obj']
        self.level = 0
        for obj in self:
            res = deeper_sequence(obj, res)

        for obj in self:
            obj.sequence = 1000 * obj.level + len(obj.child_ids)

    def remote_read(self, remote_ids, remote_fields=[]):
        "read the value of the remote object filter on remote_ids"
        self.ensure_one()
        remote_odoo = odoo_proxy.RPCProxy(self.server_id)
        remote_fields = remote_fields or self.field_ids.mapped('name')
        remote_value = remote_odoo.get(self.model_name).read(remote_ids, remote_fields)
        return remote_value

    def remote_search(self, domain=[]):
        "read the value of the remote object filter on remote_ids"
        self.ensure_one()
        remote_odoo = odoo_proxy.RPCProxy(self.server_id)
        remote_obj = remote_odoo.get(self.model_name)
        remote_domain = eval(self.domain)
        remote_ids = remote_obj.search(remote_domain + domain)
        return remote_ids

    def read_groupby_ids(self, groupby_field, groupby_domain=[]):
        "Return list of remote ids by domain filter"
        self.ensure_one()
        remote_odoo = odoo_proxy.RPCProxy(self.server_id)
        remote_obj = remote_odoo.get(self.model_name)
        remote_domain = eval(self.domain) + groupby_domain

        read_groupby = remote_obj.read_group(remote_domain, [groupby_field], [groupby_field])
        response = []
        for item in read_groupby:
            if item.get(groupby_field):
                remote_id = item[groupby_field][0]
                response.append(remote_id)
        return response

    def default_search_field(self):
        "return the default search field to do mapping"
        self.ensure_one()

        if self.search_field:
            search_field = [self.search_field]
        else:
            search_field = ['name']
        return search_field

    def search_local_id(self, remote_ids):
        "get the local id associated with remote_ids, save in obj.line"
        # Return a dic {remote_id: local_id, ...}
        self.ensure_one()
        res = {}
        # Get the significative search field like code, name... and read the remote value
        search_fields = self.default_search_field()
        if 'name' in search_fields:
            remote_values = self.remote_read(remote_ids, search_fields)
        else:
            # Add name only to have human description
            remote_values = self.remote_read(remote_ids, search_fields + ['name'])

        for remote_value in remote_values:
            remote_id = remote_value['id']
            local_id = False
            res[remote_id] = False

            # Construct the condition from the search_fields and search
            condition = []
            description = ''
            for search_field in search_fields:
                search_value = remote_value.get(search_field)
                description = '%s ' % search_value + description
                condition.append((search_field, '=', search_value))

            local_ids = self.env[self.model_id.model].search(condition)
            local_id = local_ids and (len(local_ids) == 1) and local_ids[0].id or False

            line_condition = [
                    ('obj_id', '=', self.id),
                    ('remote_id', '=', remote_id)]
            obj_line_ids = self.env['synchro.obj.line'].search(line_condition)
            mapping_line = obj_line_ids and obj_line_ids[0] or obj_line_ids

            if not mapping_line:
                mapping_vals = {
                        'local_id': False,
                        'remote_id': remote_id,
                        'description': description,
                        'obj_id': self.id
                        }
                mapping_line = obj_line_ids.create(mapping_vals)

            if local_id:
                res[remote_id] = local_id
                mapping_line.local_id = local_id

        return res

    def get_void_local_ids(self):
        "return id list of line with no local_id"
        self.ensure_one()
        condition = [('local_id', '=', 0), ('obj_id', '=', self.id)]
        local_ids = self.env['synchro.obj.line'].search(condition)
        res = local_ids.mapped('remote_id')
        return res

    def get_remote_id(self, local_id):
        "Get remote id if exist"
        self.ensure_one()
        condition = [('local_id', '=', local_id), ('obj_id', '=', self.id)]
        remote_ids = self.env['synchro.obj.line'].search(condition)
        if remote_ids:
            return remote_ids[0].remote_id
        else:
            return False

    def get_local_id(self, remote_id, no_create=False, no_search=False, check_local_id=True):
        "return the local_id associated with the remote_id"
        self.ensure_one()
        condition = [('remote_id', '=', remote_id), ('obj_id', '=', self.id)]
        local_ids = self.env['synchro.obj.line'].search(condition)

        if not local_ids:
            self.env['synchro.obj.line'].create({
                'local_id': 0,
                'remote_id': remote_id,
                'obj_id': self.id,
                'description': '?',
                'update_date': fields.Datetime.now(),
                })

        for line in local_ids:
            if line.error:
                return False

        if check_local_id:
            # Check if there is a local object pointing by these ids
            checking_local_ids = self.env['synchro.obj.line']
            for checking_local_id in local_ids:
                try:
                    if self.env[self.model_id.model].browse(checking_local_id.local_id):
                        checking_local_ids |= checking_local_id
                except:
                    checking_local_id.error = "local Deleting"

            local_ids = checking_local_ids

        if local_ids:
            if local_ids[0].local_id:
                return local_ids[0].local_id
            else:
                return False
        else:
            if self.auto_search and not no_search:
                result = self.search_local_id([remote_id])
                if result.get(remote_id):
                    return result[remote_id]

            if self.auto_create and not no_create:
                remote_vals = self.remote_read([remote_id])
                if remote_vals:
                    self.write_local_value(remote_vals)
                    return self.get_local_id(remote_id, no_create=True, no_search=True, check_local_id=True)
                else:
                    return False
            else:
                return False

    def get_local_value(self, remote_value):
        """get local database the values for mani2x field
            values: [{'id': 1, 'name': 'My object name', ....}, {'id': 2, ...}]
            the id field is the remote id and must be set
        """
        self.ensure_one()
        local_value = {}

        for sync_field in self.field_ids:
            if sync_field.field_id.ttype in ['many2one']:
                if remote_value.get(sync_field.name):
                    many2_remote_id = remote_value.get(sync_field.name)[0]
                    many2_obj = self.server_id.get_obj(sync_field.field_id.relation)
                    many2_local_id = many2_obj.get_local_id(many2_remote_id)
                    if many2_local_id:
                        field_name = sync_field.field_id.name
                        local_value.update({field_name: many2_local_id})

            elif sync_field.field_id.ttype in ['many2many']:
                many2_remote_ids = remote_value.get(sync_field.name)
                if many2_remote_ids:
                    many2_obj = self.server_id.get_obj(sync_field.field_id.relation)
                    many2_local_ids = []
                    for many2_remote_id in many2_remote_ids:
                        many2_local_id = many2_obj.get_local_id(many2_remote_id)
                        if many2_local_id:
                            many2_local_ids.append(many2_local_id)
                    if many2_local_ids:
                        field_name = sync_field.field_id.name
                        local_value.update({field_name: [(6, 0, many2_local_ids)]})

            elif sync_field.field_id.ttype in ['date']:
                field_value = remote_value.get(sync_field.name)
                if isinstance(field_value, str):
                    field_value = fields.Date.from_string(field_value)
                field_name = sync_field.field_id.name
                local_value.update({field_name: field_value})

            else:
                field_value = remote_value.get(sync_field.name)
                field_name = sync_field.field_id.name
                local_value.update({field_name: field_value})

        return local_value

    def exception_value_write(self, remote_value):
        "hook exception for value"
        self.ensure_one()

        if self.model_name == 'res.partner':
            type_value = remote_value.get('type')
            if type_value and type_value not in ['invoice', 'contact', 'delivery', 'other']:
                remote_value['type'] = 'contact'

        return remote_value

    def exception_value_create(self, remote_value):
        "hook exception for value"
        self.ensure_one()
        if self.model_name == 'res.partner' and not remote_value.get('name'):
            remote_value['name'] = '?'

        remote_value = self.exception_value_write(remote_value)
        return remote_value

    def exception_value(self, remote_value):
        "hook exception for value"
        # TODO: create a data mapping and remove this
        self.ensure_one()

        if self.model_name == 'hr_timesheet.sheet':
            if not remote_value.get('review_policy'):
                remote_value['review_policy'] = 'hr'

        elif self.model_name == 'res.partner':
            type_value = remote_value.get('type')
            if type_value and type_value not in ['invoice', 'contact', 'delivery', 'private', 'other']:
                remote_value['type'] = 'contact'

        elif self.model_name == 'sale.order':

            state = remote_value.get('state', '')
            if state in ['draft', 'sent', 'sale', 'done', 'cancel']:
                pass
            elif state in ['waiting_date', 'confirmed', 'progress', 'manual', 'shipping_except', 'invoice_except']:
                remote_value['state'] = 'sent'
            else:
                remote_value['state'] = 'draft'

        elif self.model_name == 'purchase.order':
            state = remote_value.get('state', '')
            if state in ['draft', 'sent', 'to_approve', 'sale', 'done', 'cancel']:
                pass
            elif state in ['confirmed']:
                remote_value['state'] = 'to_approve'
            elif state in ['waiting_date', 'confirmed', 'progress', 'manual', 'shipping_except', 'invoice_except']:
                remote_value['state'] = 'done'
            else:
                remote_value['state'] = 'draft'

        return remote_value

    def write_local_value(self, remote_values, commit=True):
        """write in local database the values, the values is a list of dic vals
            values: [{'id': 1, 'name': 'My object name', ....}, {'id': 2, ...}]
            the id field is the remote id and must be set
        """
        self.ensure_one()

        for remote_value in remote_values:
            remote_id = remote_value.get('id')
            local_id = self.get_local_id(remote_id, no_create=True)
            error = False

            if local_id and (self.auto_update or self.env.context.get('auto_update')):
                # Write
                remote_value = self.exception_value_write(remote_value)
                local_value = self.get_local_value(remote_value)
                browse_obj = self.env[self.model_id.model].browse(local_id)
                try:
                    browse_obj.sudo().with_context(synchro=True).write(local_value)
                except Exception as e:
                    error = "%s" % e

            elif self.auto_create or self.env.context.get('auto_create'):
                # Create
                remote_value = self.exception_value_create(remote_value)
                local_value = self.get_local_value(remote_value)
                _logger.info("create: %s: %s" % (self.model_id.model, local_value))
                try:
                    new_obj = self.env[self.model_id.model].sudo().with_context(synchro=True).create(local_value)
                    local_id = new_obj.id

                except Exception as e:
                    local_id = 0
                    error = "%s" % e

            condition = [('remote_id', '=', remote_id), ('obj_id', '=', self.id)]
            local_ids = self.env['synchro.obj.line'].search(condition)
            local_ids.write({
                    'local_id': local_id,
                    'description': '%s' % (remote_value.get('name', '???')),
                    'update_date': fields.Datetime.now(),
                    'error': error})

            if commit:
                self.env.cr.commit()

    @api.model
    def get_synchronazed_remote_ids(self):
        "return all remote id"
        self.ensure_one()
        line_ids = self.env['synchro.obj.line'].search([('obj_id', '=', self.id)])
        return line_ids.mapped('remote_id')

    def update_synchronize_date(self):
        """ Update the value of synchronize date"""
        for obj in self:
            condition = [('error', '=', False), ('obj_id', '=', obj.id)]
            line_ids = obj.line_id.search(condition, limit=1, order='update_date')
            if line_ids:
                obj.synchronize_date = line_ids[0].update_date

    def update_line(self):
        """ Update the values by checking write_date on remote object"""
        self.update_synchronize_date()
        new_date = fields.Datetime.now()
        for obj in self:
            condition = [('write_date', '>', obj.synchronize_date)]
            last_obj_writing_ids = obj.remote_search(condition)
            for line in obj.line_id:
                if line.remote_id not in last_obj_writing_ids:
                    line.update_date = new_date
                elif obj.auto_update:
                    line.update_values()
        self.update_synchronize_date()



