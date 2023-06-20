# -*- coding: utf-8 -*-
from odoo import fields, models, api
import urllib3

class StockWeightDevice(models.Model):
    _name = "stock.weight.device"
    _description = "Weight device"

    name = fields.Char('Description', required=True, select=True)
    code = fields.Char('Code', select=True, size=8)
    barcode = fields.Char('Barcode', select=True)
    address = fields.Char('Network address')


    def get_weight(self, ids=False, picking_id=False, product_id=False, product_qty=False):
        unique_id = ids and ids[0] or False
        res = {}
        if unique_id:
            device = self.browse(unique_id)
            http = urllib3.PoolManager()
            resp = http.request('GET',device.address)
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
                        res['device_id'] = unique_id
                    else:
                        res['warning'] = "Erreur de lecture balance"
            else:
                res['warning'] = "Erreur de lecture balance"
        if res.get('number',False):
            weight_value_obj = self.env['stock.weight.value']

            weight_value_ids = weight_value_obj.search([('name', '=', res['number'])])
            if not weight_value_ids:
                vals = {
                    'name': res['number'],
                    'device_id': res['device_id'],
                    'weight': res['weight'],
                    'tare': res['tare'],
                    'product_qty': product_qty,
                    'product_id': product_id,
                    'picking_id': picking_id,
                    }
                weight_value_obj.create(vals)

        return res