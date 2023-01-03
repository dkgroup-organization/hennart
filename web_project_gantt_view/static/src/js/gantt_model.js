odoo.define('web_project_gantt_view.GanttModel', function (require) {
    "use strict";
    
    var AbstractModel = require('web.AbstractModel');
    var core = require('web.core');
    var fieldUtils = require('web.field_utils');
    var session = require('web.session');
    const { findWhere, groupBy } = require('web.utils');
    
    var concurrency = require('web.concurrency');
    
    var _t = core._t;
    
    var  GanttModel = AbstractModel.extend({
    
        init: function () {
            this._super.apply(this, arguments);
            this.dp = new concurrency.DropPrevious();
    
            this.gantt = null;
        },
    
        get: function () {
            return _.extend({}, this.gantt);
        },
    
        load: function (params) {        
            this.modelName = params.modelName;
            this.mapping = params.mapping;
            this.fields = params.fields;
            this.domain = params.domain;
            
            this.dateStartField = params.dateStartField;
            this.dateStopField = params.dateStopField;
            this.progressField = params.progressField;
            this.colorField = params.colorField;
            this.taskType = params.taskType;
            this.deadLine = params.deadLine;
            this.showLinks = params.showLinks;
            this.taskPriority = params.taskPriority;

            this.collapseFirstLevel = params.collapseFirstLevel;

    
            this.defaultGroupBy = params.defaultGroupBy ? [params.defaultGroupBy] : [];
            var groupedBy = params.groupedBy;
            if (!groupedBy || !groupedBy.length) {
                groupedBy = this.defaultGroupBy;
            }
            groupedBy = this._dateFilterInGroupedBy(groupedBy);
    
            
            this.gantt = {
                fields: this.fields,
                mapping: this.mapping,
                
                dateStartField: params.dateStartField,
                dateStopField: params.dateStopField,
    
                groupedBy: groupedBy,
                domain: params.domain || [],
                context: params.context || {},
            };
            this._setFocusDate(params.initialDate, params.scale);
            return this._fetchData().then(function () {
                return Promise.resolve();
            });
        },
    
        reload: function (handle, params) {
            if (params.domain) {
                this.gantt.domain = params.domain;
            }
            if (params.context) {
                this.gantt.context = params.context;
            }
    
            if (params.domain) {
                this.domain = params.domain;
            }
    
            this.defaultGroupBy = params.defaultGroupBy ? [params.defaultGroupBy] : [];
            if (params.groupBy) {
                if (params.groupBy && params.groupBy.length) {
                    this.gantt.groupedBy = this._dateFilterInGroupedBy(params.groupBy);
                    if (this.gantt.groupedBy.length !== params.groupBy.length) {
                        this.displayNotification({
                            message: _t('Grouping by date is not supported'),
                            type: 'danger'
                        });
                    }
                } else {
                    this.gantt.groupedBy = this.defaultGroupBy;
                }
            }
            return this._fetchData();
        },
    
        _dateFilterInGroupedBy(groupedBy) {
            var self = this;
            return groupedBy.filter(function(groupedByField)
                {
                    var fieldName = groupedByField.split(':')[0];
                    return fieldName in self.fields && self.fields[fieldName].type.indexOf('date') === -1;
                }
            );
        },
    
        setFocusDate: function (focusDate) {
            this._setFocusDate(focusDate, this.gantt.scale);
        },
    
        setScale: function (scale) {
            this._setFocusDate(this.gantt.focus_date, scale);
        },

        stringDateToServerTime: function (date) {
            var result = date.clone();
            if (!result.isUTC()) {
                result.subtract(session.getTZOffset(date), 'minutes');
            }
            return result.locale('en').format('YYYY-MM-DD HH:mm:ss');
        },

        _getDomain: function () {
            var gannt_start_date = this.stringDateToServerTime(this.gantt.start_date);
            var gannt_to_date = this.stringDateToServerTime(this.gantt.to_date);

            var domain = [
                [this.dateStopField, '<=', gannt_to_date]
            ];
            if (this.fields[this.dateStopField]) {
                domain = domain.concat([
                    '|',
                    [this.dateStartField, ">=", gannt_start_date],
                    [this.dateStopField, '=', false]
                ]);
            }
            return this.domain.concat(domain);
        },
        
        _getFields: function () {
            var self = this;
            var fields = _.values(this.mapping).concat(this.gantt.groupedBy);
            fields.push('display_name','parent_id',this.gantt.dateStartField, this.gantt.dateStopField);
    
            if (this.progressField) {
                fields.push(this.progressField);
            }
    
            if (this.colorField) {
                fields.push(this.colorField);
            }
    
            if (this.taskType) {
                fields.push(this.taskType);
            }
            
            if (this.deadLine) {
                fields.push(this.deadLine);
            }

            if(this.taskPriority){
                fields.push(this.taskPriority);
            }
    
            return _.uniq(fields);
        },
        _fetchData: function () {
            var self = this;
            var domain = self._getDomain();
            var context = Object.assign({}, this.context, { group_by: this.gantt.groupedBy });
            var groupsDef;
            if (this.gantt.groupedBy.length) {
                groupsDef = this._rpc({
                    model: this.modelName,
                    method: 'read_group',
                    fields: this._getFields(),
                    domain: domain,
                    context: context,
                    groupBy: this.gantt.groupedBy,
                    orderBy: this.gantt.groupedBy.map(function (f) { return {name: f}; }),
                    lazy: this.gantt.groupedBy.length === 1,
                });
            }
    
            var dataDef = this._rpc({
                route: '/web/dataset/search_read',
                model: this.modelName,
                fields: this._getFields(),
                context: context,
                domain: domain,
            });

            var linkDef = this._rpc({
                model: this.modelName,
                method: 'search_read_links',
                args: [self.gantt.domain.concat(domain)],
                context: self.gantt.context,
            });

            return this.dp.add(Promise.all([groupsDef, dataDef, linkDef])).then(function (results) {
                const groups = results[0] || [];
                groups.forEach((g) => (g.fromServer = true));
                var searchReadResult = results[1];
                var oldRows = self.allRows;
                self.allRows = {};
                self.gantt.records = self._parseServerData(searchReadResult.records);
                self.gantt.rows = self._generateGanttRows({
                    groupedBy: self.gantt.groupedBy,
                    groups: groups,
                    oldRows: oldRows,
                    parentPath: [],
                    records: self.gantt.records,
                });
                self.gantt.links = results[2];
            })
        },
        _getFormattedFieldValue: function (value, field) {
            var options = {};
            if (field.type === 'boolean') {
                options = {forceString: true};
            }
            let label;
            if (field.type === "many2many") {
                label = Array.isArray(value) ? value[1] : value;
            } else {
                label = fieldUtils.format[field.type](value, field, options);
            }
            return label || _.str.sprintf(_t('Undefined %s'), field.string);
        },
        _getRowName(groupedByField, value) {
            const field = this.fields[groupedByField];
            return this._getFormattedFieldValue(value, field);
        },
        _generateGanttRows(params) {
            const { groupedBy, groups, oldRows, parentPath, records } = params;
            const groupLevel = this.gantt.groupedBy.length - groupedBy.length;
            
            if (!groupedBy.length || !groups.length) {
                const row = {
                    groupLevel,
                    id: JSON.stringify([...parentPath, {}]),
                    isGroup: false,
                    name: "",
                    records,
                };
                this.allRows[row.id] = row;
                return [row];
            }
    
            const rows = [];
            const groupedByField = groupedBy[0];
            const currentLevelGroups = groupBy(groups, group => {
                if (group[groupedByField] === undefined) {
                    group[groupedByField] = false;
                }
                return group[groupedByField];
            });
            const isM2MGrouped = this.gantt.fields[groupedByField].type === "many2many";
            let groupedRecords;
            if (isM2MGrouped) {
                groupedRecords = {};
                for (const [key, currentGroup] of Object.entries(currentLevelGroups)) {
                    groupedRecords[key] = [];
                    const value = currentGroup[0][groupedByField];
                    for (const r of records || []) {
                        if (
                            !value && r[groupedByField].length === 0 ||
                            value && r[groupedByField].includes(value[0])
                        ) {
                            groupedRecords[key].push(r)
                        }
                    }
                }
            } else {
                groupedRecords = groupBy(records || [], groupedByField);
            }
    
            for (const key in currentLevelGroups) {
                const subGroups = currentLevelGroups[key];
                const groupRecords = groupedRecords[key] || [];
                let value;
                if (groupRecords && groupRecords.length && !isM2MGrouped) {
                    value = groupRecords[0][groupedByField];
                } else {
                    value = subGroups[0][groupedByField];
                }
                const part = {};
                part[groupedByField] = value;
                const path = [...parentPath, part];
                const id = JSON.stringify(path);
                const resId = Array.isArray(value) ? value[0] : value;
                const minNbGroups = this.collapseFirstLevel ? 0 : 1;
                const isGroup = groupedBy.length > minNbGroups;
                const fromServer = subGroups.some((g) => g.fromServer);
                const row = {
                    name: this._getRowName(groupedByField, value),
                    groupedBy,
                    groupedByField,
                    groupLevel,
                    id,
                    resId,
                    isGroup,
                    fromServer,
                    isOpen: !findWhere(oldRows, { id: JSON.stringify(parentPath), isOpen: false }),
                    records: groupRecords,
                };
    
                if (isGroup) {
                    row.rows = this._generateGanttRows({
                        ...params,
                        groupedBy: groupedBy.slice(1),
                        groups: subGroups,
                        oldRows,
                        parentPath: path,
                        records: groupRecords,
                    });
                    row.childrenRowIds = [];
                    row.rows.forEach(function (subRow) {
                        row.childrenRowIds.push(subRow.id);
                        row.childrenRowIds = row.childrenRowIds.concat(subRow.childrenRowIds || []);
                    });
                }
    
                rows.push(row);
                this.allRows[row.id] = row;
            }
            return rows;
        },
    
        _parseServerData: function (data) {
            var self = this;
            data.forEach(function (record) {
                Object.keys(record).forEach(function (fieldName) {
                    record[fieldName] = self._parseServerValue(self.fields[fieldName], record[fieldName]);
                });
            });
    
            return data;
        },
    
        _setFocusDate: function (focusDate, scale) {
            this.gantt.scale = scale;
            this.gantt.focus_date = focusDate;
    
            this.gantt.start_date = focusDate.clone().subtract(1, scale).startOf(scale);
            this.gantt.to_date = focusDate.clone().add(3, scale).endOf(scale);
    
            this.gantt.end_date = this.gantt.to_date.add(1, scale);
            this.gantt.date_display = this._dateReformat(focusDate, scale);
        },
    
        _dateReformat: function (date, scale) {
            switch(scale) {                                    
                case "year":
                    return date.format("YYYY");
                case "month":
                    return date.format("MMMM YYYY");
                case "week":
                    var date_start = date.clone().startOf("week").format("D MMM");
                    var date_end = date.clone().endOf("week").format("D MMM");
                    return date_start + " - " + date_end;
                case "day":
                    return date.format("D MMM");
            }
        },
    
    });
    return GanttModel;
    });
    