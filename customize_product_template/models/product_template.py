# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################


from odoo import api, fields, models, _, Command
from odoo.addons.base.models.decimal_precision import DecimalPrecision


class Product_tempalte(models.Model):
    _inherit = 'product.template'

    code_ean_prix = fields.Char('CODE EAN Prix', size=12)
    code_ean_poids = fields.Char('CODE EAN Poids', size=12)
    code_DUN14 = fields.Char('CODE DUN14', size=14)
    not_solded = fields.Boolean(string='No longer sold')
    origine = fields.Char('Origine', size=128,select=True)
    area = fields.Many2one(string='Area', comodel_name='product.area')
    ingredient = fields.Many2many('product.ingredient','ingredient_rel', string="Ingredient")
    allergen = fields.Many2many( 'product.allergen', 'allereg_reel',string="Allergen" )
    production_specificity = fields.Many2many('product.specificity','specifit_reel' ,string="Production specifity" , help='define some spécificity like OGM, IGP, farmer, presence of GMO')
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

    matiere_grasse =  fields.Char('Fat', size=12)
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
    life_time = fields.Integer(string='DLC : Product Life Time',help='When a new a Serial Number is issued, this is the number of days before the goods may become dangerous and must not be consumed' )
    use_time = fields.Integer(string='Product Use Time',help='When a new a Serial Number is issued, this is the number of days before the goods starts deteriorating, without being dangerous yet' )
    alert_time = fields.Integer(string='Product Alert Time',help='When a new a Serial Number is issued, this is the number of days before an alert should be notified' )

    removal_time = fields.Integer(string='Product Removal Time',help='When a new a Serial Number is issued, this is the number of days before the goods should be removed from the stock.' )

    volume = fields.Float(string='Volume',help='The volume in m3')
    to_weight = fields.Boolean(string='a peser')
    tare = fields.Float(string='Tare',help='Tare')
    weight_net = fields.Float(string='Net Weight',help='The net weight in Kg.')
    format_etiquette =  fields.Char('Format d\'etiquette', size=128,select=True)
    to_label = fields.Boolean(string='a etiqueter')
    gestion_affinage = fields.Boolean(string='Gestion de l affinage')
    to_personnalize = fields.Boolean(string='Specifique au client')








