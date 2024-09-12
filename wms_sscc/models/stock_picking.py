
import logging

from odoo import models, fields, api


_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = "stock.picking"

    sscc_line_ids = fields.One2many('stock.sscc', 'picking_id', 'Code colis SSCC')
    nb_total_sscc = fields.Integer('Total label', compute='compute_total_sscc')

    # Container and pallet need a sscc number.
    nb_container = fields.Integer('Nb container')
    nb_pallet = fields.Integer('Nb pallet')

    @api.depends('sscc_line_ids')
    def compute_total_sscc(self):
        """ return total label """
        for picking in self:
            picking.nb_total_sscc = len(picking.sscc_line_ids)

    @api.depends('nb_container', 'nb_pallet')
    def update_sscc(self):
        for picking in self:

            if picking.picking_type_code != 'outgoing':
                continue
            nb_total_container = int(picking.nb_container + picking.nb_pallet)
            sscc_line_ids = picking.sscc_line_ids.mapped('id')
            todo_sscc = nb_total_container - len(sscc_line_ids)

            if todo_sscc > 0:
                # Create SSCC
                while todo_sscc:
                    self.env['stock.sscc'].create({'picking_id': picking._origin.id})
                    todo_sscc -= 1
            elif todo_sscc < 0:
                # Delete SSCC
                while todo_sscc:
                    sscc = self.env['stock.sscc'].search([('picking_id', '=', picking._origin.id)],
                                                         order="id desc", limit=1)
                    sscc.unlink()
                    todo_sscc += 1




            #[{'sscc_name': '00070022210000053', 'package_id': None]
            sscc_datas = []
            for sscc in self.env['stock.sscc'].search([('picking_id', '=', picking._origin.id)], order="id desc"):
                # Chercher l'entrée dans 'stock.quant.package' qui correspond au nom du SSCC
                package = self.env['stock.quant.package'].search([('name', '=', sscc.name)], limit=1)
                # Ajouter les données au dictionnaire
                sscc_datas.append({
                    'sscc': sscc.name,
                    'package_id': package.id if package else None  # Si un package existe, prendre son ID, sinon None
                })

            #[{'product_id': 857, 'weight': 5.0, 'result_package_id': 2}]
            products = [
                {   "product_id": move_line.product_id.id,
                    "weight": move_line.weight,
                    "result_package_id": move_line.result_package_id.id
                }
                for move_line in picking.move_line_ids
            ]

            #repartition des produits dans les cartons en fonction du nombre demandé
            package_distribution = self.distribute_products_in_cartons(products, sscc_datas)

            # Rechercher le type de package ayant le nom "Chronopost Custom Parcel"
            default_package_type = self.env['stock.package.type'].search([('name', '=', 'Chronopost Custom Parcel')], limit=1)

            # Parcourir chaque carton dans la distribution
            for package in package_distribution:
                if package['package_id'] is None:
                    # Le package n'existe pas, le créer
                    new_package = self.env['stock.quant.package'].create({
                        'name': package['sscc_name'],
                        'package_type_id': default_package_type.id, 
                        'shipping_weight': package['total_weight'],
                    })

                    # Assigner le package_id nouvellement créé
                    package['package_id'] = new_package.id

                else:
                    # Le package existe déjà, on va le mettre à jour
                    existing_package = self.env['stock.quant.package'].browse(package['package_id'])

                    # Mettre à jour le poids du package
                    existing_package.shipping_weight = package['total_weight']
                
                for product in package['products']:

                    # Rechercher le move_line correspondant à ce produit
                    move_line = self.env['stock.move.line'].search([
                        ('product_id', '=', product['product_id']),
                        ('picking_id', '=', picking.id) 
                    ], limit=1)

                    # Mettre à jour le package_id dans move_line avec le nouveau ou l'existant package_id
                    move_line.write({
                        'result_package_id': package['package_id']  # Mise à jour du champ package_id
                    })

                    _logger.warning(f'WARNING_DKGROUP |  move_line : {move_line}')
            

          
    # construit un tableaux en sortie ;[{'sscc_name': '00070022210000053', 'package_id': None, 'total_weight': 5.0, 'products': [{'product_id': 857, 'weight': 5.0, 'result_package_id': 2}]}]
    def distribute_products_in_cartons(self, products, sscc_datas):
        # Sort products by weight descending to ensure a balanced distribution
        products_sorted = sorted(products, key=lambda x: x['weight'], reverse=True)
        
        # Initialize dictionary to store cartons with their sscc names, package_ids, and products
        cartons = [{'sscc_name': sscc['sscc'], 'package_id': sscc['package_id'], 'total_weight': 0, 'products': []} for sscc in sscc_datas]
        
        # Distribute products into cartons to balance weight
        for product in products_sorted:
            # Find the carton with the smallest current total weight
            min_carton = min(cartons, key=lambda x: x['total_weight'])
            
            # Add the product to that carton and update the total weight
            min_carton['products'].append(product)
            min_carton['total_weight'] += product['weight']
        
        return cartons

