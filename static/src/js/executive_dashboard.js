odoo.define('qimamhd_booking_v2.executive_dashboard',function(require){
"use strict";
var AbstractAction=require('web.AbstractAction'),core=require('web.core'),rpc=require('web.rpc');var QWeb=core.qweb;
var Executive=AbstractAction.extend({
 template:'QimamExecutiveDashboard',
 events:{'click .qe_apply':'_apply','click .qe_range':'_range','click .qe_drill':'_drill'},
 init:function(){this._super.apply(this,arguments);this.startDate=null;this.endDate=null;},
 start:function(){return this._super.apply(this,arguments).then(this._load.bind(this));},
 _load:function(){var self=this;return rpc.query({model:'qimam.booking.executive.analytics',method:'dashboard',args:[this.startDate,this.endDate]}).then(function(d){self.data=d;self.$('.qe_host').html(QWeb.render('QimamExecutiveDashboardBody',{d:d}));});},
 _apply:function(){this.startDate=this.$('.qe_start').val()||null;this.endDate=this.$('.qe_end').val()||null;return this._load();},
 _range:function(ev){var days=parseInt($(ev.currentTarget).data('days'),10),end=moment(),start=moment().subtract(days-1,'days');this.startDate=start.format('YYYY-MM-DD');this.endDate=end.format('YYYY-MM-DD');return this._load();},
 _drill:function(ev){return rpc.query({model:'qimam.booking.executive.analytics',method:'drilldown',args:[$(ev.currentTarget).data('metric'),this.data.start,this.data.end]}).then(this.do_action.bind(this));}
});core.action_registry.add('qimam_executive_dashboard',Executive);return Executive;
});
