odoo.define('web_project_gantt_view.GanttController', function (require) {
    "use strict";

    let __exports = {};

    var AbstractController = require('web.AbstractController');
    var core = require('web.core');
    var config = require('web.config');
    var Dialog = require('web.Dialog');
    var dialogs = require('web.view_dialogs');
    var time = require('web.time');
    var session = require('web.session');

    var _t = core._t;
    var qweb = core.qweb;

    const { FormViewDialog } = require("@web/views/view_dialogs/form_view_dialog");
    const { Component } = owl;

    var n_direction = false;

    var GanttController = AbstractController.extend({
        events: {
            'click .gantt_task_row .gantt_task_cell': '_onCreateClick',            
            'click .o_gantt_scale_button': '_onScaleClick',
            'click .o_gantt_new_button': '_onNewClick',
            'click .o_gantt_today_button': '_onTodayClick',
            'click .o_gantt_left_button': '_onPreviousClick',
            'click .o_gantt_right_button': '_onNextClick',
            'click .o_gantt_sort_button': '_onSortClick',        
            'click .o_gantt_export_pdf': '_onExportPDFClick',
            'click .o_gantt_export_png': '_onExportPNGClick',
        },
        custom_events: _.extend({}, AbstractController.prototype.custom_events, {
            task_update: '_onTaskUpdate',
            task_display: '_onTaskDisplay',
            task_create: '_onTaskCreate',
            crate_link: '_onCreateLink',
            delete_link: '_onDeleteLink',
        }),

        init: function (parent, model, renderer, params) {
            this._super.apply(this, arguments);     
            this.set('title', params.displayName);   
            this.context = params.context;
            this.displayName = params.displayName;
            this.dateStartField = params.dateStartField;
            this.dateStopField = params.dateStopField;
            this.linkModel = params.linkModel;
        },

        getTitle: function () {
            return this.get('title');
        },

        renderButtons: function ($node) {
            var self = this;
            this.$buttons = $(qweb.render("WebGanttView.buttons", {'isMobile': config.device.isMobile}));
            if ($node) {
                this.$buttons.appendTo($node);
            }
        },  

        _onScaleClick: function(event){
            var self = this;
            self.$buttons.find('.o_gantt_scale_dropdown_button').text($(this).text());
            self.$buttons.find('.o_gantt_scale_button').removeClass('active');
            var scale = $(event.target).data('value');
            self._updateButtons(scale);
            return self._setScale($(event.target).data('value'));
        },
        
        _updateButtons: function(scale){
            var self = this;
            if (!self.$buttons) {
                return;
            }
            self.$buttons.find('.o_gantt_scale_button[data-value="' + scale + '"]').addClass('active');
        },

        _onTodayClick: function(){
            var self = this;
            self.model.setFocusDate(moment(new Date()));
            return self.reload();
        },

        _onPreviousClick: function(){
            var self = this;
            var state = self.model.get();
            self._setFocusDate(state.focus_date.subtract(1, state.scale));
        },
        _onNextClick: function(){
            var self = this;
            var state = self.model.get();
            self._setFocusDate(state.focus_date.add(1, state.scale));
        },

        _setScale: function (scale) {
            var self = this;
            this.model.setScale(scale);
            self.set('title', self.displayName + ' (' + self.model.get().date_display + ')');
            this.reload();
        },

        _onCreateClick: function (event) {
            if (this.activeActions.create) {
                
                var context = _.clone(this.context);
                var id = event.target.parentElement.attributes.task_id.value;
                var task = gantt.getTask(id);
                var classDate = _.find(event.target.classList, function (e) {
                    return e.indexOf("date_") > -1;
                });
                
                var startDate = moment(new Date(parseInt(classDate.split("_")[1], 10))).utc();
                var endDate;
                switch (this.model.get().scale) {
                    case "day":
                        endDate = startDate.clone().add(4, "hour");
                        break;
                    case "week":
                        endDate = startDate.clone().add(2, "day");
                        break;
                    case "month":
                        endDate = startDate.clone().add(4, "day");
                        break;
                    case "year":
                        endDate = startDate.clone().add(2, "month");
                        break;
                }
                
                var get_create = function (item) {
                    if (item.create) {
                        context["default_"+item.create[0]] = item.create[1][0];
                    }
                    if (item.parent) {
                        var parent = gantt.getTask(item.parent);
                        get_create(parent);
                    }
                };
                get_create(task);

                context["default_"+this.dateStartField] = startDate.format("YYYY-MM-DD HH:mm:ss");
                if (this.dateStopField) {
                    context["default_"+this.dateStopField] = endDate.format("YYYY-MM-DD HH:mm:ss");
                } 
                else {
                    context["default_"+this.model.mapping.date_delay] = gantt.calculateDuration(startDate, endDate);
                }

                context.id = 0;

                const state = this.model.get(this.handle, { raw: true });
                Component.env.services.dialog.add(FormViewDialog, {
                    resModel: this.modelName,
                    context: session.user_context,
                    onRecordSaved: () => {
                        this.reload(state);
                    }
                }, {});
            }
        },

        _onTaskUpdate: function (event) {
            var taskObj = event.data.task;
            var success = event.data.success;
            var fail = event.data.fail;
            var fields = this.model.fields;
            
            if (fields[this.dateStopField] === undefined) {
                    Dialog.alert(this, _t('You have no date_stop field defined!'));
                return fail();
            }

            if (fields[this.dateStartField].readonly || fields[this.dateStopField].readonly) {
                Dialog.alert(this, _t('You are trying to write on a read-only field!'));
                return fail();
            }

            var start = taskObj.start_date;
            var end = taskObj.end_date;
            
            var data = {};
            data[this.dateStartField] = time.auto_date_to_str(start, fields[this.dateStartField].type);
            if (this.dateStopField) {
                var field_type = fields[this.dateStopField].type;
                if (field_type === 'date') {
                    end.setTime(end.getTime() - 86400000);
                    data[this.dateStopField] = time.auto_date_to_str(end, field_type);
                    end.setTime(end.getTime() + 86400000);
                } else {
                    data[this.dateStopField] = time.auto_date_to_str(end, field_type);
                }
            } 
            
            var taskId = parseInt(taskObj.resId);

            this._rpc({
                model: this.model.modelName,
                method: 'write',
                args: [taskId, data],
            })
            .then(success, fail);
        },

        _onTaskCreate: function () {
            if (this.activeActions.create) {
                var startDate = moment(new Date()).utc();
                this._createTask(0, startDate);
            }
        },
        
        _onCreateLink: function (item) {
            var linkObj = item.data.link;
            var success = item.data.success;
            var fail = item.data.fail;
            
            var linkSourceId = parseInt(linkObj.link_source);
            var linkTargetId = parseInt(linkObj.link_target);            
            var linkType = linkObj.type || 0;

            var args = [{
                'task_id' : linkSourceId,
                'target_task_id' : linkTargetId,
                'link_type' : linkType,
            }];
            
            return this._rpc({
                model: this.linkModel,
                method: 'create',
                args: args,
            }).then(success, fail);
        },

        _onDeleteLink: function (item) {
            var linkObj = item.data.link;
            var success = item.data.success;
            var fail = item.data.fail;

            var Id = parseInt(linkObj.link_id);
            
            return this._rpc({
                model: this.linkModel,
                method: 'unlink',
                args: [Id],
            }).then(success, fail);
        },

        _onTaskDisplay: function (task) {
            var readonly = this.is_action_enabled('edit') ? "edit" : "readonly";
            this._displayTask(task.data, readonly);
        },

        _displayTask: function (task, readonly) {
            var taskId = parseInt(task.resId);
            readonly = readonly ? readonly : false;
            const state = this.model.get(this.handle, { raw: true });

            Component.env.services.dialog.add(FormViewDialog, {
                resModel: this.modelName,
                resId: taskId,
                mode: readonly,
                context: session.user_context,
                onRecordSaved: () => {
                    this.reload(state);
                }
            }, {});
        },
    
        _setFocusDate: function (focusDate) {
            var self = this;
            this.model.setFocusDate(focusDate);
            self.set('title', self.displayName + ' (' + self.model.get().date_display + ')');
            this.reload();
        },

        _onNewClick: function (event) {
            var context = _.clone(this.context);
            var startDate = moment(new Date()).utc();
            var endDate;
            switch (this.model.get().scale) {
                case "day":
                    endDate = startDate.clone().add(4, "hour");
                    break;
                case "week":
                    endDate = startDate.clone().add(2, "day");
                    break;
                case "month":
                    endDate = startDate.clone().add(4, "day");
                    break;
                case "year":
                    endDate = startDate.clone().add(2, "month");
                    break;
            }
            
            context["default_"+ this.dateStartField] = startDate.format("YYYY-MM-DD HH:mm:ss");
            if (this.dateStopField) {
                context["default_"+ this.dateStopField] = endDate.format("YYYY-MM-DD HH:mm:ss");
            } 

            const state = this.model.get(this.handle, { raw: true });

            Component.env.services.dialog.add(FormViewDialog, {
                resModel: this.modelName,
                context: session.user_context,
                onRecordSaved: () => {
                    this.reload(state);
                }
            }, {});
        },
        
        _onSortClick: _.debounce(function(event){
            event.preventDefault();        
            if (n_direction){
                gantt.sort("id",false);
            } 
            else {
                gantt.sort("id",true);
            }
            n_direction = !n_direction;
        }, 200, true),

        _onExportPNGClick: _.debounce(function(event){
            event.preventDefault();
            this._onExportOpen('png')        
        }, 200, true),

        _onExportPDFClick: _.debounce(function(event){
            event.preventDefault();    
            this._onExportOpen('pdf')
        }, 200, true),

        stringDateToServerTime: function (date) {
            var clone = date.clone();
            if (!clone.isUTC()) {
                clone.subtract(session.getTZOffset(date), 'minutes');
            }
            return clone.locale('en').format('YYYY-MM-DD HH:mm:ss');
        },

        _onExportOpen(format){
            var self = this;
            var format = format;
            var $content = `<div class='form-group'>
                <label for='startDate'>Start Date</label>
                <input type='text' id="startDate" class='form-control'>
                </div>
                <div class='form-group'>
                <label for='endDate'>End Date</label>
                <input type='text' id="endDate" class='form-control'>
                </div>`;
            this.exportToDialog = new Dialog(this, {
                size: 'small',
                title: _t('Export PDF'),
                $content: $content,
                buttons: [
                    {
                        text: _t('Set Date'),  
                        classes: 'btn-primary',  
                        close: false,  
                        click: function () {
                            var date_start = this.$el.find('#startDate');
                            var date_end = this.$el.find('#endDate');
                            
                            if (!date_start.val()){  
                                date_start[0].style.borderColor = '#ff0000';
                                return;
                            }else{
                                date_start[0].style.borderColor = '#ced4da';
                            }
                            if (!date_end.val()){  
                                date_end[0].style.borderColor = '#ff0000';
                                return;
                            }else{
                                date_end[0].style.borderColor = '#ced4da';
                            }

                            if (Date.parse(date_start.val())  >=  Date.parse(date_end.val())){
                                self.displayNotification({ message: _t('Start date must be anterior to end date!'), type: 'warning' });
                                return;
                            }

                            var scale = self.model.get().scale;
                            var DateStart = moment(date_start.val());
                            var DateEnd = moment(date_end.val());

                            self.model.gantt.start_date = DateStart.clone().startOf(scale);
                            self.model.gantt.to_date = DateEnd.clone().endOf(scale);

                            self.model._fetchData();   
                            self.reload();

                            gantt.config.start_date = self.stringDateToServerTime(DateStart);
                            gantt.config.min_date = self.stringDateToServerTime(DateStart);
                            gantt.render();
                            
                            if (date_start && date_end){
                                $('.export_gantt').removeClass('d-none');
                            }                            
                        }
                    },
                    {
                        text: _t('Export'),  
                        classes: 'btn-primary export_gantt d-none',  
                        close: false,
                        click: function () {
                            var date_start = this.$el.find('#startDate');
                            var date_end = this.$el.find('#endDate');

                            if (!date_start.val()){  
                                date_start[0].style.borderColor = '#ff0000';
                                return;
                            }else{
                                date_start[0].style.borderColor = '#ced4da';
                            }
                            if (!date_end.val()){  
                                date_end[0].style.borderColor = '#ff0000';
                                return;
                            }else{
                                date_end[0].style.borderColor = '#ced4da';
                            }

                            if (Date.parse(date_start.val())  >=  Date.parse(date_end.val())){
                                self.displayNotification({ message: _t('Start date must be anterior to end date!'), type: 'warning' });
                                return;
                            }

                            var DateStart = moment(date_start.val());
                            var DateEnd = moment(date_end.val());

                            var date_start = DateStart.locale('en').format("DD-MM-YYYY");
                            var date_end = DateEnd.locale('en').format("DD-MM-YYYY");
                            
                            if(format === 'pdf'){
                                gantt.exportToPDF({
                                    name: date_start + "_" + date_end + ".pdf",
                                    start: date_start,
                                    end: date_end,
                                });
                                self.exportToDialog.close();
                            }else if(format === 'png'){
                                gantt.exportToPNG({
                                    name: date_start + "_" + date_end + ".png",
                                    start: date_start,
                                    end: date_end,
                                });
                                self.exportToDialog.close();
                            }else{
                                self.displayNotification({ message: _t('The export format has not been specified!'), type: 'warning' });
                            }
                        },
                    },
                    {
                        text: _t('Discard'), 
                        close: true
                    }
                ],
            });
            this.exportToDialog.opened().then(function () {
                $('.export_gantt').hide();

                self.exportToDialog.$("#startDate").datepicker({
                    dateFormat: 'yy-mm-dd',
                });
                self.exportToDialog.$("#endDate").datepicker({
                    dateFormat: 'yy-mm-dd',
                });

                self.exportToDialog.$("#startDate").on('change', function(){
                    if(!self.exportToDialog.$("#startDate").val()){
                        $('.export_gantt').hide();
                    }
                    else {
                        $('.export_gantt').show();
                    }
                });

                self.exportToDialog.$("#endDate").on('change', function(){
                    if(!self.exportToDialog.$("#endDate").val()){
                        $('.export_gantt').hide();
                    }
                    else {
                        $('.export_gantt').show();
                    }
                });
            });
            this.exportToDialog.open();
        },
    });
    return GanttController;
});
