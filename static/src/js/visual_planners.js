odoo.define('qimamhd_booking_v2.visual_planners', function (require) {
    "use strict";
    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var rpc = require('web.rpc');
    var QWeb = core.qweb;

    function isoDate(d) {
        var y=d.getFullYear(), m=('0'+(d.getMonth()+1)).slice(-2), day=('0'+d.getDate()).slice(-2);
        return y+'-'+m+'-'+day;
    }

    var HallPlanner = AbstractAction.extend({
        template: 'QimamHallPlanner',
        events: {
            'click .o_qimam_prev':'_prev', 'click .o_qimam_next':'_next',
            'click .o_qimam_today':'_today', 'click .o_qimam_day':'_openDay'
        },
        init: function () { this._super.apply(this, arguments); var n=new Date(); this.year=n.getFullYear(); this.month=n.getMonth()+1; },
        start: function () { return this._super.apply(this, arguments).then(this._load.bind(this)); },
        _load: function () {
            var self=this;
            return rpc.query({model:'qimam.booking.calendar.service',method:'get_hall_month',args:[this.year,this.month]})
            .then(function(data){ self.$('.o_qimam_planner_body').html(QWeb.render('QimamHallMonth',{data:data})); });
        },
        _prev:function(){ this.month--; if(this.month<1){this.month=12;this.year--;} return this._load(); },
        _next:function(){ this.month++; if(this.month>12){this.month=1;this.year++;} return this._load(); },
        _today:function(){var n=new Date();this.year=n.getFullYear();this.month=n.getMonth()+1;return this._load();},
        _openDay:function(ev){
            var date=$(ev.currentTarget).data('date');
            this.do_action({type:'ir.actions.act_window',name:'توفر القاعات',res_model:'qimam.booking.availability.wizard',
                views:[[false,'form']],target:'current',context:{default_booking_date:date}});
        }
    });

    var HotelPlanner = AbstractAction.extend({
        template:'QimamHotelPlanner',
        events:{
            'click .o_qimam_prev':'_prev','click .o_qimam_next':'_next','click .o_qimam_today':'_today',
            'click .o_qimam_room_cell':'_cell','click .o_qimam_stay_bar':'_bar'
        },
        init:function(){this._super.apply(this,arguments);this.startDate=new Date();this.days=14;},
        start:function(){return this._super.apply(this,arguments).then(this._load.bind(this));},
        _load:function(){
            var self=this;
            return rpc.query({model:'qimam.booking.calendar.service',method:'get_stay_timeline',args:[isoDate(this.startDate),this.days]})
            .then(function(data){self.$('.o_qimam_planner_body').html(QWeb.render('QimamHotelTimeline',{data:data}));});
        },
        _prev:function(){this.startDate.setDate(this.startDate.getDate()-7);return this._load();},
        _next:function(){this.startDate.setDate(this.startDate.getDate()+7);return this._load();},
        _today:function(){this.startDate=new Date();return this._load();},
        _bar:function(ev){
            ev.stopPropagation();
            var stay=$(ev.currentTarget).data('stay'), self=this;
            return rpc.query({model:'qimam.booking.workspace.service',method:'booking_preview',args:['qimam.stay.booking',stay]}).then(function(d){
                self.$('.o_qimam_drawer_host').remove();
                self.$el.append('<div class="o_qimam_drawer_host open">'+QWeb.render('QimamBookingDrawer',{r:d})+'</div>');
                self.$('.qo_close').on('click',function(){self.$('.o_qimam_drawer_host').remove();});
                self.$('.qo_open').on('click',function(){self.do_action({type:'ir.actions.act_window',res_model:'qimam.stay.booking',res_id:stay,views:[[false,'form']],target:'current'});});
            });
        },
        _cell:function(ev){
            var $c=$(ev.currentTarget), stay=$c.data('stay'), resource=$c.data('resource'), date=$c.data('date');
            if(stay){
                var self=this;
                return rpc.query({model:'qimam.booking.workspace.service',method:'booking_preview',args:['qimam.stay.booking',stay]}).then(function(d){
                    self.$('.o_qimam_drawer_host').remove();
                    self.$el.append('<div class="o_qimam_drawer_host open">'+QWeb.render('QimamBookingDrawer',{r:d})+'</div>');
                    self.$('.qo_close').on('click',function(){self.$('.o_qimam_drawer_host').remove();});
                    self.$('.qo_open').on('click',function(){self.do_action({type:'ir.actions.act_window',res_model:'qimam.stay.booking',res_id:stay,views:[[false,'form']],target:'current'});});
                });
            }
            var end=new Date(date+'T12:00:00');end.setDate(end.getDate()+1);
            return this.do_action({type:'ir.actions.act_window',name:'حجز إقامة',res_model:'qimam.stay.booking',
                views:[[false,'form']],target:'current',context:{default_resource_id:resource,default_checkin_date:date,default_checkout_date:isoDate(end)}});
        }
    });

    core.action_registry.add('qimam_hall_planner', HallPlanner);
    core.action_registry.add('qimam_hotel_planner', HotelPlanner);
    return {HallPlanner:HallPlanner,HotelPlanner:HotelPlanner};
});
