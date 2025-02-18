/** @odoo-module **/

import { registry } from '@web/core/registry';
import { getPeriodOptions as originalGetPeriodOptions } from "@web/search/utils/dates";

let customFiltersEnabled = true;



// Ajouter les nouveaux filtres seulement si activé dans la config
function getPeriodOptions(referenceMoment) {
    const options = originalGetPeriodOptions(referenceMoment);

    if (customFiltersEnabled) {
        Object.assign(options, {
            last_3_months: { id: "last_3_months", groupNumber: 1, format: "MMMM", plusParam: { months: -3 }, granularity: "month" },
            last_4_months: { id: "last_4_months", groupNumber: 1, format: "MMMM", plusParam: { months: -4 }, granularity: "month" },
            last_5_months: { id: "last_5_months", groupNumber: 1, format: "MMMM", plusParam: { months: -5 }, granularity: "month" },
            last_6_months: { id: "last_6_months", groupNumber: 1, format: "MMMM", plusParam: { months: -6 }, granularity: "month" },
            last_7_months: { id: "last_7_months", groupNumber: 1, format: "MMMM", plusParam: { months: -7 }, granularity: "month" },
            last_8_months: { id: "last_8_months", groupNumber: 1, format: "MMMM", plusParam: { months: -8 }, granularity: "month" },
            last_9_months: { id: "last_9_months", groupNumber: 1, format: "MMMM", plusParam: { months: -9 }, granularity: "month" },
            last_10_months: { id: "last_10_months", groupNumber: 1, format: "MMMM", plusParam: { months: -10 }, granularity: "month" },
            last_11_months: { id: "last_11_months", groupNumber: 1, format: "MMMM", plusParam: { months: -11 }, granularity: "month" },
        });
    }

    return options;
}

// Surcharge de la fonction de filtrage
registry.category('searchUtils').add('getPeriodOptions', getPeriodOptions, { force: true });
