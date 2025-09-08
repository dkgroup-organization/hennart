# -*- coding: utf-8 -*-


from odoo import api, fields, models
from datetime import datetime, timedelta
import unicodedata
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_customer = fields.Boolean('Customer')
    is_supplier = fields.Boolean('Supplier')
    exclude_from_intrastat = fields.Boolean('Exclure de la déclaration DEB')

    @api.model_create_multi
    def create(self, vals_list):
        search_partner_mode = self.env.context.get('res_partner_search_mode')
        is_customer = search_partner_mode == 'customer'
        is_supplier = search_partner_mode == 'supplier'
        if search_partner_mode:
            for vals in vals_list:
                if is_customer:
                    vals['is_customer'] = True
                elif is_supplier:
                    vals['is_supplier'] = True
        return super().create(vals_list)

    @api.onchange('is_customer', 'is_supplier')
    def change_rank(self):
        """ Check minimum rank"""
        for partner in self:
            if partner.is_customer and partner.customer_rank <= 0:
                partner.customer_rank = 1
            elif not partner.is_customer:
                partner.customer_rank = 0

            if partner.is_supplier and partner.supplier_rank <= 0:
                partner.supplier_rank = 1
            elif not partner.is_supplier:
                partner.supplier_rank = 0

    def get_function(self):
        """ Save function"""
        for partner in self:
            function_txt = ""
            for function in partner.email_function:
                function_txt += " %s" % function.name
            partner.function = function_txt

    #@api.depends('child_ids.email_function')
    @api.depends('child_ids.email_function', 'email')
    def get_function_email(self):
        """Return email by function: from child if found, else fallback to partner's email"""
        for partner in self:
            if partner.is_company:
                parent = partner
            elif partner.parent_id:
                parent = partner.parent_id
            else:
                parent = partner

            default_email = parent.email or ''
            contact_function = {}

            # 1. Rassembler les e-mails des contacts enfants par fonction (sans doublons)
            for contact in parent.child_ids:
                if not contact.email:
                    continue
                for function in contact.email_function:
                    contact_function.setdefault(function.code, set()).add(contact.email)

            # 2. Pour chaque fonction, prioriser les contacts enfants sinon fallback sur l'e-mail société
            for code in [
                'email_delivery', 'email_accounting', 'email_director',
                'email_vendor', 'email_sale', 'email_quality',
                'email_department_manager', 'email_other'
            ]:
                if code in contact_function and contact_function[code]:
                    emails_str = ','.join(sorted(contact_function[code]))
                    setattr(partner, code, emails_str)
                else:
                    setattr(partner, code, default_email)



    def get_function_email_OLD(self):
        """ return email by function"""
        for partner in self:
            if partner.is_company:
                parent = partner
            elif partner.parent_id:
                parent = partner.parent_id
            else:
                parent = partner

            default_email = parent.email
            contact_function = {}
            for contact in parent.child_ids:
                if not contact.email:
                    continue
                for function in contact.email_function:
                    if function.code not in list(contact_function.keys()):
                        contact_function[function.code] = contact.email
                    else:
                        contact_function[function.code] += ',' + contact.email

            for code in ['email_delivery', 'email_accounting', 'email_director', 'email_vendor', 'email_sale',
                         'email_quality', 'email_department_manager', 'email_other']:
                setattr(partner, code, contact_function.get(code) or default_email)

    def put_function_email(self):
        """ check and create a contact for new email"""
        for partner in self:
            if not partner.is_company:
                continue
            dic_function = {
                'email_delivery': partner.email_delivery,
                'email_accounting': partner.email_accounting,
                'email_director': partner.email_director,
                'email_vendor': partner.email_vendor,
                'email_sale': partner.email_sale,
                'email_quality': partner.email_quality,
                'email_department_manager': partner.email_department_manager,
                'email_other': partner.email_other,
                }
            dic_email = {}

            for code, list_email in dic_function.items():
                if not list_email:
                    continue

                # format list_email with comas separator
                list_email = list_email.lower().strip().replace(' ', ',').replace(';', ',').replace(',,,', ',').replace(',,', ',').replace(',,', ',')
                dic_function[code] = list_email

                for email in list_email.split(','):
                    if not email in list(dic_email.keys()):
                        dic_email[email] = []
                    if not code in dic_email[email]:
                        dic_email[email].append(code)

            for email in list(dic_email.keys()):
                if not email:
                    continue

                condition = [('parent_id', '=', partner.id), ('email', '=', email)]
                contact_ids = self.search(condition)
                if not contact_ids and email == partner.email:
                    continue

                if not contact_ids:
                    contact_ids = contact_ids.create({
                        'parent_id': partner.id,
                        'name': email,
                        'email': email,
                    })
                function_ids = self.env['res.partner.function'].search([('code', 'in', dic_email[email])])
                contact_vals = {'email_function': [(6, 0, function_ids.ids)]}
                contact_ids.write(contact_vals)
            partner.update(dic_function)

    @api.onchange('name')
    def onchange_name(self):
        """ Only ASCII and upper char """
        only_ascii = unicodedata.normalize('NFD', self.name or '').encode('ascii', 'ignore')
        self.name = only_ascii.upper()

    # Sale data
    sale_area = fields.Many2one('res.partner.area', string="Sale area")
    discount_weight = fields.Float('Discount weight (kg)')
    typology_id = fields.Many2one('res.partner.typology', string='Typology')


    # email data
    v7_function = fields.Char('V7 save function value')
    function = fields.Char('Function', compute="get_function")
    email_delivery = fields.Char('Email delivery', compute='get_function_email', inverse="put_function_email", store=True)
    email_accounting = fields.Char('Email accounting', compute='get_function_email', inverse="put_function_email", store=True)
    email_director = fields.Char('Email director', compute='get_function_email', inverse="put_function_email", store=True)
    email_vendor = fields.Char('Email vendor', compute='get_function_email', inverse="put_function_email", store=True)
    email_sale = fields.Char('Email Sale', compute='get_function_email', inverse="put_function_email", store=True)
    email_quality = fields.Char('Email quality', compute='get_function_email', inverse="put_function_email", store=True)
    email_department_manager = fields.Char('Email department manager', compute='get_function_email', inverse="put_function_email", store=True)
    email_other = fields.Char('Email other', compute='get_function_email', inverse="put_function_email", store=True)
    email_function = fields.Many2many('res.partner.function', string="Functions")

    # preparation data
    print_picking = fields.Boolean('Print Delivery', default=True, help="Print Delivery at the end of preparation")
    print_picking2 = fields.Boolean('Print Delivery with price', default=True, help="Print Delivery with price at the end of preparation")

    print_invoice = fields.Boolean('Print Invoice', default=True, help="Print Invoice at the end of preparation")
    paper_invoice = fields.Boolean('Paper invoice by mail', default=False, help="Send paper invoice by physical mail")
    email_invoice = fields.Boolean('Automatic email pdf invoice', default=False)
    #email_picking = fields.Boolean('Automatic email pdf picking', default=False)

    invoice_auto = fields.Boolean('Automatic validation', default=True,
            help="The invoice is automatically validated at the end of preparation")
    no_invoice_auto = fields.Boolean('Manual Invoice', default=False,
            help="The invoice is not automaticaly created, so it's possible to group the delivery in one invoice or don't invoice some partner")

    # Carrier and export
    incoterm_id = fields.Many2one('account.incoterms', 'Incoterm',
                                  help="International Commercial Terms are a series of predefined commercial terms used in international transactions.")
    incoterm_contact_id = fields.Many2one('res.partner', string="Incoterm contact")
    incoterm_city = fields.Char("Incoterm City")
    carrier_zone = fields.Char("Carrier zone")
    oeri_code = fields.Char("OERI code")
    label_forced = fields.Boolean('label all packages', default=False)
    label_all_product = fields.Boolean('label all products', default=False)
    label_needed = fields.Boolean('label according to product sheet', default=False)
    hour_delivery = fields.Float('Hour delivery', default=0.0)
    payment_method_id = fields.Many2one("account.payment.method", store=True, index=True, string="Payment method")

    def button_update_partner(self):
        "Update partner after import"
        pass
