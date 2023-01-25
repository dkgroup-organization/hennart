#!/usr/bin/python
##############################################
#
# Copyright (C) 2015 OpenCREA (<http://opencrea.fr>)
#
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs.
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company.
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/> or
# write to the Free Software Foundation, Inc.,
# 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
###############################################


from odoo import api, fields, models, _
from datetime import date, timedelta


class partner_delivery_appointment(models.Model):

    _name = "partner.delivery.appointment"
    _description = "Partner delivery Appointement"


    load_day =fields.Selection([
                        ('0', 'Monday'),
                        ('1', 'Tuesday'),
                        ('2', 'Wednesday'),
                        ('3', 'Thursday'),
                        ('4', 'Friday'),
                        ('5', 'Saturday'),
                        ('6', 'Sunday'),
                        ], 'Load day', index=True)
    load_time = fields.Float('Load Time')
    delivery_day = fields.Selection([
                        ('0', 'Monday'),
                        ('1', 'Tuesday'),
                        ('2', 'Wednesday'),
                        ('3', 'Thursday'),
                        ('4', 'Friday'),
                        ('5', 'Saturday'),
                        ('6', 'Sunday'),
                           ], 'Delivery Day', index=True)
    delivery_time = fields.Float('Delivery Time')

    partner_id = fields.Many2one('res.partner', 'Customer')
    carrier_id = fields.Many2one("delivery.carrier", "Delivery Method")


