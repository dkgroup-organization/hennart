# -*- coding: utf-8 -*-
from odoo import fields, models, api
import urllib3

class StockWeightDevice(models.Model):
    _name = "stock.weight.device"
    _description = "Weight device"

    name = fields.Char('Description', required=True)
    code = fields.Char('Code', index=True, size=8)
    barcode = fields.Char('Barcode', index=True)
    address = fields.Char('Network address')

    def get_weight(self, data):
        self.ensure_one()

        res = {}

        http = urllib3.PoolManager()
        resp = http.request('GET', self.address)
        html = resp.data.decode('utf-8')
        if html:
            try:
                body = html.split('<body>')[1].split('</body>')[0]
            except:
                body = ''
        if body:
            remove_txt = ['<h1>', '</h1>', 'kg', ' ', '<p>', '</p>']
            for balise in remove_txt:
                body = body.replace(balise, '')
            if 'ERR' in body:
                res['warning'] = "Erreur balance: %s" % body
            else:
                body = body.split(',')

                if len(body) == 5:
                    try:
                        res['weight'] = float(body[2])
                        res['tare'] = float(body[3])
                    except:
                        res['weight'] = 0.0
                        res['tare'] = 0.0

                    res['number'] = body[4]
                    res['device_id'] = self.id
                else:
                    res['warning'] = "Erreur de lecture balance"
        else:
            res['warning'] = "Erreur de lecture balance"
        
        if res.get('number'):
            weight_value_obj = self.env['stock.weight.value']

            weight_value_ids = weight_value_obj.search([('name', '=', res['number'])])
            if not weight_value_ids:
                vals = {
                    'name': res['number'],
                    'device_id': res['device_id'],
                    'weight': res['weight'],
                    'tare': res['tare'],
                    'move_line_id': data.get('weight_line'),
                    }
                weight_value_obj.create(vals)

        return res