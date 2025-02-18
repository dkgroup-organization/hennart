odoo.define('customize_account.searchUtilsExtension', function (require) {
    "use strict";

    var searchUtils = require('web.searchUtils');

    // Étendre une méthode spécifique
    searchUtils.MONTH_OPTIONS = {
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

    searchUtils.PERIOD_OPTIONS = Object.assign({}, searchUtils.MONTH_OPTIONS, searchUtils.QUARTER_OPTIONS, searchUtils.YEAR_OPTIONS);



    return searchUtils;
});
