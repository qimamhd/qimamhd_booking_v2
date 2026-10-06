odoo.define('qimamhd_booking_v2.booking_studio', function(require){
"use strict";
var AbstractAction=require('web.AbstractAction'),core=require('web.core'),rpc=require('web.rpc');
var QWeb=core.qweb;

var Studio=AbstractAction.extend({
 template:'QimamBookingStudio',
 events:{
  'click .qs_mode':'_mode','click .qs_customer':'_customer','input .qs_customer_search':'_searchCustomer',
  'click .qs_period':'_period','click .qs_event_quote':'_eventQuote','click .qs_stay_quote':'_stayQuote',
  'click .qs_room':'_room','click .qs_back':'_back','click .qs_continue':'_continue',
  'click .qs_create':'_create','click .qs_done_open':'_openDone','click .qs_restart':'_restart','click .qs_add_service':'_addService','click .qs_remove_service':'_removeService','click .qs_apply_package':'_package','click .qs_requote':'_requote','click .qs_finish_commercial':'_finishCommercial','click .qs_payment_next':'_paymentNext'
 },
 init:function(){this._super.apply(this,arguments);this.mode=null;this.step=1;this.data=null;this.pick={period_ids:[]};this.done=null;this.catalog=null;this.commercial={items:[],discount_type:'none',discount_value:0};},
 start:function(){return this._super.apply(this,arguments).then(this._boot.bind(this));},
 _boot:function(mode){var self=this;return rpc.query({model:'qimam.booking.studio.service',method:'bootstrap',args:[mode||null]}).then(function(d){self.data=d;self.mode=d.mode;self.step=1;self.pick={period_ids:[]};self.done=null;self.catalog=null;self.commercial={items:[],discount_type:'none',discount_value:0};self._render();});},
 _render:function(){this.$('.qs_host').html(QWeb.render('QimamBookingStudioBody',{d:this.data,mode:this.mode,step:this.step,p:this.pick,done:this.done,catalog:this.catalog,commercial:this.commercial}));},
 _mode:function(ev){this._boot($(ev.currentTarget).data('mode'));},
 _customer:function(ev){this.pick.partner_id=$(ev.currentTarget).data('id');this.pick.partner_name=$(ev.currentTarget).data('name');this._render();},
 _searchCustomer:function(ev){var self=this,q=$(ev.currentTarget).val();clearTimeout(this.timer);this.timer=setTimeout(function(){rpc.query({model:'qimam.booking.studio.service',method:'search_customers',args:[q]}).then(function(r){self.data.customers=r;self._render();self.$('.qs_customer_search').val(q).focus();});},250);},
 _period:function(ev){var id=parseInt($(ev.currentTarget).data('id'),10),a=this.pick.period_ids,i=a.indexOf(id);if(i>=0)a.splice(i,1);else a.push(id);$(ev.currentTarget).toggleClass('selected');},
 _continue:function(){if(this.step===1&&!this.pick.partner_id){this._msg('اختر العميل أولًا');return;}this.step=Math.min(this.step+1,4);this._render();},
 _back:function(){this.step=Math.max(this.step-1,1);this._render();},
 _eventQuote:function(){
   var self=this,date=this.$('.qs_date').val(),hall=parseInt(this.$('.qs_hall').val()||0,10);
   this.pick.booking_date=date;this.pick.hall_id=hall;
   rpc.query({model:'qimam.booking.studio.service',method:'event_quote',args:[date,hall,this.pick.period_ids]}).then(function(q){
     self.pick.quote=q;if(q.ok){self.pick.hall_name=q.hall.name;self.step=4;}else{self._msg(q.message);}self._render();
   });
 },
 _stayQuote:function(){
   var self=this,ci=this.$('.qs_ci').val(),co=this.$('.qs_co').val(),ad=parseInt(this.$('.qs_adults').val()||1,10),ch=parseInt(this.$('.qs_children').val()||0,10);
   this.pick.checkin_date=ci;this.pick.checkout_date=co;this.pick.adults=ad;this.pick.children=ch;
   rpc.query({model:'qimam.booking.studio.service',method:'stay_quote',args:[ci,co,ad+ch]}).then(function(q){self.pick.stay_quote=q;self.step=3;self._render();});
 },
 _room:function(ev){this.pick.resource_id=parseInt($(ev.currentTarget).data('id'),10);this.pick.resource_name=$(ev.currentTarget).data('name');this.pick.total=$(ev.currentTarget).data('total');this.step=4;this._render();},
 _create:function(ev){
   var self=this,hold=$(ev.currentTarget).data('hold')===1,method=this.mode==='events'?'create_event':'create_stay';
   var payload=$.extend({},this.pick,{hold:hold});
   this.$('.qs_create').prop('disabled',true);
   rpc.query({model:'qimam.booking.studio.service',method:method,args:[payload]}).then(function(r){
     self.done=r;
     if(self.mode==='events'){
       rpc.query({model:'qimam.booking.commercial.service',method:'catalog',args:[]}).then(function(c){self.catalog=c;self.step=5;self._requote();});
     }else{self.step=6;self._render();}
   });
 },
 _addService:function(ev){var id=parseInt($(ev.currentTarget).data('id'),10),found=this.commercial.items.filter(function(x){return x.id===id;})[0];if(found)found.qty+=1;else this.commercial.items.push({id:id,qty:1});this._requote();},
 _removeService:function(ev){var id=parseInt($(ev.currentTarget).data('id'),10);this.commercial.items=this.commercial.items.filter(function(x){return x.id!==id;});this._requote();},
 _package:function(ev){var id=parseInt($(ev.currentTarget).data('id'),10),pkg=this.catalog.packages.filter(function(x){return x.id===id;})[0],self=this;if(!pkg)return;this.commercial.package_id=id;pkg.lines.forEach(function(l){var f=self.commercial.items.filter(function(x){return x.id===l.service_id;})[0];if(f)f.qty=l.quantity;else self.commercial.items.push({id:l.service_id,qty:l.quantity});});this._requote();},
 _requote:function(){
   var self=this;if(!this.done||!this.catalog)return;
   var dt=this.$('.qs_discount_type').val()||this.commercial.discount_type,dv=parseFloat(this.$('.qs_discount_value').val()||this.commercial.discount_value||0);
   this.commercial.discount_type=dt;this.commercial.discount_value=dv;
   rpc.query({model:'qimam.booking.commercial.service',method:'quote_event',args:[this.pick.hall_id,this.pick.partner_id,this.commercial.items,dt,dv]}).then(function(q){self.commercial.quote=q;self._render();});
 },
 _finishCommercial:function(){
   var self=this;rpc.query({model:'qimam.booking.commercial.service',method:'apply_to_event',args:[this.done.id,this.commercial.items,this.commercial.package_id||null,this.commercial.discount_type,this.commercial.discount_value]}).then(function(){self.step=6;self._render();});
 },
 _paymentNext:function(){if(this.done)this.do_action({type:'ir.actions.client',tag:'qimam_payment_experience',name:'الدفع والتأكيد',context:{active_id:this.done.id}});},
 _openDone:function(){if(this.done)this.do_action({type:'ir.actions.act_window',res_model:this.done.model,res_id:this.done.id,views:[[false,'form']],target:'current'});},
 _restart:function(){this._boot(this.mode);},
 _msg:function(m){this.do_warn('الحجز',m);}
});
core.action_registry.add('qimam_booking_studio',Studio);
return Studio;
});
