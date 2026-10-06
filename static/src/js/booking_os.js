odoo.define('qimamhd_booking_v2.booking_os', function(require){
"use strict";
var AbstractAction=require('web.AbstractAction'), core=require('web.core'), rpc=require('web.rpc');
var QWeb=core.qweb;

var BookingOS=AbstractAction.extend({
    template:'QimamBookingOS',
    events:{
        'click .qb_mode':'_switchMode',
        'click .qb_open_halls':'_openHalls',
        'click .qb_open_hotel':'_openHotel',
        'click .qb_new_event':'_newEvent',
        'click .qb_new_stay':'_newStay',
        'click .qb_search_stay':'_searchStay',
        'click .qb_option':'_chooseStay'
    },
    init:function(){this._super.apply(this,arguments);this.data=null;this.mode=null;},
    start:function(){return this._super.apply(this,arguments).then(this._bootstrap.bind(this));},
    _bootstrap:function(){
        var self=this;
        return rpc.query({model:'qimam.booking.workspace.service',method:'bootstrap',args:[]}).then(function(d){
            self.data=d; self.mode=d.company.mode==='hotel'?'hotel':'events';
            self._render();
        });
    },
    _render:function(){
        this.$('.qb_shell_host').html(QWeb.render('QimamBookingOSShell',{data:this.data,mode:this.mode}));
    },
    _switchMode:function(ev){this.mode=$(ev.currentTarget).data('mode');this._render();},
    _openHalls:function(){this.do_action('qimamhd_booking_v2.action_hall_visual_planner');},
    _openHotel:function(){this.do_action('qimamhd_booking_v2.action_hotel_visual_planner');},
    _newEvent:function(){this.do_action('qimamhd_booking_v2.action_booking_studio');},
    _newStay:function(){this.do_action('qimamhd_booking_v2.action_booking_studio');},
    _searchStay:function(){
        var self=this, ci=this.$('.qb_ci').val(), co=this.$('.qb_co').val(), guests=parseInt(this.$('.qb_guests').val()||'1',10);
        if(!ci||!co){this.$('.qb_results').html('<div class="qb_empty">حدد الوصول والمغادرة أولًا</div>');return;}
        this.$('.qb_results').html('<div class="qb_loading">جاري البحث عن أفضل الخيارات…</div>');
        rpc.query({model:'qimam.booking.workspace.service',method:'find_stay_options',args:[ci,co,guests]}).then(function(r){
            self.$('.qb_results').html(QWeb.render('QimamStayOptions',{result:r,ci:ci,co:co}));
        });
    },
    _chooseStay:function(ev){
        var $e=$(ev.currentTarget);
        this.do_action({type:'ir.actions.act_window',name:'حجز إقامة',res_model:'qimam.stay.booking',views:[[false,'form']],target:'current',
            context:{default_resource_id:$e.data('id'),default_checkin_date:$e.data('ci'),default_checkout_date:$e.data('co')}});
    }
});
core.action_registry.add('qimam_booking_os',BookingOS);
return BookingOS;
});
