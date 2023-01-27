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
import pytz
import datetime

class PartnerCrmAppointment(models.Model):
    _name = "partner.crm.appointment"
    _description = "Partner Appointment"

    type1 = fields.Selection([
                        ('spontaneous', 'Spontaneous'),
                        ('todo', 'To call'),
                           ], 'Type', index=True, default='todo')

    day = fields.Selection([
                        ('0', 'Monday'),
                        ('1', 'Tuesday'),
                        ('2', 'Wednesday'),
                        ('3', 'Thursday'),
                        ('4', 'Friday'),
                        ('5', 'Saturday'),
                        ('6', 'Sunday'),
                           ], 'Day', index=True, required=True)
    frequency = fields.Selection([
                        ('7', 'Every week'),
                        ('14', 'Every 2 week'),
                        ('21', 'Every 3 week'),
                        ('28', 'Every 4 week'),
                        ('42', 'Every 6 week'),
                           ], 'Frequency', default='7', required=True)

    time = fields.Float('Time')
    channel = fields.Selection([
                        ('phone', 'Phone'),
                        ('fax', 'Fax'),
                        ('mail', 'Mail'),
                        ('other', 'Other'),
                           ], string='Channel', default='phone')

    partner_id = fields.Many2one('res.partner', 'Customer')
    contact_id = fields.Many2one('res.partner', 'Contact')

    def init_appointment(self):
        """ ON change frequency or day remove previous appointment"""
        today = fields.datetime.now()
        phone_ids = self.env['crm.phone'].search([('date', '>=', today), ('appointment_id', '=', self.ids)])
        phone_ids.unlink()

    @api.model
    def timezone_2_utc(self, nextday, time, timezone="Europe/Paris"):
        """ return datetime with time (in float) with conversion in  timezone to UTC"""
        time = time or 8.0
        hour = int(time)
        minute = int((float(time) - float(hour)) * 60.0)
        nextday = nextday.replace(hour=hour, minute=minute, second=0)
        nextday_timezone = pytz.timezone(timezone).localize(nextday, is_dst=False)
        return nextday_timezone.astimezone(pytz.utc).replace(tzinfo=None)

    def create_next_appointment(self):
        """ return true if the last appointment is so older"""
        today = fields.datetime.now()
        res = self.env['crm.phonecall']

        for appointment in self:
            # check last appointment is ok in the futur
            partner = appointment.partner_id
            last_phone_ids = self.env['crm.phonecall'].search([('appointment_id', '=', appointment.id)],
                                                               order="date desc", limit=1)
            # if there is already a appointment: skip
            if last_phone_ids and last_phone_ids[0].date >= today:
                continue
            # Else if the last appointment is older than the frequency: create one
            if not last_phone_ids or (today - last_phone_ids[0].date).days > int(appointment.frequency):
                weekday = int(appointment.day)
                now_weekday = today.weekday()

                if now_weekday <= weekday:
                    nextday = today + datetime.timedelta(days=(weekday - now_weekday))
                else:
                    nextday = today + datetime.timedelta(days=(7 + weekday - now_weekday))

                nextday_utc = self.timezone_2_utc(nextday, appointment.time)

                phone_vals = {
                    'user_id': partner.user_id.id or False,
                    'name': partner.name or '?',
                    'partner_id': partner.id,
                    'partner_phone': partner.phone or '',
                    'partner_mobile': partner.mobile or '',
                    'duration': 0.5,
                    'appointment_id': appointment.id,
                    'channel': appointment.channel,
                    'type1': appointment.type1,
                    'date': nextday_utc,
                }
                res != self.env['crm.phonecall'].create(phone_vals)

        return res

    @api.model
    def cron_phone_appointment(self):
        """ Plan the customer call to do """
        today = fields.datetime.now()
        last_phone_ids = self.env['crm.phonecall'].search(
            [('date', '>', today), ('state', 'not in', ['cancel', 'done']), ('appointment_id', '!=', False)])
        futur_appointment_ids = last_phone_ids.mapped('appointment_id')
        print('-----------futur_appointment_ids--------------', futur_appointment_ids)
        appointment_ids = self.search([('id', 'not in', futur_appointment_ids.ids)])
        res = appointment_ids.create_next_appointment()
        print(res)
        return res
