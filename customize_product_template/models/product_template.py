# -*- coding: utf-8 -*-


from odoo import api, fields, models, tools, _


class ProductArea(models.Model):
    _name = 'product.area'
    _description = "Geographical area"
    name = fields.Char(string='Name', required=True, translate=True)


class ProductAllergen(models.Model):
    _name = 'product.allergen'
    _description = "Allergenic component "
    name = fields.Char(string='Name', required=True, translate=True)


class ProductIngredient(models.Model):
    _name = 'product.ingredient'
    _description = "Ingredient"
    name = fields.Char(string='Name', required=True, translate=True)


class ProductSpecificity(models.Model):
    _name = 'product.specificity'
    _description = "Spécificity"
    name = fields.Char(string='Name', required=True, translate=True)
    
    
class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @tools.ormcache()
    def _get_default_uos_id(self):
        return self.env.ref('uom.product_uom_unit')

    uos_id = fields.Many2one('uom.uom', string='Unit of Sale',
                             default=_get_default_uos_id, required=True,
                             help="Default unit of Sale used for invoicing.")
    code_ean_prix = fields.Char('Code EAN Prix', size=12)
    code_ean_poids = fields.Char('Code EAN Poids', size=12)
    code_DUN14 = fields.Char('Code DUN14', size=14)
    not_solded = fields.Boolean(string='No longer sold')
    origine = fields.Char('Origin', size=128)
    area = fields.Many2one(string='Area', comodel_name='product.area')
    ingredient = fields.Many2many('product.ingredient', 'ingredient_rel', string="Ingredient")
    allergen = fields.Many2many('product.allergen', 'allereg_reel', string="Allergen" )
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
    to_weight = fields.Boolean(string='to weight')
    tare = fields.Float(string='Tare', help='Tare')
    weight_gross = fields.Float(string='Gross Weight',help='The gross weight in Kg.')
    format_etiquette =  fields.Char('Format d\'etiquette', size=128)
    to_label = fields.Boolean(string='to label')
    gestion_affinage = fields.Boolean(string='Refining management')
    to_personnalize = fields.Boolean(string='Customer specifity')

    # WEB description
    web_historic = fields.Html('Historic')
    web_manufacture = fields.Html('Manufacture')
    web_tasting = fields.Html('Tasting')






