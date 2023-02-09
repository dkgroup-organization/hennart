# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################


from odoo import api, fields, models, _, Command
from odoo.addons.base.models.decimal_precision import DecimalPrecision


class Product_area(models.Model):
    _name = 'product.area'
    name = fields.Char(string='Name', required=True, translate=True)
    
class Product_allergen(models.Model):
    _name = 'product.allergen'
    name = fields.Char(string='Name', required=True, translate=True)
    
class Product_ingredient(models.Model):
    _name = 'product.ingredient'
    name = fields.Char(string='Name', required=True, translate=True)
    
class Product_specificity(models.Model):
    _name = 'product.specificity'
    name = fields.Char(string='Name', required=True, translate=True)
    
    
class Product_tempalte(models.Model):
    _inherit = 'product.template'

    code_ean_prix = fields.Char('Code EAN Prix', size=12)
    code_ean_poids = fields.Char('Code EAN Poids', size=12)
    code_DUN14 = fields.Char('Code DUN14', size=14)
    not_solded = fields.Boolean(string='No longer sold')
    origine = fields.Char('Origine', size=128, select=True)
    area = fields.Many2one(string='Area', comodel_name='product.area')
    ingredient = fields.Many2many('product.ingredient', 'ingredient_rel', string="Ingredient")
    allergen = fields.Many2many( 'product.allergen', 'allereg_reel',string="Allergen" )
    production_specificity = fields.Many2many('product.specificity','specifit_reel', string="Production specifity",
                                              help='define some spécificity like OGM, IGP, farmer, presence of GMO')
    specificity_milk = fields.Selection(
        selection=[
            ('farmer', 'Farmer'),
            ('craft', 'Craft'),
            ('cooked_pressed', 'Cooked pressed dough'),
            ('uncooked_pressed', 'Uncooked pressed dough'),
            ('veined', 'Veined cheese dough'),
            ('natural_rind', 'Natural rind soft cheese'),
            ('washed_rind', 'Soft washed rind'),
            ('fuzzy_rind', 'Soft fuzzy rind'),
            ('processed', 'Processed product'),
            ('fees', 'Fees and Butter'),
            ('tray', 'Tray'),
            ('craft', 'Craft'),
            ('other', 'Other'),

        ],
        string='Technical family')
    heat_treatment_milk = fields.Selection(
        selection=[
            ('raw', 'Raw'),
            ('thermised', 'Thermised'),
            ('pasteurized', 'Pasteurized'),
            ('other', 'Other'),
        ],
        string='Heat treatment of milk')

    rennet = fields.Selection(
        selection=[
            ('animal', 'Animal'),
            ('fermentative', 'Fermentative'),
            ('microbial', 'Microbial'),
            ('other', 'Other'),
        ],
        string='Rennet')

    salting = fields.Selection(
        selection=[
            ('dry', 'Dry'),
            ('brine', 'Brine'),
        ],
        string='Salting')

    pate_molle = fields.Boolean(string='Pate molle')
    type_milk = fields.Selection(
        selection=[
            ('cow', 'Cow'),
            ('goat', 'Goat'),
            ('sheep', 'Sheep'),
            ('vegetable', 'Vegetable'),
            ('other', 'Other'),
        ],
        string='Type milk')

    matiere_grasse = fields.Char('Fat', size=12)
    fat_in_product = fields.Float(string='Fat in product (%)')
    fat_in_dry_matter = fields.Float(
        string='Fat in dry matter (%)') 
    whole_milk = fields.Boolean(string='Whole milk')

    nv_energy_kj = fields.Float(string=' Energy (Kj)')
    nv_energy_kc = fields.Float(string=' Energy (Kcal)')
    nv_fat = fields.Float(string='FAT (g)')
    nv_saturated_fatty_acids = fields.Float(string='Saturated fatty acids (g)')
    nv_carbohydrates = fields.Float(string='Carbohydrates (g)')
    nv_sugars = fields.Float(string='Sugars (g)')
    nv_protein = fields.Float(string=' Protein (g)')
    nv_salt = fields.Float(string='Salt (g)')

    life_date = fields.Boolean(string='DLC : End of Life Date')
    use_date = fields.Boolean(string='DDM : Best before Date')

    # volume = fields.Float(string='Volume',help='The volume in m3')
    to_weight = fields.Boolean(string='a peser')
    tare = fields.Float(string='Tare',help='Tare')
    weight_net = fields.Float(string='Net Weight',help='The net weight in Kg.')
    format_etiquette =  fields.Char('Format d\'etiquette', size=128,select=True)
    to_label = fields.Boolean(string='a etiqueter')
    gestion_affinage = fields.Boolean(string='Gestion de l affinage')
    to_personnalize = fields.Boolean(string='Specifique au client')





