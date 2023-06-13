##############################################################################
#                                                                            #
#   OpenERP Module                                                           #
#   Copyright (C) 2016 OpenCrea <joannes.landy@opencrea.fr>                  #
#                                                                            #
#   This program is free software: you can redistribute it and/or modify     #     
#   it under the terms of the GNU Affero General Public License as           #    
#   published by the Free Software Foundation, either version 3 of the       #    
#   License, or (at your option) any later version.                          #    
#                                                                            #    
#   This program is distributed in the hope that it will be useful,          #    
#   but WITHOUT ANY WARRANTY; without even the implied warranty of           #    
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the            #    
#   GNU Affero General Public License for more details.                      #    
#                                                                            #  
#   You should have received a copy of the GNU Affero General Public License #
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.    #
#                                                                            #
##############################################################################

{
    "name": "Hennart Labels extend",
    "version": "1.0",
    "depends": ["wms_label"],
    "author": "OpenCrea",
    "category": "Stocks",
    "description": """
    Etiquette ZEBRA projet Hennart
    """,
    "data": ["security/ir.model.access.csv","data/label.xml", "wizard/label_stock_move_view.xml", "wizard/label_container_view.xml"],
    'installable': True,
    'active': False,

}
