# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
import urllib3
import random

SIMULATION_NUMBER = '99999999'

class StockWeightDevice(models.Model):
    _name = "stock.weight.device"
    _description = "Weight device"

    name = fields.Char('Description', required=True)
    code = fields.Char('Code', index=True, size=8)
    barcode = fields.Char('Barcode', index=True)
    address = fields.Char('Network address')
    simulation = fields.Boolean('Simulation')

    def get_weight(self, data={}):
        """ Get the weight, ask the device"""
        self.ensure_one()

        res = {}
        body = ''
        if self.simulation:
            if data.get('weight_line'):
                alea_product = random.uniform(0.90, 1.1)
                weight = data.get('weight')
                if not weight:
                    weight = 0.0
                weight = data['weight_line'].product_id.weight * alea_product * data['weight_line'].qty_done + weight
                res['weight'] = weight
            else:
                res['weight'] = random.uniform(0.90, 1.1)
            res['tare'] = 0.0
            res['number'] = SIMULATION_NUMBER
        else:
            try:
                http = urllib3.PoolManager()
                resp = http.request('GET', self.address)
                html = resp.data.decode('utf-8')
                body = html.split('<body>')[1].split('</body>')[0]
            except:
                res['warning'] = _("Weighted error, Network or device is unreachable")

            if body:
                remove_txt = ['<h1>', '</h1>', 'kg', ' ', '<p>', '</p>']
                for balise in remove_txt:
                    body = body.replace(balise, '')

                if 'ERR' in body:
                    res['warning'] = _("Weighted device in error")
                else:
                    body = body.split(',')

                    if len(body) == 5:
                        try:
                            res['weight'] = float(body[2])
                            res['tare'] = float(body[3])
                            res['number'] = body[4]
                        except:
                            res['weight'] = 0.0
                            res['tare'] = 0.0
                            res['warning'] = _("Weighted error, the weight value is not correct")
                    else:
                        res['warning'] = _("Weighted error, the weight value is not correct")
        
        if res.get('number'):
            weight_value_obj = self.env['stock.weight.value']
            weight_value_ids = weight_value_obj
            if res['number'] != SIMULATION_NUMBER:
                weight_value_ids = weight_value_obj.search([('name', '=', res['number'])])
            if not weight_value_ids:
                vals = {
                    'name': res.get('number', '?'),
                    'device_id': self.id,
                    'weight': res['weight'],
                    'tare': res.get('tare', 0.0),
                    'state': 'done'
                    }
                if res['number'] != SIMULATION_NUMBER:
                    vals['state'] = 'simulation'
                if data.get('weight_line'):
                    vals['move_line_id'] = data['weight_line'].id

                weight_value_obj.create(vals)

        return res.get('weight') or 0.0