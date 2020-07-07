odoo.define('document.FolderViews', function (require) {
    "use strict";

    var core = require('web.core');
    var view_registry = require('web.view_registry');
    var AbstractView = require('web.AbstractView');
    var config = require('web.config');
    var FolderRenderer = require('document.ViewRenderer');
    var FolderModel = require('document.Model');
    var FolderController = require('document.Controller');
    var utils = require('web.utils');


    var _lt = core._lt;

    var FolderView = AbstractView.extend({
        accesskey: "f",
        display_name: _lt('Folder'),
        icon: 'fa-sitemap',
        jsLibs: ['/document_management/static/lib/jsTree/jstree.js'],
        config: _.extend({}, AbstractView.prototype.config, {
            Model: FolderModel,
            Controller: FolderController,
            Renderer: FolderRenderer,
        }),
        withSearchBar: false,
        searchMenuTypes: [],
        mobile_friendly: false,
        viewType: 'folder',
        /**
         * @constructor
         * @override
         */
        init: function (viewInfo, params) {

            this._super.apply(this, arguments);
            // console.log(this);
            // var arch = this.arch;
            // var attrs = this.arch.attrs;
            // this.loadParams.limit = this.loadParams.limit || 80;
            // this.loadParams.openGroupByDefault = true;
            // this.loadParams.type = 'list';
            //
            // this.loadParams.groupBy = arch.attrs.default_group_by ? [arch.attrs.default_group_by] : (params.groupBy || []);
            //
            // this.arch = this.rendererParams.arch;
            //
            // this.fields = viewInfo.fields;
            this.modelName = this.controllerParams.modelName;
            // this.action = params.action;
            // this.rendererParams.search = this.action.searchView;
            this.rendererParams.model = this.modelName;
            // this.controllerParams.readOnlyMode = false;
        },

    });

    view_registry.add('folder', FolderView);
    return FolderView;
});

