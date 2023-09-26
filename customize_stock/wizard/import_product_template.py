# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
import base64
import time
import logging
import datetime
from dateutil.relativedelta import relativedelta
from odoo.addons.web.controllers.export import ExportXlsxWriter

FORMAT_DATE = [('ddmmyy', 'ddmmyy'), ('dd/mm/yyyy', 'dd/mm/yyyy'), ('yyyy-mm-dd', 'yyyy-mm-dd'),
               ('yyyymmdd', 'yyyymmdd'), ('mm/dd/yyyy', 'mm/dd/yyyy')]
MIN_COLUMN = 2
ANNEE = int(time.strftime('%Y'))
FORMAT_ANNEE = [(str(ANNEE), str(ANNEE)), (str(ANNEE + 1), str(ANNEE + 1))]

_logger = logging.getLogger(__name__)
try:
    import xlrd

    try:
        from xlrd import xlsx
    except ImportError:
        _logger.info("xlsx None")
        xlsx = None
except ImportError:
    _logger.info("xlrd None")
    xlrd = xlsx = None


class ImportPriceList(models.TransientModel):
    _name = 'import.product.template'
    _description = "Import product template"

    file = fields.Binary('Import File')
    name = fields.Char('Name')

    file_name = fields.Char('File name')

    def action_valide(self):
        self.ensure_one()
        if not self.file:
            raise UserError(_("Please select a file to import."))

        # Charger le fichier Excel depuis le champ binaire
        book = xlrd.open_workbook(file_contents=base64.b64decode(self.file))
        sheet = book.sheet_by_index(0)
        header = {}

        for i_col in range(sheet.ncols):
            header_name = sheet.cell_value(0, i_col)
            header[header_name] = i_col

        # Parcourir les lignes du fichier Excel
        for row in range(1, sheet.nrows):
            product_code = str(sheet.cell_value(row, header.get('default_code')))
            raise UserError(product_code)
            if not product_code:
                continue  # Ignorer les lignes sans default_code

            # Rechercher le produit par default_code
            product = self.env['product.template'].search([('default_code', '=', product_code)])

            # Créer ou mettre à jour le produit en fonction de son existence
            if not product:
                product = self.env['product.template'].create({
                    'default_code': product_code,
                    'name': sheet.cell_value(row, header.get('name')),
                })

            # Mapper les autres champs du fichier Excel aux champs Odoo ici pour mettre à jour le produit
            product.write({
                'name': sheet.cell_value(row, header.get('name')),
                # 'agrement_number': sheet.cell_value(row, header.get('agrement_number')),
                'region': sheet.cell_value(row, header.get('region')),
                # Allergen (Many2many)
                # AOP
                # Type fermier
                'type_milk': sheet.cell_value(row, header.get('type_milk')).lower(),
                'heat_treatment_milk': sheet.cell_value(row, header.get('heat_treatment_milk')).lower(),
                'rennet': sheet.cell_value(row, header.get('rennet')).lower(),
                'salting': sheet.cell_value(row, header.get('salting')).lower(),
                # Allergen (Many2many)
                # OGM
                'nv_energy_kj': sheet.cell_value(row, header.get('nv_energy_kj')),
                'nv_energy_kc': sheet.cell_value(row, header.get('nv_energy_kc')),
                'nv_fat': sheet.cell_value(row, header.get('nv_fat')),
                'fat_in_dry_matter': sheet.cell_value(row, header.get('fat_in_dry_matter')),
                'nv_saturated_fatty_acids': sheet.cell_value(row, header.get('nv_saturated_fatty_acids')),
                'nv_carbohydrates': sheet.cell_value(row, header.get('nv_carbohydrates')),
                'nv_sugars': sheet.cell_value(row, header.get('nv_sugars')),
                'nv_protein': sheet.cell_value(row, header.get('nv_protein')),
                'nv_salt': sheet.cell_value(row, header.get('nv_salt')),
            })
            
            # Récupérer les valeurs de la colonne ingredient et les diviser par ","
            ingredient_values = sheet.cell_value(row, header.get('ingredient')).split(',')
            
            # Nettoyer et créer les enregistrements product.ingredient si nécessaire
            ingredient_ids = []
            for ingredient_value in ingredient_values:
                ingredient_name = ingredient_value.strip()
                if ingredient_name:
                    # Rechercher ou créer un enregistrement product.ingredient avec le nom
                    ingredient = self.env['product.ingredient'].search([('name', '=', ingredient_name)], limit=1)
                    if not ingredient:
                        ingredient = self.env['product.ingredient'].create({'name': ingredient_name})
                    ingredient_ids.append(ingredient.id)
            
            # Attacher les enregistrements product.ingredient au produit
            product.write({'ingredient': [(6, 0, ingredient_ids)]})

        return True