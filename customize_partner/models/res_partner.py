# -*- coding: utf-8 -*-


from odoo import api, fields, models
import unicodedata


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def get_function(self):
        """ Save old V7 value"""
        for partner in self:
            if not partner.v7_function:
                partner.v7_function = partner.function or '?'

            function_txt = ""
            for function in partner.email_function:
                function_txt += " %s" % function.name
            partner.function = function_txt

    @api.depends('child_ids.email_function')
    def get_function_email(self):
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

            for code, email in dic_function.items():
                if not email:
                    continue
                elif not email in list(dic_email.keys()):
                    dic_email[email] = []
                if not code in dic_email[email]:
                    dic_email[email].append(code)

            for email in list(dic_email.keys()):

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
    v7_function = fields.Char('V7 save function value', compute="get_function", store=True)
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




    def button_update_partner(self):
        "Update partner after import"
        pass
