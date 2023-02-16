##############################################################################
#
#    Source code aggregation of :
#    Copyright (C) 2016 OpenCrea SAS (<http://opencrea.fr>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
"name" : "Carrier module of the WMS",
    "category" : "Generic Modules",
    "version" : "1.0",
    "depends": ["crm", "calendar", "delivery", "sale"],
    "author" : "OpenCrea",
    "description": """
    carrier module for the Warehouse Management System:
    """,
    # 'init_xml': [],
    "data": [
    "view/carrier_view.xml",
    "view/stock_picking_out_view.xml",
    "security/ir.model.access.csv",
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
