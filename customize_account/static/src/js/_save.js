/** @odoo-module **/
// need to modify web/static/src/search/utils/dates.js

import {MONTH_OPTIONS} from "@web/search/utils/dates";
import {QUARTER_OPTIONS} from "@web/search/utils/dates";
import {YEAR_OPTIONS} from "@web/search/utils/dates";

console.log("✅ MONTH_OPTIONS !", MONTH_OPTIONS);
/** @odoo-module **/

import { registry } from '@web/core/registry';
import { getPeriodOptions as originalGetPeriodOptions } from  "@web/search/utils/dates";

//import { Moment } from 'moment';

const MONTH_OPTIONS_OVERRIDE = {
    last_3_months: {
        id: "last_3_months",
        groupNumber: 1,
        format: "MMMM",
        plusParam: { months: -3 },
        granularity: "month",
    },
    last_4_months: {
        id: "last_4_months",
        groupNumber: 1,
        format: "MMMM",
        plusParam: { months: -4 },
        granularity: "month",
    },
    last_5_months: {
        id: "last_5_months",
        groupNumber: 1,
        format: "MMMM",
        plusParam: { months: -5 },
        granularity: "month",
    },
    last_6_months: {
        id: "last_6_months",
        groupNumber: 1,
        format: "MMMM",
        plusParam: { months: -6 },
        granularity: "month",
    },
    last_7_months: {
        id: "last_7_months",
        groupNumber: 1,
        format: "MMMM",
        plusParam: { months: -7 },
        granularity: "month",
    },
    last_8_months: {
        id: "last_8_months",
        groupNumber: 1,
        format: "MMMM",
        plusParam: { months: -8 },
        granularity: "month",
    },
    last_9_months: {
        id: "last_9_months",
        groupNumber: 1,
        format: "MMMM",
        plusParam: { months: -9 },
        granularity: "month",
    },
    last_10_months: {
        id: "last_10_months",
        groupNumber: 1,
        format: "MMMM",
        plusParam: { months: -10 },
        granularity: "month",
    },
    last_11_months: {
        id: "last_11_months",
        groupNumber: 1,
        format: "MMMM",
        plusParam: { months: -11 },
        granularity: "month",
    },
};


export const PERIOD_OPTIONS_OVERRIDE = Object.assign({}, MONTH_OPTIONS_OVERRIDE, QUARTER_OPTIONS, YEAR_OPTIONS);
/**
 * Returns a version of the options in PERIOD_OPTIONS with translated descriptions
 * and a key defautlYearId used in the control panel model when toggling a period option.
 */
export function getPeriodOptions(referenceMoment) {
    // adapt when solution for moment is found...
    const options = [];
    const originalOptions = Object.values(PERIOD_OPTIONS_OVERRIDE);
    for (const option of originalOptions) {
        const { id, groupNumber } = option;
        let description;
        let defaultYear;
        switch (option.granularity) {
            case "quarter":
                description = option.description.toString();
                defaultYear = referenceMoment.set(option.setParam).year;
                break;
            case "month":
            case "year": {
                const date = referenceMoment.plus(option.plusParam);
                description = date.toFormat(option.format);
                defaultYear = date.year;
                break;
            }
        }
        const setParam = getSetParam(option, referenceMoment);
        options.push({ id, groupNumber, description, defaultYear, setParam });
    }
    const periodOptions = [];
    for (const option of options) {
        const { id, groupNumber, description, defaultYear } = option;
        const yearOption = options.find((o) => o.setParam && o.setParam.year === defaultYear);
        periodOptions.push({
            id,
            groupNumber,
            description,
            defaultYearId: yearOption.id,
        });
    }
    return periodOptions;
}


registry.category('searchUtils').add('getPeriodOptions', getPeriodOptions, { force: true });
console.log("✅ 12 mois ajoutés à MONTH_OPTIONS !", PERIOD_OPTIONS);