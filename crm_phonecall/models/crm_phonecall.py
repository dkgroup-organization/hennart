# Copyright 2004-2016 Odoo SA (<http://www.odoo.com>)
# Copyright 2017 Tecnativa - Vicent Cubells
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from functools import reduce
from odoo.exceptions import UserError
from odoo import _, api, fields, models
from odoo.tools.safe_eval import safe_eval
from datetime import datetime
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import pytz
from odoo import api, fields, models, _, Command
from odoo.addons.base.models.decimal_precision import DecimalPrecision

class CrmPhonecall(models.Model):
    """Model for CRM phonecalls."""

    _name = "crm.phonecall"
    _description = "Phonecall"
    _order = "id desc"
    _inherit = ["mail.thread", "utm.mixin"]

    date_action_last = fields.Datetime(string="Last Action", readonly=True)
    date_action_next = fields.Datetime(string="Next Action", readonly=True)
    create_date = fields.Datetime(string="Creation Date", readonly=True)
    team_id = fields.Many2one(
        comodel_name="crm.team",
        string="Sales Team",
        index=True,
        help="Sales team to which Case belongs to.",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
        default=lambda self: self.env.user,
    )
    partner_id = fields.Many2one(comodel_name="res.partner", string="Contact")
    company_id = fields.Many2one(comodel_name="res.company", string="Company")
    description = fields.Text()
    state = fields.Selection(
        [
            ("open", "Confirmed"),
            ("cancel", "Cancelled"),
            ("pending", "Pending"),
            ("done", "Held"),
        ],
        string="Status",
        tracking=3,
        default="open",
        help="The status is set to Confirmed, when a case is created.\n"
        "When the call is over, the status is set to Held.\n"
        "If the callis not applicable anymore, the status can be set "
        "to Cancelled.",
    )
    email_from = fields.Char(string="Email", help="These people will receive email.")
    date_open = fields.Datetime(string="Opened", readonly=True)
    name = fields.Char(string="Call Summary", required=True)
    active = fields.Boolean(required=False, default=True)
    duration = fields.Float(help="Duration in minutes and seconds.")
    tag_ids = fields.Many2many(
        comodel_name="crm.tag",
        relation="crm_phonecall_tag_rel",
        string="Tags",
        column1="phone_id",
        column2="tag_id",
    )
    partner_phone = fields.Char(string="Phone")
    partner_mobile = fields.Char("Mobile")
    priority = fields.Selection(
        selection=[("0", "Low"), ("1", "Normal"), ("2", "High")],
        default="1")
    date_closed = fields.Datetime(string="Closed", readonly=True)
    date = fields.Datetime(default=lambda self: fields.Datetime.now())
    opportunity_id = fields.Many2one(comodel_name="crm.lead", string="Lead/Opportunity")
    direction = fields.Selection(
        [("in", "In"), ("out", "Out")], default="out", required=True
    )

    channel = fields.Selection([
        ('phone', 'Phone'),
        ('fax', 'Fax'),
        ('mail', 'Mail'),
        ('other', 'Other'),
        ], 'Channel')

    type1 = fields.Selection([
        ('spontaneous', 'Spontaneous'),
        ('todo', 'To call'),
        ], 'Type', index=True, required=True)

    appointment_id = fields.Many2one('partner.crm.appointment', 'Appointment')

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        """Contact number details should be change based on partner."""
        if self.partner_id:
            self.partner_phone = self.partner_id.phone
            self.partner_mobile = self.partner_id.mobile

    @api.onchange("opportunity_id")
    def _onchange_opportunity_id(self):
        """Based on opportunity, change contact, tags, partner, team."""
        if self.opportunity_id:
            self.team_id = self.opportunity_id.team_id.id
            self.partner_phone = self.opportunity_id.phone
            self.partner_mobile = self.opportunity_id.mobile
            self.partner_id = self.opportunity_id.partner_id.id
            self.tag_ids = self.opportunity_id.tag_ids.ids

    def write(self, values):
        """Override to add case management: open/close dates."""
        if values.get("state"):
            if values.get("state") == "done":
                values["date_closed"] = fields.Datetime.now()
                self.compute_duration()
            elif values.get("state") == "open":
                values["date_open"] = fields.Datetime.now()
                values["duration"] = 0.0
        return super().write(values)

    def compute_duration(self):
        """Calculate duration based on phonecall date."""
        phonecall_dates = self.filtered("date")
        phonecall_no_dates = self - phonecall_dates
        for phonecall in phonecall_dates:
            if phonecall.duration <= 0 and phonecall.date:
                duration = fields.Datetime.now() - phonecall.date
                values = {"duration": duration.seconds / 60.0}
                phonecall.write(values)
            else:
                phonecall.duration = 0.0
        phonecall_no_dates.write({"duration": 0.0})
        return True

    def get_values_schedule_another_phonecall(self, vals):
        res = {
            "name": vals.get("name"),
            "user_id": vals.get("user_id") or self.user_id.id,
            "description": self.description,
            "date": vals.get("schedule_time") or self.date,
            "team_id": vals.get("team_id") or self.team_id.id,
            "partner_id": self.partner_id.id,
            "partner_phone": self.partner_phone,
            "partner_mobile": self.partner_mobile,
            "priority": self.priority,
            "opportunity_id": self.opportunity_id.id,
            "campaign_id": self.campaign_id.id,
            "source_id": self.source_id.id,
            "medium_id": self.medium_id.id,
        }
        if vals.get("tag_ids"):
            res.update({"tag_ids": [(6, 0, vals.get("tag_ids"))]})
        return res

    def schedule_another_phonecall(self, vals, return_recordset=False):
        """Action :('schedule','Schedule a call'), ('log','Log a call')."""
        phonecall_dict = {}
        for call in self:
            values = call.get_values_schedule_another_phonecall(vals)
            new_id = self.create(values)
            if vals.get("action") == "log":
                call.write({"state": "done"})
            phonecall_dict[call.id] = new_id
        if return_recordset:
            return reduce(lambda x, y: x + y, phonecall_dict.values())
        else:
            return phonecall_dict

    def redirect_phonecall_view(self):
        """Redirect on the phonecall related view."""
        # Select the view
        tree_view_id = self.env.ref("crm_phonecall.crm_case_phone_tree_view").id
        form_view_id = self.env.ref("crm_phonecall.crm_case_phone_form_view").id
        search_view_id = self.env.ref(
            "crm_phonecall.view_crm_case_phonecalls_filter"
        ).id
        value = {}
        for call in self:
            value = {
                "name": _("Phone Call"),
                "view_type": "form",
                "view_mode": "tree,form",
                "res_model": "crm.phonecall",
                "res_id": call.id,
                "views": [
                    (form_view_id or False, "form"),
                    (tree_view_id or False, "tree"),
                    (False, "calendar"),
                ],
                "type": "ir.actions.act_window",
                "search_view_id": search_view_id or False,
            }
        return value

    def action_make_meeting(self):
        """Open meeting's calendar view to schedule a meeting on phonecall."""
        partner_ids = [self.env["res.users"].browse(self.env.uid).partner_id.id]
        res = {}
        for phonecall in self:
            if phonecall.partner_id and phonecall.partner_id.email:
                partner_ids.append(phonecall.partner_id.id)
            res = self.env["ir.actions.act_window"]._for_xml_id(
                "calendar.action_calendar_event"
            )
            res["context"] = {
                "default_phonecall_id": phonecall.id,
                "default_partner_ids": partner_ids,
                "default_user_id": self.env.uid,
                "default_email_from": phonecall.email_from,
                "default_name": phonecall.name,
            }
        return res

    def _prepare_opportunity_vals(self):
        return {
            "name": self.name,
            "partner_id": self.partner_id.id,
            "phone": self.partner_phone or self.partner_id.phone,
            "mobile": self.partner_mobile or self.partner_id.mobile,
            "email_from": self.partner_id.email,
            "team_id": self.team_id.id,
            "description": self.description,
            "priority": self.priority,
            "type": "opportunity",
            "campaign_id": self.campaign_id.id,
            "source_id": self.source_id.id,
            "medium_id": self.medium_id.id,
            "tag_ids": [(6, 0, self.tag_ids.ids)],
        }

    def action_button_convert2opportunity(self):
        """Convert a phonecall into an opp and redirect to the opp view."""
        self.ensure_one()
        opportunity = self.env["crm.lead"]
        opportunity_id = opportunity.create(self._prepare_opportunity_vals())
        self.write({"opportunity_id": opportunity_id.id, "state": "done"})
        return opportunity_id.redirect_lead_opportunity_view()

    def action_sale_create(self):
        """ Create sale order"""
        action = {}
        sale_ids = self.env['sale.order']

        for phonecall in self:
            if not phonecall.partner_id:
                raise UserError(_('Error!'), _('Please define a contact before create a sale order'))
            elif phonecall.partner_id.is_company:
                partner = phonecall.partner_id
            elif phonecall.partner_id.parent_id:
                partner = phonecall.partner_id.parent_id
            else:
                partner = phonecall.partner_id
            if not partner:
                continue
            commitment_date = False
            date_entrepot = False
            carrier = False
            today1 = datetime.now()
            

            if partner.appointment_delivery_ids:
                app = phonecall.partner_id.appointment_delivery_ids[0]

                if today1.weekday() == int(app.load_day):
                  if  today1.hour <= 12:
                    while today1.weekday() != int(app.load_day): #0 for monday
                      today1 += timedelta(days=1)
                    date_entrepot = today1
                    today2 = date_entrepot

                    while today2.weekday() != int(app.delivery_day): #0 for monday
                      today2 += timedelta(days=1)
                    commitment_date = today2

                    sale_vals = {
                    'user_id': partner.user_id.id or False,
                    'partner_id': partner.id,
                    'state': 'draft',
                    'date_entrepot':date_entrepot,
                    'carrier_id' : partner.appointment_delivery_ids[0].carrier_id.id,
                    'commitment_date': commitment_date
            }
                  else:
                    today1 += timedelta(days=1)
                    while today1.weekday() != int(app.load_day): #0 for monday
                      today1 += timedelta(days=1)
                    date_entrepot = today1
                    today2 = date_entrepot

                    while today2.weekday() != int(app.delivery_day): #0 for monday
                      today2 += timedelta(days=1)
                    commitment_date = today2

                    sale_vals = {
                    'user_id': partner.user_id.id or False,
                    'partner_id': partner.id,
                    'state': 'draft',
                    'date_entrepot':date_entrepot,
                    'carrier_id' : partner.appointment_delivery_ids[0].carrier_id.id,
                    'commitment_date': commitment_date
                    }

                else:
                    while today1.weekday() != int(app.load_day): #0 for monday
                      today1 += timedelta(days=1)
                    date_entrepot = today1
                    today2 = date_entrepot

                    while today2.weekday() != int(app.delivery_day): #0 for monday
                      today2 += timedelta(days=1)
                    commitment_date = today2

                    sale_vals = {
                    'user_id': partner.user_id.id or False,
                    'partner_id': partner.id,
                    'state': 'draft',
                    'date_entrepot':date_entrepot,
                    'carrier_id' : partner.appointment_delivery_ids[0].carrier_id.id,
                    'commitment_date': commitment_date
                    }

            


            sale = self.env['sale.order'].create(sale_vals)
            sale_ids |= sale
            phonecall.write({'state': 'done'})

        if sale_ids:
            action = {
                'name': _('Sale'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'sale.order',
                'res_id': sale[0].id,
                'target': 'current',
                'context': {},
                'type': 'ir.actions.act_window',
                }
            if len(sale_ids) > 1:
                action['res_id'] = False
                action['domain'] = [('id', 'in', sale_ids.ids)]

        return action
