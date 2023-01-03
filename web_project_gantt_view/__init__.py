
# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from . import models

def uninstall_hook(cr, registry):
    cr.execute("UPDATE ir_act_window "
               "SET view_mode=replace(view_mode, ',ganttview', '')"
               "WHERE view_mode LIKE '%,ganttview%';")
    cr.execute("UPDATE ir_act_window "
               "SET view_mode=replace(view_mode, 'ganttview,', '')"
               "WHERE view_mode LIKE '%ganttview,%';")
    cr.execute("DELETE FROM ir_act_window "
               "WHERE view_mode = 'ganttview';")
