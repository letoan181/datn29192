odoo.define('document.ViewRenderer', function (require) {
    "use strict";

    var ajax = require('web.ajax');
    var core = require('web.core');
    var Widget = require('web.Widget');
    var AbstractRenderer = require('web.AbstractRenderer');
    var QWeb = core.qweb;
    var Dialog = require('web.Dialog');
    var session = require('web.session');
    var rpc = require('web.rpc');
    var _t = core._t;
    var xml_load = ajax.loadXML(
        '/document_management/static/src/xml/viewtype_template.xml',
        QWeb);
    var document_tree_data;
    var is_user_base;
    var ensure_one;
    var super_self;
    var check_refresh;
    var need_scroll = false;
    var scroll_element = false;
    var DocumentsRenderer = AbstractRenderer.extend({
        template: 'document.FolderTree',
        events: _.extend({}, AbstractRenderer.prototype.events, {
            // 'click .jstree-node': '_onParentClicked',
        }),
        xmlDependencies: [
            '/document_management/static/src/xml/viewtype_template.xml'
        ],
        cssLibs: [
            '/document_management/static/lib/jsTree/themes/default/style.css',
        ],
        jsLibs: [
            '/document_management/static/lib/jsTree/jstree.js',
        ],
        init: function (parent, state, params) {
            this._super.apply(this, arguments);
            // console.log(params)
            this.modelName = params.model;
            // this.searchView = params.search;
            ensure_one = [];
            check_refresh = true;
            super_self = this;
            this.getSession().user_has_group('base.group_system').then(function (has_group) {
                if (has_group) {
                    is_user_base = true
                }
            });
        },
        willStart: function () {
            // ajax.loadXML('/document_management/static/src/xml/viewtype_template.xml', QWeb);
            return $.when(ajax.loadLibs(this),
                this._super.apply(this, arguments)
            );
        },

        start: function () {
            var self = this;
            var res = this._super.apply(this, arguments);
            // console.log(this)
            this.$searchView = $(QWeb.render('document.Search'));
            this.$('#search_input').html(this.$searchView);
            // Trigger events on tree
            this.$tree.bind("dblclick.jstree", function (event) {
                var tree = $(this).jstree();
                var tree = $('.folder_tree').jstree(true);
                if (tree) {
                    var node = tree.get_node(event.target);
                    if (node.a_attr != undefined) {
                        var href = node.a_attr.href;
                        if (href != '#') {
                            window.open(href);
                        }
                    }
                }
            });
            this.$tree.bind("select_node.jstree", function (e, data) {
                if (data.node.children.length == 0 && data.node.parent == '#') {
                    $('.folder_tree').jstree(true).trigger("open_node.jstree", data);
                }
                if (data.node.children.length == 0 && data.node.parent == '#') {
                    for (var i = 0; i < document_tree_data.length; i++) {
                        if (document_tree_data[i]['id'] == data.node.id) {
                            document_tree_data[i]['is_child_listed'] = false;
                        }

                    }
                }
                for (var i = 0; i < document_tree_data.length; i++) {
                    if (document_tree_data[i]['id'] == data.node.id) {
                        var action = document_tree_data[i]['action'].edit;
                        if (action) {
                            var def = rpc.query({
                                model: 'document.abstract',
                                method: 'search_read',
                                kwargs: {
                                    res_model: action.res_model,
                                    res_id: action.res_id,
                                },
                                args: [[], []],/**/
                            }).then(function (result) {
                                if (!result) {
                                    var new_document_tree_data_fresh = [];
                                    for (var i = 0; i < document_tree_data.length; i++) {
                                        if (document_tree_data[i]['id'] != data.node.id) {
                                            new_document_tree_data_fresh.push(document_tree_data[i])
                                        }
                                    }
                                    document_tree_data = new_document_tree_data_fresh;
                                    $('.folder_tree').jstree(true).settings.core.data = document_tree_data;
                                    $('.folder_tree').jstree(true).refresh(true, false);
                                }
                            })
                        }
                        break;
                    }
                }
            });
            this.$('#o_input_search_nodes').keyup(function (event) {
                // var self = this;
                var searchString = $('#o_input_search_nodes').val();
                $('.folder_tree').jstree('search', searchString);
                if (event.keyCode === 13) {
                    var searchString = $('#o_input_search_nodes').val();
                    // $('.folder_tree').jstree(true).search(searchString)
                    if (this.modelName == 'document.general') {
                        var model = 'document.general.file';
                        var method = 'action_document_general_file_list'
                    } else if (this.modelName == 'project.project') {
                        var model = 'document.project.file';
                        var method = 'action_document_project_file_list'
                    } else if (this.modelName == 'sale.order') {
                        var model = 'document.quotation.file';
                        var method = 'action_document_quotation_file_list'
                    } else if (this.modelName == 'crm.lead') {
                        var model = 'document.crm.file';
                        var method = 'action_document_crm_file_list'
                    }
                    var load = this._rpc({
                        model: model,
                        method: method,
                        // args: [[], []],/**/
                        // kwargs: {},
                    }).then(function (action) {
                        var action = action;
                        return self.do_action(action).then(function (record) {
                            if (!(document.getElementById("character_temp"))) {
                                $('body').append('<input id="character_temp" type="hidden">');
                            }
                            $("#o_searchview_input").focus();
                            for (var i = 0; i < searchString.length; i++) {
                                $('#character_temp').val(searchString[i]);
                                var code = document.getElementById("character_temp").value.charCodeAt(0);
                                var e = jQuery.Event("keypress");
                                e.which = code;
                                e.keyCode = code;
                                $(".o_searchview_input").trigger(e);
                            }
                            // $(".o_searchview_input").val(searchString);
                            // $("#o_searchview_input").focus();
                            // var ev = jQuery.Event('keydown', {which: $.ui.keyCode.ENTER});
                            // var ev = jQuery.Event("keydown");
                            // ev.which = 13; //choose the one you want
                            // ev.keyCode = 13;
                            // // document.getElementsByClassName("o_searchview_input").trigger(e);
                            // $('#o_searchview_input').focus().trigger(ev);
                        });
                    });

                }
                // return $.when(this._super.apply(this, arguments), load);
            }.bind(this));
            // On open node
            this.$tree.on('open_node.jstree', function (e, data) {
                if (data.node.children.length > 0) {
                    data.instance.set_icon(data.node, "/document_management/static/description/images/folder.png");
                    for (var i = 0; i < data.node.children.length; i++) {
                        if (data.node.children[i].includes('doctype')) {
                            $('.folder_tree').jstree(true).set_icon(data.node.children[i], "/document_management/static/description/images/docs.png");
                        } else if (data.node.children[i].includes('exceltype')) {
                            $('.folder_tree').jstree(true).set_icon(data.node.children[i], "/document_management/static/description/images/sheets.png");
                        } else if (data.node.children[i].includes('power_pointtype')) {
                            $('.folder_tree').jstree(true).set_icon(data.node.children[i], "/document_management/static/description/images/slides.png");
                        } else {
                            $('.folder_tree').jstree(true).set_icon(data.node.children[i], "/document_management/static/description/images/google-drive.png");
                        }
                    }
                }
                var is_child_listed = false;
                for (var i = 0; i < document_tree_data.length; i++) {
                    if (document_tree_data[i]['id'] == data.node.id) {
                        is_child_listed = document_tree_data[i]['is_child_listed'];
                        var action = document_tree_data[i]['action'].edit;
                        if (action) {
                            var def = rpc.query({
                                model: 'document.abstract',
                                method: 'search_read',
                                kwargs: {
                                    res_model: action.res_model,
                                    res_id: action.res_id,
                                },
                                args: [[], []],/**/
                            }).then(function (result) {
                                if (!result) {
                                    var new_document_tree_data_fresh = [];
                                    for (var i = 0; i < document_tree_data.length; i++) {
                                        if (document_tree_data[i]['id'] != data.node.id) {
                                            new_document_tree_data_fresh.push(document_tree_data[i])
                                        }
                                    }
                                    document_tree_data = new_document_tree_data_fresh;
                                    $('.folder_tree').jstree(true).settings.core.data = document_tree_data;
                                    $('.folder_tree').jstree(true).refresh(true, false);
                                    is_child_listed = true;
                                }
                            })
                        }
                        break;
                    }
                }
                // if is_child_listed == true and virtual exist -> set is_child_listed = false
                // var is_current_child_virtual = false;
                // var current_tree_data = $('.folder_tree').jstree(true).settings.core.data;
                // for (var i = 0; i < current_tree_data.length; i++) {
                //     if (current_tree_data[i]['parent'] == data.node.id && current_tree_data[i]['id'].includes('virtual_folder')) {
                //         is_current_child_virtual = true;
                //     }
                // }
                // //if is_current_child_virtual remove it from current js tree
                // // var new_current_tree_data = [];
                // // for (var i = 0; i < current_tree_data.length; i++) {
                // //     if (current_tree_data[i]['id'].includes('virtual_folder')) {
                // //         current_tree_data[i]['text'] = ''
                // //     }
                // //     new_current_tree_data.push(current_tree_data[i])
                // // }
                // // $('.folder_tree').jstree(true).settings.core.data = new_current_tree_data;
                // if (is_child_listed && is_current_child_virtual) {
                //     is_child_listed = false;
                // }
                if (!is_child_listed) {
                    var self = this;
                    // update node
                    // search all child files
                    rpc.query({
                        route: '/document/view/tree/node',
                        params: {
                            current_node: data.node.id,
                            permission: is_user_base
                        },
                    }).then(function (result) {
                            // remove all child of current node
                            // console.log(document_tree_data)
                            var new_document_tree_data = [];
                            for (var i = 0; i < document_tree_data.length; i++) {
                                if (document_tree_data[i]['parent'] != data.node.id) {
                                    new_document_tree_data.push(document_tree_data[i])
                                }
                            }
                            document_tree_data = new_document_tree_data;
                            for (var i = 0; i < document_tree_data.length; i++) {
                                if (document_tree_data[i]['id'] == result['current_node']) {
                                    document_tree_data[i]['is_child_listed'] = true;
                                }
                            }
                            // update new child for current code
                            if (result['data'].length > 0) {
                                // console.log(document_tree_data)
                                // console.log(result['data'])
                                document_tree_data = document_tree_data.concat(result['data']);
                                // console.log(document_tree_data)
                                // update current parent node

                            }
                            $('.folder_tree').jstree(true).settings.core.data = document_tree_data;
                            need_scroll = true;
                            scroll_element = data.node.id + '_anchor';
                            $('.folder_tree').jstree(true).refresh(true, false);
                        }
                    )
                }


            });
            this.$tree.on('close_node.jstree', function (e, data) {
                data.instance.set_icon(data.node, "fa fa-folder-o");
                // update is_child_listed
                var node = data.node;
                var jstree = $('.folder_tree').jstree(true);
                var list = RemoveAllChild(jstree, node);
                var list_sub_node = [];
                for (var i = 0; i < list.length; i++) {
                    if (Array.isArray(list[i])) {
                        list_sub_node.push(list[i][0]);
                    } else {
                        list_sub_node.push(list[i])
                    }
                }
                for (var i = 0; i < document_tree_data.length; i++) {
                    if (document_tree_data[i]['id'] == data.node.id) {
                        document_tree_data[i]['is_child_listed'] = false;
                    }
                    // if(list_sub_node.includes(document_tree_data[i]['id'])){
                    //     document_tree_data[i]['is_child_listed'] = false;
                    // }
                }
                // // search and remove child
                var new_document_tree_data = [];
                // var all_child_list = [];
                for (var i = 0; i < document_tree_data.length; i++) {
                    // if (document_tree_data[i]['parent'] != data.node.id) {
                    //     new_document_tree_data.push(document_tree_data[i])
                    // }
                    if (!list_sub_node.includes(document_tree_data[i]['id'])) {
                        // new_document_tree_data = document_tree_data.splice(document_tree_data.indexOf(document_tree_data[i], 1))
                        new_document_tree_data.push(document_tree_data[i])

                    }
                }
                new_document_tree_data.push({
                    "id": node.id + '_' + 'virtual_folder',
                    "parent": data.node.id, "text": '',
                    "is_child_listed": false
                });
                for (var i = 0; i < new_document_tree_data.length; i++) {
                    if (new_document_tree_data[i]['id'] == data.node.id) {
                        var action = new_document_tree_data[i]['action'].edit;
                        if (action) {
                            var def = rpc.query({
                                model: 'document.abstract',
                                method: 'search_read',
                                kwargs: {
                                    res_model: action.res_model,
                                    res_id: action.res_id,
                                },
                                args: [[], []],/**/
                            }).then(function (result) {
                                if (!result) {
                                    window.location.reload()
                                }
                            })
                        }
                        break;
                    }
                }
                document_tree_data = new_document_tree_data;
                // document_tree_data = new_document_tree_data;
                $('.folder_tree').jstree(true).settings.core.data = document_tree_data;
                need_scroll = true;
                scroll_element = data.node.id + '_anchor';
                $('.folder_tree').jstree(true).refresh(true, false);

                // setTimeout(function () {
                //     document.getElementById(data.node.id + '_anchor').scrollIntoView();
                // }, 200);
            });
            this.$tree.on('refresh.jstree', function (e, data) {
                if (need_scroll) {
                    try {
                        $('.jstree-wholerow-clicked').removeClass('jstree-wholerow-clicked');
                        document.getElementById(scroll_element).scrollIntoView();
                        $('#' + scroll_element.replace('_anchor', '')).attr('aria-selected', 'true');
                        $('#' + scroll_element.replace('_anchor', '')).children(":first").addClass("jstree-wholerow-clicked");
                        // setTimeout(function () {
                        //     $('#' + scroll_element.replace('_anchor', '')).children(":first").addClass("jstree-wholerow-clicked");
                        // }, 5000);
                    } catch (e) {
                        console.log(e)
                    }
                }
            });
            // this.$tree.on('select_node.jstree', function (e, data) {
            //     var self = this;
            //     if (data.node.id) {
            //         rpc.query({
            //             route: '/document/get/action',
            //             params: {
            //                 current_node: data.node.id,
            //                 permission: is_user_base
            //             },
            //         }).then(function (action) {
            //             self.do_action(action)
            //         })
            //     }
            // }.bind(this));
            this.$('[data-toggle="tooltip"]').tooltip();
            // console.log(this)
            this._super.apply(this, self);
            return res;
        },

        // _onParentClicked: function (e) {
        //     var self = this;
        //
        // },
        /**
         * @override
         * @private
         * @returns {Deferred}
         */
        _render: function () {
            var self = this;
            var jstree = this.$tree = this.$('.folder_tree');
            if (jstree) {
                this._rpc({
                    route: '/document/view/tree/directory',
                    params: {
                        model: this.modelName,
                        permission: is_user_base
                    },
                }).then(function (result) {
                        // if (result.length == 0 || result == false) {
                        //     self.do_warn(_t("No Data To Show"))
                        // }
                        if (result != false && result.length > 0) {
                            document_tree_data = result;
                            jstree.jstree({
                                'contextmenu': {
                                    'items': customMenu
                                },
                                'core': {
                                    'data': document_tree_data
                                },
                                "check_callback": true,
                                "themes": {
                                    'name': 'proton',
                                    'responsive': true,
                                    "variant": "large",
                                    'ellipsis': true
                                },
                                "search": {
                                    "case_insensitive": true,
                                    "show_only_matches": false
                                },
                                'types': {
                                    // "root": {
                                    //     "icon": "/document_management/static/description/images/drive.png"
                                    // },
                                    "default": {"icon": "/document_management/static/description/images/google-drive.png"}
                                },

                                "plugins": [
                                    "contextmenu", "search", "state", "types", "wholerow"
                                ],
                            });
                            self._refresh(jstree, document_tree_data)

                        }

                    }
                );
            }
            // this.$tree.jstree(true).refresh(true, false);
            return $.when().then(function () {
                // Prevent Double Rendering on Updates
                if (!self) {
                    $(window).trigger('resize');
                }
            });
        },
        _refresh: function (jstree, data) {
            var self = this;
            if (jstree) {
                jstree.jstree(true).settings.core.data = data;
                jstree.jstree(true).refresh(true, false);
            }
        },
    });

    function RemoveAllChild(jstree, node) {
        var list = [];
        if (node.children.length > 0) {
            for (var i = 0; i < node.children.length; i++) {
                list.push(node.children[i]);
                list.push(RemoveAllChild(jstree, jstree.get_node(node.children[i])))
            }
        }
        return list
    }

    function customMenu(node) {
        var self = this;
        var nodes = node;
        // if (node.a_attr.href == '#') {
        var items = {
            'item1': {
                'label': 'New',
                'icon': 'fa fa-plus-circle',
                'submenu': {
                    'item4': {
                        'label': 'Current Folder/Files',
                        'action': function () {
                            for (var i = 0; i < document_tree_data.length; i++) {
                                if (document_tree_data[i]['id'] == node.id) {
                                    var action = document_tree_data[i]['action'].create;
                                    if (action) {
                                        if (node.parent == '#') {
                                            return super_self.do_action({
                                                type: 'ir.actions.act_window',
                                                res_model: action.res_model,
                                                // res_id: action.res_id,
                                                context: action.context,
                                                views: action.views,
                                                target: action.target
                                            }, {
                                                on_close: function () {
                                                    window.location.reload()
                                                },
                                            });

                                        } else {
                                            return super_self.do_action({
                                                type: 'ir.actions.act_window',
                                                res_model: action.res_model,
                                                // res_id: action.res_id,
                                                context: action.context,
                                                views: action.views,
                                                target: action.target
                                            });
                                        }
                                        // console.log(this)
                                    }
                                }
                            }
                        }.bind([document_tree_data, super_self]),
                        '_disabled': function (data) {
                            for (var i = 0; i < document_tree_data.length; i++) {
                                if (document_tree_data[i]['id'] == node.id) {
                                    return !document_tree_data[i]['permission'].perm_create;
                                }
                            }
                        }.bind(document_tree_data),
                    },
                    'item5': {
                        'label': 'Sub Folder/Files',
                        'action': function () {
                            for (var i = 0; i < document_tree_data.length; i++) {
                                if (document_tree_data[i]['id'] == node.id) {
                                    var action = document_tree_data[i]['action'].create_child;
                                    if (action.context != null || action.context != undefined) {
                                        return super_self.do_action({
                                            type: 'ir.actions.act_window',
                                            res_model: action.res_model,
                                            // res_id: action.res_id,
                                            context: action.context,
                                            views: action.views,
                                            target: action.target
                                        });
                                        // console.log(this)
                                    }
                                }
                            }
                        }.bind([document_tree_data, super_self]),
                        '_disabled': function (data) {
                            for (var i = 0; i < document_tree_data.length; i++) {
                                if (document_tree_data[i]['id'] == node.id) {
                                    if (document_tree_data[i]['permission'].perm_create_child != undefined) {
                                        return !document_tree_data[i]['permission'].perm_create_child;
                                    } else {
                                        return true;
                                    }

                                }
                            }
                        }.bind(document_tree_data),
                    },
                }

            },
            'item2': {
                'label': 'Edit',
                'icon': "fa fa-pencil",
                'action': function () {
                    for (var i = 0; i < document_tree_data.length; i++) {
                        if (document_tree_data[i]['id'] == node.id) {
                            var action = document_tree_data[i]['action'].edit;
                            if (action) {
                                return super_self.do_action({
                                    type: 'ir.actions.act_window',
                                    res_model: action.res_model,
                                    res_id: action.res_id,
                                    views: action.views,
                                    context: {create: false},
                                    target: action.target
                                }, {
                                    on_close: function () {
                                        var def = super_self._rpc({
                                            model: action.res_model,
                                            method: 'search_read',
                                            domain: [
                                                ['id', '=', action.res_id]
                                            ],
                                        }).then(function (result) {
                                            $('.folder_tree').jstree('set_text', node.id, result[0].name);
                                            document_tree_data[i]['text'] = result[0].name
                                        });
                                    },
                                });
                                // console.log(this)
                            }
                        }
                    }
                }.bind([document_tree_data, super_self]),
                '_disabled': function (data) {
                    for (var i = 0; i < document_tree_data.length; i++) {
                        if (document_tree_data[i]['id'] == node.id) {
                            return !document_tree_data[i]['permission'].perm_write;
                        }
                    }
                }.bind(document_tree_data)
            },
            'item3': {
                'label': 'Delete',
                'icon': 'fa fa-trash-o',
                'action': function () { /* action */
                    for (var i = 0; i < document_tree_data.length; i++) {
                        if (document_tree_data[i]['id'] == node.id) {
                            var action = document_tree_data[i]['action'].delete;
                            if (action) {
                                Dialog.confirm(this, _t("Are you sure you want to delete this record ?"), {
                                    confirm_callback: function () {
                                        return rpc.query({
                                            model: action.model,
                                            method: action.method,
                                            args: [action.res_id],
                                            context: session.user_context,
                                        }).then(function () {
                                            var new_document_tree_data = [];
                                            for (var i = 0; i < document_tree_data.length; i++) {
                                                if (document_tree_data[i]['id'] != node.id) {
                                                    new_document_tree_data.push(document_tree_data[i])
                                                }
                                            }
                                            document_tree_data = new_document_tree_data;
                                            $('.folder_tree').jstree(true).settings.core.data = document_tree_data;
                                            $('.folder_tree').jstree(true).refresh(true, false);
                                        });
                                    }
                                });
                            }
                        }
                    }
                }.bind([document_tree_data, $('.folder_tree').jstree(true)]),
                '_disabled': function (data) {
                    for (var i = 0; i < document_tree_data.length; i++) {
                        if (document_tree_data[i]['id'] == node.id) {
                            return !document_tree_data[i]['permission'].perm_unlink;
                        }
                    }
                }.bind(document_tree_data),
            },
        };
        return items;
        // } else
        //     return false


    }

    return DocumentsRenderer;

});
