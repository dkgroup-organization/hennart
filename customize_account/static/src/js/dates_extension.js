/** @odoo-module **/
// need to modify web/static/src/search/utils/dates.js

//import { Moment } from 'moment';
import { _lt } from "@web/core/l10n/translation";

export const QUARTERS = {
    1: { description: _lt("Q1"), coveredMonths: [1, 2, 3] },
    2: { description: _lt("Q2"), coveredMonths: [4, 5, 6] },
    3: { description: _lt("Q3"), coveredMonths: [7, 8, 9] },
    4: { description: _lt("Q4"), coveredMonths: [10, 11, 12] },
};

export const MONTH_OPTIONS = {
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

export const QUARTER_OPTIONS = {
    fourth_quarter: {
        id: "fourth_quarter",
        groupNumber: 1,
        description: QUARTERS[4].description,
        setParam: { quarter: 4 },
        granularity: "quarter",
    },
    third_quarter: {
        id: "third_quarter",
        groupNumber: 1,
        description: QUARTERS[3].description,
        setParam: { quarter: 3 },
        granularity: "quarter",
    },
    second_quarter: {
        id: "second_quarter",
        groupNumber: 1,
        description: QUARTERS[2].description,
        setParam: { quarter: 2 },
        granularity: "quarter",
    },
    first_quarter: {
        id: "first_quarter",
        groupNumber: 1,
        description: QUARTERS[1].description,
        setParam: { quarter: 1 },
        granularity: "quarter",
    },
};

export const YEAR_OPTIONS = {
    this_year: {
        id: "this_year",
        groupNumber: 2,
        format: "yyyy",
        plusParam: {},
        granularity: "year",
    },
    last_year: {
        id: "last_year",
        groupNumber: 2,
        format: "yyyy",
        plusParam: { years: -1 },
        granularity: "year",
    },
    antepenultimate_year: {
        id: "antepenultimate_year",
        groupNumber: 2,
        format: "yyyy",
        plusParam: { years: -2 },
        granularity: "year",
    },
};

export const PERIOD_OPTIONS = Object.assign({}, MONTH_OPTIONS, QUARTER_OPTIONS, YEAR_OPTIONS);

/**
 * Returns a version of the options in PERIOD_OPTIONS with translated descriptions
 * and a key defautlYearId used in the control panel model when toggling a period option.
 */
export function getPeriodOptions(referenceMoment) {
    // adapt when solution for moment is found...
    const options = [];
    const originalOptions = Object.values(PERIOD_OPTIONS);
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

/**
 * Returns a partial version of the period options whose ids are in selectedOptionIds
 * partitioned by granularity.
 */
export function getSelectedOptions(referenceMoment, selectedOptionIds) {
    const selectedOptions = { year: [] };
    for (const optionId of selectedOptionIds) {
        const option = PERIOD_OPTIONS[optionId];
        const setParam = getSetParam(option, referenceMoment);
        const granularity = option.granularity;
        if (!selectedOptions[granularity]) {
            selectedOptions[granularity] = [];
        }
        selectedOptions[granularity].push({ granularity, setParam });
    }
    return selectedOptions;
}


console.log("✅ 12 mois ajoutés à MONTH_OPTIONS !", PERIOD_OPTIONS);