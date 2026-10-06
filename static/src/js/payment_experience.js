odoo.define('qimamhd_booking_v2.payment_experience',function(require){
"use strict";
var AbstractAction=require('web.AbstractAction'),core=require('web.core'),rpc=require('web.rpc');var QWeb=core.qweb;
var PaymentExperience=AbstractAction.extend({
 template:'QimamPaymentExperience',
 events:{'click .qp_confirm':'_confirm','click .qp_schedule':'_schedule','click .qp_open':'_open','click .qp_refresh':'_load'},
 init:function(parent,action){this._super.apply(this,arguments);this.booking_id=(action.context||{}).active_id||(action.params||{}).booking_id;},
 start:function(){return this._super.apply(this,arguments).then(this._load.bind(this));},
 _load:function(){var self=this;if(!this.booking_id)return Promise.resolve();return rpc.query({model:'qimam.booking.payment.experience',method:'snapshot',args:[this.booking_id]}).then(function(d){self.data=d;self.$('.qp_host').html(QWeb.render('QimamPaymentExperienceBody',{d:d}));});},
 _schedule:function(){var self=this,mode=this.$('.qp_mode').val(),pct=parseFloat(this.$('.qp_pct').val()||30),count=parseInt(this.$('.qp_count').val()||3,10),date=this.$('.qp_first').val();return rpc.query({model:'qimam.booking.payment.experience',method:'build_schedule',args:[this.booking_id,mode,pct,count,date,1]}).then(function(d){self.data=d;self.$('.qp_host').html(QWeb.render('QimamPaymentExperienceBody',{d:d}));});},
 _confirm:function(){var self=this;return rpc.query({model:'qimam.booking.payment.experience',method:'confirm',args:[this.booking_id]}).then(function(d){self.data=d;self.$('.qp_host').html(QWeb.render('QimamPaymentExperienceBody',{d:d}));self.do_notify('الحجز','تم تأكيد الحجز وفق سياسة المنشأة.');});},
 _open:function(){this.do_action({type:'ir.actions.act_window',res_model:'qimam.booking',res_id:this.booking_id,views:[[false,'form']],target:'current'});}
});
core.action_registry.add('qimam_payment_experience',PaymentExperience);return PaymentExperience;
});
