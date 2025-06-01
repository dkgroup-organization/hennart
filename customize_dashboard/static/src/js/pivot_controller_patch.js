/** @odoo-module **/

import { PivotController } from "@web/views/pivot/pivot_controller";
import { patch } from "@web/core/utils/patch";

patch(PivotController.prototype, "customize_dashboard/pivot_controller_patch", {
    isComparingInfo() {
        return false;  // ✅ toujours désactivé, même si des domaines de comparaison sont présents
    },
});
