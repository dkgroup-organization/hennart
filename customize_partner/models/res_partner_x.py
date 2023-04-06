# -*- coding: utf-8 -*-


from odoo import api, fields, models


class ResPartnerFunction(models.Model):
    """ list the function defined for partner """
    _name = "res.partner.function"
    _description = "Partner function list"

    name = fields.Char("name", translate=True)
    code = fields.Char("code")

    def init_value(self):
        """ default value"""
        for code in ['email_delivery', 'email_accounting', 'email_director', 'email_vendor', 'email_sale',
                     'email_quality', 'email_department_manager', 'email_other']:
            function_ids = self.search([('code', '=', code)])
            if not function_ids:
                self.create({'code': code, 'name': code})


class ResPartnerArea(models.Model):
    """ Sale area of the partner """
    _name = "res.partner.area"
    _description = "Sale area"

    name = fields.Char("name")


class ResPartnerTypology(models.Model):
    """ Sale typology of the partner """
    _name = "res.partner.typology"
    _description = "Partner typology"

    name = fields.Char("name")
