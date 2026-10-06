odoo.define('qimamhd_booking_v2.mission_control',function(require){
"use strict";
var AbstractAction=require('web.AbstractAction'),core=require('web.core'),rpc=require('web.rpc');var QWeb=core.qweb;
var Mission=AbstractAction.extend({
 template:'QimamMissionControl',
 events:{'click .qm_generate':'_generate','click .qm_item_action':'_item','click .qm_start_event':'_startEvent','click .qm_open':'_open'},
 init:function(parent,action){this._super.apply(this,arguments);this.booking_id=(action.context||{}).active_id;},
 start:function(){return this._super.apply(this,arguments).then(this._load.bind(this));},
 _paint:function(d){this.data=d;this.$('.qm_host').html(QWeb.render('QimamMissionControlBody',{d:d}));},
 _load:function(){var self=this;return rpc.query({model:'qimam.booking.mission.control',method:'board',args:[this.booking_id]}).then(this._paint.bind(this));},
 _generate:function(){var self=this;return rpc.query({model:'qimam.booking.mission.control',method:'generate',args:[this.booking_id]}).then(this._paint.bind(this));},
 _item:function(ev){var self=this,$e=$(ev.currentTarget);return rpc.query({model:'qimam.booking.mission.control',method:'item_action',args:[this.booking_id,$e.data('id'),$e.data('action')]}).then(this._paint.bind(this));},
 _startEvent:function(){var self=this;return rpc.query({model:'qimam.booking.mission.control',method:'start_event',args:[this.booking_id]}).then(function(d){self._paint(d);self.do_notify('التشغيل','تم بدء المناسبة.');});},
 _open:function(){this.do_action({type:'ir.actions.act_window',res_model:'qimam.booking',res_id:this.booking_id,views:[[false,'form']],target:'current'});}
});core.action_registry.add('qimam_mission_control',Mission);return Mission;
});
