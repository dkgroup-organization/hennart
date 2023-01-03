odoo.define('web_project_gantt_view.GanttRenderer', function (require) {
    "use strict";
    
    var AbstractRenderer = require('web.AbstractRenderer');
    var core = require('web.core');
    var field_utils = require('web.field_utils');
    var time = require('web.time');
    var concurrency = require('web.concurrency');

    const { findWhere, groupBy } = require('web.utils');
    
    var _lt = core._lt;

    var GanttRenderer = AbstractRenderer.extend({
        className: "o_gantt_view",

        init: function (parent, state, params) {
            this._super.apply(this, arguments);
            var self = this;
            var mapping = this.state.mapping;
            this.gantt_events = [];
            this.modelName = params.modelName;
            this.dateStartField = params.dateStartField;
            this.dateStopField = params.dateStopField;
            this.progressField = params.progressField;
            this.colorField = params.colorField;
            this.taskType = params.taskType;
            this.taskPriority = params.taskPriority;
            this.deadLine = params.deadLine;
            this.showLinks = params.showLinks;
            this.roundDndDates = params.roundDndDates;

            this.dp = new concurrency.DropPrevious();
        },
        
        _configGantt: function () {
            var self = this;          
            //Gantt Configurations
            gantt.config.autosize = "y";
            gantt.config.drag_links = self.showLinks === 'true' ?  true : false;
            gantt.config.drag_progress = false;
            gantt.config.drag_resize = true;
            gantt.config.grid_width = 350;
            gantt.config.row_height = 35;
            gantt.config.duration_unit = "day";
            gantt.config.initial_scroll = true;
            gantt.config.preserve_scroll = true;
            gantt.config.start_on_monday = moment().startOf("week").day();
            gantt.config.start_date = this.state.start_date;
            gantt.config.end_date = this.state.end_date;
            gantt.config.round_dnd_dates = !!this.roundDndDates;
            gantt.config.drag_move = this.edit ? JSON.parse(this.edit) : true;
            gantt.config.sort = true;
            gantt.config.work_time = true;
            gantt.config.skip_off_time = true;

            gantt.plugins({ 
                tooltip: true,
                fullscreen: true,
                marker: true,
                drag_timeline: true,
                fullscreen: true
            });

            gantt.config.columns = [    
                {
                    name: "text",
                    label: _lt("Gantt View"),
                    tree: true,
                    width: "*",
                    resize: true,
                    template: function(task) {
                        var html = '';
                        if (task.deadline && task.end_date) {
                            if ( task.end_date.valueOf() > new Date(moment(task.deadline)).valueOf()) {
                                var endTime = Math.abs(( new Date(task.end_date).getTime() ));
                                var deadLine = Math.abs(( new Date(moment(task.deadline)).getTime() + 86400000 ));
                                var overdue = Math.ceil((endTime - deadLine) / (24 * 60 * 60 * 1000));
                                if (overdue > 0){
                                    html += '<div class="deadline_alert fa fa-exclamation-triangle"></div>';
                                }
                            }
                        }
                        if ((Math.round(task.progress * 100) == 100)) {
                            html += "<div class='progress_alert fa fa-check'></div>";
                        }
                        return html + task.text;
                    },
                },   
                {
                    name: "duration", 
                    label: _lt("Duration(d)"),
                    align: "center", 
                    width: 80, 
                },                                             
            ];
        
            gantt.templates.grid_indent = function () {
                return "<div class='gantt_tree_indent' style='width:20px;'></div>";
            };

            gantt.templates.task_class = function (start, end, task) {
                var classes = ["o_gantt_color" + task.color + "_0"];               
                if (task.is_group) {
                    classes.push("has_child");
                } else {
                    classes.push("is_leaf");
                }
                return classes.join(" ");
            };

            gantt.templates.task_row_class = function (start, end, task) {
                var classes = ["level_" + task.$level];
                return classes;
            };

            gantt.templates.timeline_cell_class = function (item, date) {
                var classes = "date_" + date.getTime();
                var today = new Date();
                if (self.state.scale !== "year" && (date.getDay() === 0 || date.getDay() === 6)) {
                    classes += " weekend_task";
                }
                if (self.state.scale !== "day" && date.getDate() === today.getDate() && date.getMonth() === today.getMonth() && date.getYear() === today.getYear()) {
                    classes += " today";
                }
                return classes;
            };     

            gantt.templates.task_text = function (start, end, task) {                      
                return task.text  + "<span style='text-align:left;'> (" + Math.round(task.progress * 100) + "%)</span>";
            };

            gantt.templates.tooltip_text = function(start,end,task){            
                return "<b>Task:</b> "+task.text+"<br/>" + 
                    "<b>Start date:</b>" + gantt.templates.tooltip_date_format(start) + 
                    "<br/><b>End date:</b> "+gantt.templates.tooltip_date_format(end) +
                    "<br/><b>Progress:</b> "+ (Math.round(task.progress * 100)) + "%";
            };
            
            gantt.templates.grid_folder = function(item) {
                return "<div class='gantt_tree_icon gantt_folder_" +
                (item.$open ? "open" : "closed") + "'></div>";
            };
    
            gantt.templates.grid_file = function(task) {
                var html = '';
                if (!task.is_group){
                    if (task.priority === 'high') {
                        html += "<div class='gantt_tree_icon gantt_file priority_high'></div>";
                    }
                    else if(task.priority === 'low'){
                        html += "<div class='gantt_tree_icon gantt_file priority_low'></div>";
                    }
                    else{
                        html += "<div class='gantt_tree_icon gantt_file priority_normal'></div>";
                    }                           
                }
                return html;
            };

            gantt.templates.link_class = function (link) {
                var types = gantt.config.links;
                switch (link.type) {
                    case types.finish_to_start:
                        return "finish_to_start";
                        break;
                    case types.start_to_start:
                        return "start_to_start";
                        break;
                    case types.finish_to_finish:
                        return "finish_to_finish";
                        break;
                }
            };

            gantt.templates.rightside_text = function (start, end, task) { 
                if (task.deadline) {
                    var text = "";
                    if (end.valueOf() > new Date(moment(task.deadline)).valueOf()) {
                        var endTime = Math.abs(( new Date(end).getTime() ));
                        var deadLine = Math.abs(( new Date(moment(task.deadline)).getTime() + 86400000 ));
                        var overdue = Math.ceil((endTime - deadLine) / (24 * 60 * 60 * 1000));
                        if (overdue > 0){
                            var text = "<b>Overdue: " + overdue + " days</b>";
                        }                        
                        return text;
                    }                   
                }
            };
        },

        _setScaleConfig: function (value) {            
            gantt.config.min_column_width = 48;
            gantt.config.scale_height = 48;
            gantt.config.step = 1;
                                
            switch (value) {
                case "day":                    
                    gantt.config.scale_unit = "day";
                    gantt.config.date_scale = "%d %M";
                    gantt.templates.scale_cell_class = getcss;
                    gantt.config.subscales = [{unit:"hour", step:1, date:"%H h"}];
                    gantt.config.scale_height = 27;
                    break;
                case "week":
                    var weekScaleTemplate = function (date){
                        var dateToStr = gantt.date.date_to_str("%d %M %Y");
                        var endDate = gantt.date.add(gantt.date.add(date, 1, "week"), -1, "day");
                        return dateToStr(date) + " - " + dateToStr(endDate);
                    };
                    gantt.config.scale_unit = "week";
                    gantt.templates.date_scale = weekScaleTemplate;
                    gantt.config.subscales = [{unit:"day", step:1, date:"%d, %D", css:getcss}];
                    break;
                case "month":
                    gantt.config.scale_unit = "month";
                    gantt.config.date_scale = "%F, %Y";
                    gantt.config.subscales = [{unit:"day", step:1, date:"%d", css:getcss}];
                    gantt.config.min_column_width = 25;
                    break;
                case "year":
                    gantt.config.scale_unit = "year";
                    gantt.config.date_scale = "%Y";
                    gantt.config.subscales = [{unit:"month", step:1, date:"%M"}];
                    break;
            }
            function getcss(date) {
                var today = new Date();
                if(date.getDay() === 0 || date.getDay() === 6){
                    return "weekend_scale";
                }
                if(date.getMonth() === today.getMonth() && date.getDate() === today.getDate()){
                    return "today";
                } 
            }
        },

        _render: function () {            
            this._configGantt();
            this._renderGantt();
            return $.when();
        },
        on_attach_callback: function() {
            this._super();
            if(!this.events_set){
                var self = this;
                this._configureGanttEvents();
                this.events_set = true;
            }
            this._renderGantt();
        },
        _renderGantt: function(){
            var self = this;            
            var ganttData = this._renderRows();
            this._renderGanttData(ganttData);
            this._configureGanttEvents();
        },
        
        _renderRows: function(){
            var self = this;
            var ganttData = [];
            var rowWidgets = [];
            var linkWidgets = [];
            
            var build_tasks = function (rows, groupedBy, parent=false) {
                rows.forEach(function (row) {
                    if (groupedBy.length) {
                        if (row.records.length === 0){
                            return;
                        }
                        var project_id = _.uniqueId("gantt_project_");
                        var t = {
                            'id': project_id,
                            'text': row.name,
                            'is_group': true,
                            'start_date':row.group_start,
                            'open': true,
                            'color': '#f4f7f4',
                            'textColor': '#000000',
                            'create': row.create,
                            'is_task': false,
                        }      
                        if (row.records){
                            var progress = 0;
                            _.each(row.records, function (r) {
                                progress  = progress + (r.progress / 100);
                            });
                            t.progress = progress / row.records.length || 0;;
                        }
                        if (parent){
                            t.parent = parent;
                        }
                        rowWidgets.push(t);
                        if (row.isGroup && row.isOpen) {                                    
                            var subRowWidgets = build_tasks(row.rows, groupedBy.slice(1), project_id);   
                            if (subRowWidgets != undefined){
                                rowWidgets = rowWidgets.concat(subRowWidgets);
                            }                            
                        }
                        else{
                            if (row.records){
                                _.each(row.records, function (r) {
                                    var task_id = _.uniqueId("gantt_task_");
                                    rowWidgets.push({
                                        'id': "gantt_task_" + task_id,
                                        'text': r.display_name || '',
                                        'active': r.active || true,
                                        'start_date': self._getTaskStart(r),
                                        'end_date': self._getTaskStop(r),
                                        'progress': self._getTaskProgress(r),
                                        'parent': project_id,
                                        'open': true,
                                        'color': self._getTaskColor(r),
                                        'type':r.type,
                                        'deadline': self._getTaskDeadline(r),
                                        'priority': self._getTaskPriority(r),
                                        'resId': r.id,
                                        'is_task': true,
                                    });
                                });
                            }
                        }
                    }
                    else{
                        if (row.records){
                            _.each(row.records, function (r) {
                                var task_id = _.uniqueId("gantt_task_");
                                var parent_id;
                                if (r.parent_id){
                                    parent_id = "gantt_task_" + r.parent_id[0];
                                }else{
                                    parent_id = parent;
                                }
                                rowWidgets.push({
                                    'id': "gantt_task_" + task_id,
                                    'text': r.display_name || '',
                                    'active': r.active || true,
                                    'start_date': self._getTaskStart(r),
                                    'end_date': self._getTaskStop(r),
                                    'progress': self._getTaskProgress(r),
                                    'open': true,
                                    'color': self._getTaskColor(r),
                                    'type': self._getTaskType(r),
                                    'rollup': true,
                                    'deadline': self._getTaskDeadline(r),
                                    'priority': self._getTaskPriority(r),
                                    'resId': r.id,
                                    'is_task': true,
                                    'parent': parent_id,
                                })                                
                            })
                        } 
                    }
                })
                
            };

            build_tasks(this.state.rows, this.state.groupedBy);
            ganttData['data'] = rowWidgets;

            var _findTaskRow = function(id){  
                var target;
                _.each(rowWidgets, function (row) {
                    for (const key in row) {          
                        if (row['resId'] === id){
                            target = row;
                        }
                    }
                });
                return target;
            };

            var build_links = function(links){
                rowWidgets.forEach(function (row) {                                            
                    if (row.is_task){
                        _.each(links, function (link) {
                            if (link && link.source === row.resId){
                                var target = _findTaskRow(link.target);                                   
                                if (row.id && target && target != undefined && target.id){
                                    linkWidgets.push({
                                        'id' : _.uniqueId("gantt_link_"),
                                        'source' :  row.id,
                                        'target' : target.id,
                                        'type' : link.type,
                                        'link_id': link.id,
                                        'link_source': row.resId,
                                    });
                                }
                            }
                        });
                    }
                });
            };

            if (self.showLinks === 'true'){
                if (this.state.links.length > 0){
                    build_links(this.state.links);
                }                
            }
            
            ganttData['links'] = linkWidgets;
            return ganttData;
        },
        
        _getTaskStop: function(r){
            var self = this;
            var task_stop;
            if (r[self.dateStopField]) {
                task_stop = new Date(moment(r[self.dateStopField]));
                if (self.state.fields[self.dateStopField].type === 'datetime' || self.state.fields[self.dateStopField].type === 'date') {
                    task_stop.setTime(task_stop.getTime() + 86400000);
                }
                if (!task_stop) {
                    task_stop = task_start.clone().add(1, 'hours').toDate();
                }
            }
            return task_stop;
        },
        _getTaskStart: function(r){
            var self = this;
            var task_start;
            if (r[self.dateStartField]) {
                task_start =  new Date(moment(r[self.dateStartField]));
            }                
            else{
                return false;
            }
            return task_start;
        },
        _getTaskProgress: function(r){
            var self = this;
            var progress;
            if (_.isNumber(r[self.progressField])) {
                progress = r[self.progressField] || 0;
            } 
            else {
                progress = 0;
            }
            return progress / 100;
        },
        _getTaskType: function(r){
            var self = this;
            var type;
            if (r[self.taskType]) {
                type = r[self.taskType];
            }else{
                type = 'task';
            }
            return type;
        },
        _getTaskDeadline: function(r){
            var self = this;
            var deadline;
            if (r[self.deadLine]) {
                deadline = r[self.deadLine];
            }
            return deadline;
        },
        _getTaskPriority: function(r){
            var self = this;
            var priority;
            if (r[self.taskPriority]) {
                priority = r[self.taskPriority];
            }
            return priority;
        },
        _getTaskColor: function(r){
            var self = this;
            var color;
            if (r[self.colorField]) {
                if (r[self.colorField] == '1'){
                    color = '#F06050';
                }
                if (r[self.colorField] == '2'){
                    color = '#F4A460';
                }
                if (r[self.colorField] == '3'){
                    color = '#F7CD1F';
                }
                if (r[self.colorField] == '4'){
                    color = '#6CC1ED';
                }
                if (r[self.colorField] == '5'){
                    color = '#814968';
                }
                if (r[self.colorField] == '6'){
                    color = '#EB7E7F';
                }
                if (r[self.colorField] == '7'){
                    color = '#2C8397';
                }
                if (r[self.colorField] == '8'){
                    color = '#475577';
                }
                if (r[self.colorField] == '9'){
                    color = '#D6145F';
                }
                if (r[self.colorField] == '10'){
                    color = '#30C381';
                }
                if (r[self.colorField] == '11'){
                    color = '#9365B8';
                }
            }else{
                color = "#7C7BAD";
            }
            return color;
        },

        _renderGanttData: function (gantt_tasks) {            
            var self = this;            
            var container_height = $('.o_main_navbar').height() + $('.o_control_panel').height() + 80;
            this.$el.get(0).style.minHeight = (window.outerHeight - container_height) + "px";
          
            while (this.gantt_events.length) {
                gantt.detachEvent(this.gantt_events.pop());
            }
            this._setScaleConfig(this.state.scale);            

            gantt.init(this.$el.get(0));
            gantt.clearAll();
            
            gantt.showDate(this.state.focus_date);
            gantt.parse(gantt_tasks);
            
            var dateToStr = gantt.date.date_to_str(gantt.config.task_date);
            var markerId = gantt.addMarker({  
                start_date: new Date(), 
                css: "today", 
                text: "Now", 
                title: dateToStr(new Date()) 
            }); 

            var scroll_state = gantt.getScrollState();
            gantt.scrollTo(scroll_state.x, scroll_state.y);
        },
        
        _configureGanttEvents: function (tasks, grouped_by, groups) {
        
            var self = this;
            
            this.gantt_events.push(gantt.attachEvent("onTaskClick", function (id, e) {                    
                if(gantt.getTask(id).is_group) {
                    return true;
                }                    
                if(gantt.getTask(id)){
                    var task = gantt.getTask(id);
                    self.trigger_up('task_display', task);
                }
                return true;
            }));
    
            this.gantt_events.push(gantt.attachEvent("onTaskDblClick", function (){ 
                return false; 
            }));
            
            this.gantt_events.push(gantt.attachEvent("onBeforeTaskSelected", function (id) {
                if(gantt.getTask(id).is_group){   
                    if($("[task_id="+id+"] .gantt_tree_icon")){
                        $("[task_id="+id+"] .gantt_tree_icon").click();
                        return false;
                    }                                        
                }
                return true;
            }));

            var parent_date_update = function (id) {
                var start_date, stop_date;
                var clicked_task = gantt.getTask(id);
                
                if (!clicked_task.parent) {
                    return;
                }
    
                var parent = gantt.getTask(clicked_task.parent);
    
                _.each(gantt.getChildren(parent.id), function (task_id){
                    var task_start_date = gantt.getTask(task_id).start_date;
                    var task_stop_date = gantt.getTask(task_id).end_date;
                    if(!start_date){
                        start_date = task_start_date;
                    }
                    if(!stop_date){
                        stop_date = task_stop_date;
                    }
                    if(start_date > task_start_date){
                        start_date = task_start_date;
                    }
                    if(stop_date < task_stop_date){
                        stop_date = task_stop_date;
                    }
                });

                parent.start_date = start_date;
                parent.end_date = stop_date;
                gantt.updateTask(parent.id);
                if (parent.parent) parent_date_update(parent.id);
            };
            
            this.gantt_events.push(gantt.attachEvent("onBeforeTaskDrag", function (id, mode, e){
                var task = gantt.getTask(id);
                task._start_date_original = task.start_date;
                task._end_date_original = task.end_date;
                this.lastX = e.pageX;
                
                if (task.is_group) {
                    var attr = e.target.attributes.getNamedItem("consolidation_ids");
                    if (attr) {
                        var children = attr.value.split(" ");
                        this.drag_child = children;
                        _.each(this.drag_child, function (child_id) {
                            var child = gantt.getTask(child_id);
                            child._start_date_original = child.start_date;
                            child._end_date_original = child.end_date;
                        });
                    }
                }
                return true;
            }));
            
            this.gantt_events.push(gantt.attachEvent("onTaskDrag", function (id, mode, task, original, e){
                if(gantt.getTask(id).is_group){
                    var day;                                                        
                    if (self.state.scale === "year") {
                        day = 51840000;
                    }
                    if (self.state.scale === "month") {
                        day = 3456000;
                    }
                    if (self.state.scale === "week") {
                        day = 1728000;
                    }
                    if (self.state.scale === "day") {
                        day = 72000;
                    }
                    
                    var diff = (e.pageX - this.lastX) * day;
                    this.lastX = e.pageX;
    
                    if (task.start_date > original.start_date){ 
                        task.start_date = original.start_date; 
                    }
                    if (task.end_date < original.end_date){ 
                        task.end_date = original.end_date; 
                    }
    
                    if (this.drag_child){
                        _.each(this.drag_child, function (child_id){
                            var child = gantt.getTask(child_id);
                            var new_start = +child.start_date + diff;
                            var new_stop = +child.end_date + diff;
                            if (new_start < gantt.config.start_date || new_stop > gantt.config.end_date){
                                return false;
                            }
                            child.start_date = new Date(new_start);
                            child.end_date = new Date(new_stop);
                            gantt.updateTask(child.id);
                            parent_date_update(child_id);
                        });
                    }
                    gantt.updateTask(task.id);
                    return false;
                }
                parent_date_update(id);
                return true;
            }));
    
            this.gantt_events.push(gantt.attachEvent("onAfterTaskDrag", function (id){
                var update_task = function (task_id) {
                    var task = gantt.getTask(task_id);
                    self.trigger_up('task_update', {
                        task: task,
                        success: function () {
                            parent_date_update(task_id);
                        },
                        fail: function () {
                            task.start_date = task._start_date_original;
                            task.end_date = task._end_date_original;
                            gantt.updateTask(task_id);
                            delete task._start_date_original;
                            delete task._end_date_original;
                            parent_date_update(task_id);
                        }
                    });
                };
    
                if (gantt.getTask(id).is_group && this.drag_child) {
                    _.each(this.drag_child, function (child_id) {
                        update_task(child_id);
                    });
                }
                update_task(id);
            }));
                       
            this.gantt_events.push(gantt.attachEvent("onAfterLinkAdd", function(id,item){     
                var crate_link = function (item) {                    
                    self.trigger_up('crate_link', {
                        link: item,
                        success: function (newID) {
                            if (newID){
                                var id  = _.uniqueId("gantt_link_");
                                gantt.changeLinkId(item.id, id);
                                gantt.getLink(id).link_id = newID;
                                gantt.updateLink(id);                    
                            }                            
                        },
                        fail: function () {},
                    });
                };
                var sourceTask = gantt.getTask(item.source);  
                var targetTask = gantt.getTask(item.target);
                var t = {
                    'id' : item.id,
                    'source' :  item.source,
                    'target' : item.target,
                    'type' : item.type,
                    'link_source': sourceTask.resId,
                    'link_target': targetTask.resId,
                }
                crate_link(t);
            }));  

            this.gantt_events.push(gantt.attachEvent("onAfterLinkDelete", function(id,item){
                var delete_link = function (item) {
                    self.trigger_up('delete_link', {
                        link: item,
                        success: function (result) {
                            if (result){
                                var links = gantt.getLinks();
                                if (links.length > 0){
                                    _.each(links, function (link){
                                        if (link.link_id === item.link_id){
                                            gantt.deleteLink(link.id);
                                        }
                                    });
                                }
                            }                            
                        },
                        fail: function () {

                        }
                    });
                };
                delete_link(item);
            }));  
			
			this.gantt_events.push(gantt.attachEvent("onBeforeLinkAdd", function(id,item){                
				var sourceTask = gantt.getTask(item.source);
                var targetTask = gantt.getTask(item.target);
				if (sourceTask.is_group) {
                    gantt.message({type:"error", text:"You can't create link task with group."});
					return false;
				}
                if(sourceTask.parent != targetTask.parent){
                    gantt.message({type:"error", text:"You can't create link with other project task / parent task."});
                    return false;
                }
				return true;
			}));            
        },

        destroy: function () {
            while (this.gantt_events.length) {
                gantt.detachEvent(this.gantt_events.pop());
            }
            this._super();
        },
    });
    return GanttRenderer;
});
