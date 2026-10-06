odoo.define('qimamhd_booking_v2.booking_operations', function(require){
"use strict";
var AbstractAction=require('web.AbstractAction'),core=require('web.core'),rpc=require('web.rpc');
var QWeb=core.qweb;

var Operations=AbstractAction.extend({
 template:'QimamOperations',
 events:{
  'click .qo_item':'_previewFromItem','click .qo_close':'_close','click .qo_open':'_open',
  'click .qo_primary':'_primary','click .qo_refresh':'_load'
 },
 start:function(){return this._super.apply(this,arguments).then(this._load.bind(this));},
 _load:function(){var self=this;return rpc.query({model:'qimam.booking.workspace.service',method:'today_operations',args:[]})
  .then(function(d){self.$('.qo_host').html(QWeb.render('QimamOperationsBody',{data:d}));});},
 _previewFromItem:function(ev){var $x=$(ev.currentTarget),kind=$x.data('kind'),model=kind==='event'?'qimam.booking':'qimam.stay.booking';this._preview(model,$x.data('id'));},
 _preview:function(model,id){var self=this;return rpc.query({model:'qimam.booking.workspace.service',method:'booking_preview',args:[model,id]})
  .then(function(d){self.$('.qo_drawer_host').html(QWeb.render('QimamBookingDrawer',{r:d}));self.$('.qo_drawer_host').addClass('open');});},
 _close:function(){this.$('.qo_drawer_host').removeClass('open').empty();},
 _open:function(ev){var $x=$(ev.currentTarget),m=$x.data('model'),id=$x.data('id');this.do_action({type:'ir.actions.act_window',res_model:m,res_id:id,views:[[false,'form']],target:'current'});},
 _primary:function(ev){var self=this,$x=$(ev.currentTarget);rpc.query({model:'qimam.booking.workspace.service',method:'execute_primary_action',args:[$x.data('model'),$x.data('id'),$x.data('action')]})
  .then(function(){self._close();self._load();});}
});
core.action_registry.add('qimam_operations',Operations);
return Operations;
});
