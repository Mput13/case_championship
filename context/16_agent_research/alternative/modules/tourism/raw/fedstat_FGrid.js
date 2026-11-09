var FGrid = function(params) {
    var _this = this;

    //основной блок
    _this.root_block = params.block;

    //название таблицы
    _this.title = params.title || '';
    //единица измерения
    _this.unit  = params.unit  || '';

    //содержимое грида
    _this.main_block = jQuery('<div class="agrid-content-block">');
    _this.header_block = jQuery('<div class="agrid-header-block">');
    _this.footer_block = jQuery('<div class="agrid-footer-block">');

    //преобразованная база с которой работаем
    _this.db = TAFFY([]);
    _this.db_template = {};
    _this.d_i = [];

    //системные фильтры, которые в блоке фильтров не показываются
    _this.system_filters = [];

    //фильтры с кодами окато, по которым можно построить карту
    _this.map_filter = null;
    _this.map_filters = [
        '3301', '32251', '32234', '32235', '34559', '30628'
    ];

    _this.logs = [];

    _this.debug = typeof params.debug != 'undefined' ? params.debug : false;

    //таблицы для вывода
    _this.tables = [];

    //фильтры
    _this.filters = params.filters || {};

    _this.left_columns = params.left_columns || [];
    _this.top_columns  = params.top_columns || [];

    _this.is_default_state = false;

    //варианты используемой навигации
    _this.navTypes = {
        is_default  : 0, //для одной таблицы
        maxTables   : 1, //для групп при большом колве групп и малом колве записей в группе
        maxRows     : 2 //для групп, при малом колве групп и большом колве записей в группе
    };

    _this.null_value = 0.0000000273;

    _this.lastClickedFilter = null;

    //сохраним дефолтные настройки на случай отката
    _this.default_params = jQuery.extend({}, params);
    //сохраним состояния дефотных фильтров
    Object.keys(_this.default_params.filters).forEach(function(filter_id){
        if(_this.map_filters.indexOf(filter_id) > -1)
            _this.map_filter = filter_id;

        if(_this.default_params.filters[filter_id].indicator)
            _this.system_filters.push(parseInt(filter_id));

        _this.default_params.filters[filter_id].default_all = _this.default_params.filters[filter_id].all;
        Object.keys(_this.default_params.filters[filter_id].values).forEach(function(value_id){
            _this.default_params.filters[filter_id].values[value_id].default_checked = _this.default_params.filters[filter_id].values[value_id].checked;
        })
    });

    //текущий тип навигации
    _this.navType = _this.navTypes.is_default;

    //текущая страница
    _this.page = 1;

    //кол-во видимых страниц слева и справа
    _this.page_count_visible = 5;

    //кол-во записей/таблиц на страницу
    _this.limit = 200;//00;
    _this.groups_limit = 10;

    //итератор таблиц(для группировки с большим кол-вом таблиц)
    _this.groups_iterator = 0;

    //флаг - грид развернут на весь экран
    _this.fullscreen = false;

    //параметры для отрисовки грида и столбцов
    _this.field_params = {
        locked_content_height: 500,
        wrap_content_height: 500,

        group_padding: 14
    };

    switch (true) {
        case window.outerWidth >= 1280:
            _this.field_params.main_block_width = 1000;
            _this.field_params.grid_width = 998;
            _this.field_params.locked_header_width = 180;
            _this.field_params.wrap_header_width = 180;
            break;
        case window.outerWidth >= 1024:
            _this.field_params.main_block_width = 984;
            _this.field_params.grid_width = 982;
            _this.field_params.locked_header_width = 150;
            _this.field_params.wrap_header_width = 150;
            break;
        default :
            //самые маленькие < 1024
            _this.field_params.main_block_width = 728;
            _this.field_params.grid_width = 726;
            _this.field_params.locked_header_width = 150;
            _this.field_params.wrap_header_width = 150;
            break;
    }


    //id объекта fedstat
    _this.id = params.id;

    _this.url = '/indicator/dataGrid.do?id=';
    //_this.url = '/common/indicator/dataGrid.php?id=';

    _this.editor = typeof FGridEditor != 'undefined' ? new FGridEditor(_this): null;

    //группировки столбцов в том порядке, который казан в строке группировки
    _this.groups = params.groups || [];
    _this.group_block_text = 'Перетащите сюда заголовок колонки, чтобы сгруппировать записи из этой колонки';

    //столбцы для отрисовки
    _this.columns = params.columns;

    //массив для сортировки
    _this.order = [];

    //флаг, необходимость загрузки данных
    _this.need_load_data = false;

    _this.chart = null;
    _this.chart_title = null;

    //индикатор загрузки
    _this.loader = (function(){
        var loader = document.createElement('div');
        loader.className = 'agrid-loader';

        var loader_text = document.createElement('div');
        loader_text.innerText = 'Получение данных. Пожалуйста, подождите.';
        loader_text.className = 'agrid-loader-text';
        loader.appendChild(loader_text);

        return loader;
    })();

    //шаблон для вывода данных в таблицы, формируется при построении заголовков
    _this.line_template_fixed = [];
    _this.line_template_wrap  = [];

    _this.locked_header  = jQuery('<div class="k-grid-header-locked">');
    _this.wrap_header    = jQuery('<div class="k-grid-header-wrap">');

    _this.action_block = jQuery('#agrid-action-block');

    _this.graphics_block = jQuery('#modal_grafik_sogl');
    _this.graphics_content = jQuery('#agrid-graphics-content');

    _this.setting_tab_button = jQuery('#setting_tab');

    _this.dialog_data_is_null = jQuery('#dialog_data_is_null');

    _this.options = {
        mCustomScrollbar: function(type) {
            return {
                axis: type,
                theme:"dark",
                scrollInertia:100,
                advanced:{
                    //autoExpandHorizontalScroll:true,
                    //updateOnContentResize: true
                },
                callbacks: {
                    /*whileScrolling : function() {
                     var top = this.mcs.top * -1,
                     left = this.mcs.left * -1
                     ;

                     if(_this.scrollTop != top) {
                     _this.scrollTop = top;
                     _this.content_locked.scrollTop(_this.scrollTop);
                     }

                     if(_this.scrollLeft != left) {
                     _this.scrollLeft = left;
                     _this.header_wrap.scrollLeft(_this.scrollLeft);
                     }
                     }*/
                }
            };
        },
        draggable: {
            appendTo: 'body',
            containment: 'window',
            connectToSortable: '#sortable',
            helper: function(){
                var obj = jQuery(this).clone();
                obj.css({
                    margin: '5px', padding: '5px'
                });
                obj.text(_this.filters[obj.data('field')].title);
                obj.fadeTo( "slow" , 0.5);
                if(_this.group_block.find('th').length == 0)
                    _this.group_block.text('');
                return obj;
            },
            start: function() {
                if(!_this.checkedFiltersLength(false)) {
                    if(_this.group_block.find('th').length == 0)
                        _this.group_block.text(_this.group_block_text);
                    return false;
                }
            },
            drag: function() {
                if(_this.groups_refreshing)
                    return false;
            },
            stop: function(){
                if(_this.group_block.find('th').length == 0)
                    _this.group_block.text(_this.group_block_text);
            },
            revert: false
        },
        sortable: {
            revert: 0,
            placeholder: 'ui-state-highlight',
            stop: function(event, ui) {
                if(!ui.item.data('tag') && !ui.item.data('handle')) {
                    ui.item.data('tag', true);
                    ui.item.html(_this.filters[ui.item.data('field')].title + '<span class="k-icon k-group-delete"></span>');
                    ui.item.css({
                        margin: '5px',
                        padding: '5px',
                        display: 'inline',
                        'min-width': "150px"
                    })
                }
                ui.item.fadeTo( "slow" , 1);
                _this.events.group_block.refresh();
            },
            start: function(e,ui){
                ui.placeholder.height(ui.item.height());
                ui.helper.fadeTo( "slow" , 0.5);
            }
        }
    };

    _this.events = {
        //события индикатора загрузки
        loader: {
            show: function(e, obj) {
                _this.root_block.css({position: 'relative'});
                _this.loader.style.display = 'block';
            },
            hide: function(e, obj) {
                _this.loader.style.display = 'none';
                _this.root_block.css({position: ''});
            }
        },
        on_changed_block: {
            show: function(e, obj) {
                $("#agrid-action-default-state2, #grid_to_widget").show();
                _this.is_default_state = false;
            },
            hide: function(e, obj) {
                $("#agrid-action-default-state2, #grid_to_widget").hide();
                _this.is_default_state = true;
            }
        },
        //события заголовков
        theader : {
            //сортировка
            sort: function(e, a) {
                var th = a.parent();
                var field = th.attr('data-field-sort');

                //очищаем предыдущие сортировки
                jQuery('.k-icon.k-i-arrow-n, .k-icon.k-i-arrow-s').remove();

                var fieldSort = th.data('fieldSort');
                var orders = jQuery('.order-asc, .order-desc');
                switch (true) {
                    case th.hasClass('order-asc'):
                        orders.removeClass('order-asc').removeClass('order-desc');
                        th.addClass('order-desc');
                        a.append('<span class="k-icon k-i-arrow-s"></span>');

                        _this.order = [fieldSort, 'logicaldesc'];
                        break;
                    case th.hasClass('order-desc'):
                        orders.removeClass('order-asc').removeClass('order-desc');
                        _this.order = [];
                        break;
                    default :
                        orders.removeClass('order-asc').removeClass('order-desc');
                        th.addClass('order-asc');
                        a.append('<span class="k-icon k-i-arrow-n"></span>');

                        _this.order = [fieldSort, 'logical'];
                        break;
                }

                setTimeout(function(){
                    //перерисовываем данные
                    _this.tables.forEach(function(table){
                        table.renderContent();
                    });
                }, 500);

                return false;
            }
        },

        //события блока группировок
        group_block : {
            drop: function(e, obj) {
                if(_this.checkedFiltersLength()) {
                    //удаляем запись
                    obj.parent().remove();
                    //обновляем группировки
                    _this.events.group_block.refresh();
                }
            },
            refresh : function(e, obj) {
                _this.groups_refreshing = true;

                _this.events.on_changed_block.show();

                var elems = _this.group_block.find('th');
                if(elems.length == 0) {
                    _this.group_block.text(_this.group_block_text);
                }

                //очищаем сортировку, т.к. столбцы могут отличаться
                //todo проверить
                _this.order = [];

                var new_groups = [];
                jQuery.each(elems, function() {
                    new_groups.push( parseInt(jQuery(this).data('field')));
                });

                //если группировка изменилась - обновляем
                if(new_groups.join() != _this.groups.join()) {
                    _this.groups = new_groups.slice();

                    //_this.events.loader.show();
                    setTimeout(function(){

                        var fullscreen = false;
                        if(_this.fullscreen) {
                            fullscreen = true;
                            _this.gridFullscreen();
                        }

                        _this.prepareHeaders();

                        _this.createTables();

                        _this.drawNavigation();

                        switch (_this.navType) {
                            case _this.navTypes.maxTables:
                                //отображаем только видивые таблицы
                                var iterator = 0;
                                _this.tables.forEach(function(table){
                                    if(iterator >= (_this.page - 1) * _this.groups_limit && iterator < (_this.page - 1) * _this.groups_limit + _this.groups_limit) {
                                        if (!table.inited)
                                            table.init();
                                        if(!table.rendered)
                                            table.render();

                                        table.show();
                                    }
                                    else {
                                        table.hide();
                                    }
                                    iterator++;
                                });
                                break;
                            case _this.navTypes.maxRows:
                                _this.tables.forEach(function(table){
                                    table.render();
                                    table.show();
                                });
                                break;
                            default:
                                _this.tables.forEach(function(table){
                                    table.render();
                                    table.show();
                                });
                        }

                        if(fullscreen) {
                            _this.gridFullscreen();
                        }

                        _this.preparePreview();

                        _this.groups_refreshing = false;

                    }, 500);
                }
            }
        },

        filter: {
            click: function(e, obj) {
                _this.lastClickedFilter = obj;
                var filter_id = parseInt(obj.data('field'));
                if(isNaN(filter_id))
                    filter_id = parseInt(obj.closest('.k-header').data('field'));

                Object.keys(_this.filters).forEach(function(f_id){
                    if(typeof _this.filters[f_id].filter_block != 'undefined' && _this.filters[f_id].filter_block != null)
                        _this.filters[f_id].filter_block.hide();
                });

                if(!!!_this.filters[filter_id].filter_block || !_this.filters[filter_id].filter_block.find('form').length) {
                    var container = jQuery('<div class="k-animation-container"/>').css({
                        'margin-left': '-2px', 'padding-left': '2px', 'padding-right': '2px', 'padding-bottom': '4px',
                        overflow: 'visible', position: 'absolute', top: obj.offset().top +'px', 'z-index': 10002,
                        left: (screen.width - obj.offset().left < 200 ? obj.offset().left - 200 : obj.offset().left) + 'px', 'box-sizing': 'content-box'
                    }).on('mouseleave', _this.events.filter.mouse_leave);

                    var all = _this.filters[filter_id].all;

                    html =
                        '<form class="k-filter-menu k-popup k-group k-reset k-state-border-up" data-role="popup" style="display: block; font-stretch: normal; -webkit-transform: translateY(0px); ">'+ //position: absolute;
                        '<ul class="k-reset k-multicheck-wrap">'+
                            '<li class="k-item">' +
                                '<label class="k-label">'+
                                    '<input type="checkbox" class="k-check-all hide" value="Select All" data-id="'+ filter_id +'" '+ (all ? 'checked' : '') +'>' +
                                    '<span class="sp_checkbox"></span><b>Выбрать все (' + Object.keys(_this.filters[filter_id].values).length + ')</b>' +
                                '</label>' +
                            '</li>' +
                            '<div class="k-other-filters" '+ (all ? 'style="display: none;"' : '') +'>' +
                        _this.objectKeys(filter_id).map(function(under_id){
                            var filter = _this.filters[filter_id].values[under_id];
                            return '<li class="k-item"><label class="k-label"><input type="checkbox" class="k-check-filter hide" '+ (filter.checked ? ' checked="checked" ' : '' ) +' value="'+ under_id +'" data-owner="'+ filter_id +'"><span class="sp_checkbox"></span>'+ filter.title +'</label></li>';
                        }).join('') +
                            '</div>' +
                        '</ul>'+
                        '<button type="submit" class="k-button k-primary k-filter-load" '+ (!_this.checkedFiltersLength(false)? 'disabled' : '') +'>Фильтровать</button>' +
                        '<button type="button" onclick="$(this).prev().prev(\'ul\').find(\'.k-check-filter:checked, .k-check-all:checked\').click(); return false;" class="k-button">Очистить</button>'+
                        '</form>';

                    container.html(html);

                    _this.main_block.append(container);
                    _this.filters[filter_id].filter_block = container;
                } else {
                    if(_this.main_block.find(_this.filters[filter_id].filter_block).length == 0) {
                        _this.main_block.append(
                            _this.filters[filter_id].filter_block.on('mouseleave', _this.events.filter.mouse_leave)
                        );
                    }

                    _this.filters[filter_id].filter_block
                        .css({
                            top: obj.offset().top +'px',
                            left: (screen.width - obj.offset().left < _this.filters[filter_id].filter_block.width() ? obj.offset().left - _this.filters[filter_id].filter_block.width() + 30 : obj.offset().left) + 'px'
                        })
                        .show()
                }

                $(document).trigger('click.context');
                _this.events.filter.click_in_out(e, _this.filters[filter_id].filter_block, filter_id);

                return false;
            },
            checkAll: function (e, obj) {
                _this.filters[obj.data('id')].all = obj.prop('checked');
                if(obj.prop('checked'))
                    obj.closest('.k-multicheck-wrap').find('.k-other-filters').hide();
                else
                    obj.closest('.k-multicheck-wrap').find('.k-other-filters').show();

                if (!_this.checkedFiltersLength(false)) {
                    _this.main_block.find('.k-animation-container .k-filter-load, .k-animation-container .k-filter-clear').each(function(){
                        $(this).prop('disabled', true);
                    });

                    //$(e.target.form).find('.k-filter-load').attr('disabled', 'disabled');
                    //$(e.target.form).find('.k-filter-clear').attr('disabled', 'disabled');
                } else {
                    _this.main_block.find('.k-animation-container .k-filter-load, .k-animation-container .k-filter-clear').each(function(){
                        $(this).prop('disabled', false);
                    });
                    //$(e.target.form).find('.k-filter-load').removeAttr('disabled');
                    //$(e.target.form).find('.k-filter-clear').removeAttr('disabled');
                    _this.events.on_changed_block.show();
                }
            },
            click_in_out: function(e, obj, filter_id) {
                var yourClick = false;

                $(document).off('click.filter').on('click.filter', function (e) {
                    if (!yourClick && $(e.target).closest(obj).length == 0) {
                        _this.checkedFiltersLength();

                        obj.hide();
                        $(document).off('click.filter');
                    }
                    yourClick = false;
                });
                e.preventDefault();
            },
            mouse_leave: function(e, obj) {
/*                jQuery(this).hide();
                _this.checkedFiltersLength();
*/            },
            check_value: function(e, obj) {
                var obj_val = obj.val(),
                    obj_owner = obj.data('owner');


                _this.filters[obj_owner].values[obj_val].checked = !_this.filters[obj_owner].values[obj_val].checked;

                if (!_this.checkedFiltersLength(false)) {
                    _this.main_block.find('.k-animation-container .k-filter-load, .k-animation-container .k-filter-clear').each(function(){
                        $(this).prop('disabled', true);
                    });

                    //$(e.target.form).find('.k-filter-load').attr('disabled', 'disabled');
                    //$(e.target.form).find('.k-filter-clear').attr('disabled', 'disabled');
                } else {
                    _this.main_block.find('.k-animation-container .k-filter-load, .k-animation-container .k-filter-clear').each(function(){
                        $(this).prop('disabled', false);
                    });
                    //$(e.target.form).find('.k-filter-load').removeAttr('disabled');
                    //$(e.target.form).find('.k-filter-clear').removeAttr('disabled');
                    _this.events.on_changed_block.show();
                }
            },
            filter: function(e, obj) {
                if(_this.checkedFiltersLength()) {
                    _this.updateData(null, function () {
                        _this.showDialogIsNull();
                    });
                } else {
                    $(e.target).closest('.k-animation-container').hide();
                }
                return false;
            }
        },

        navigation: {
            click: function(e, obj) {
                _this.page = parseInt(obj.data('page'));

                switch (_this.navType) {
                    case _this.navTypes.maxTables:
                        //отображаем только видивые таблицы
                        var iterator = 0;
                        _this.tables.forEach(function(table){
                            if(iterator >= (_this.page - 1) * _this.groups_limit && iterator < (_this.page - 1) * _this.groups_limit + _this.groups_limit) {
                                if (!table.inited)
                                    table.init();
                                if(!table.rendered)
                                    table.render();

                                table.show();
                            }
                            else {
                                table.hide();
                            }
                            iterator++;
                        });
                        break;
                    case _this.navTypes.maxRows:
                        _this.tables.forEach(function(table){
                            table.render();
                            table.show();
                        });
                        break;
                    case _this.navTypes.is_default:
                        _this.tables.forEach(function(table) {
                            table.renderContent();
                            table.content_wrap.scrollTop(0);
                        });
                        break;
                }

                _this.drawNavigation();
                return false;
            },
            hide_group: function(e, obj) {
                obj.addClass('k-grid-group-block-hidden');
                if(obj.parent().hasClass('k-grid-group-content')) {
                    var parent_content = obj.parent();
                    //нужно считать скрытые элементы методом hide_group, а не все скрытые
                    if(parent_content.find('.k-grid-group-block').length == parent_content.find('.k-grid-group-block-hidden').length)
                        _this.events.navigation.hide_group(e, parent_content.parent());
                }
            },
            show_group: function(e, obj) {
                obj.removeClass('k-grid-group-block-hidden');
                if(obj.parent().hasClass('k-grid-group-content')) {
                    var parent_content = obj.parent();
                    //if(parent_content.find('k-grid-group-block:visible').length > 0)
                    _this.events.navigation.show_group(e, parent_content.parent());
                }
            }
        },

        action_block: {
            selectAllRows: function(e, obj) {
                _this.events.action_block.deselect(e, obj);
                _this.tables.forEach(function(table){
                    table.content_locked.find('tr').addClass('row-selected');
                    table.content_wrap.find('tr').addClass('row-selected');
                    table.data.forEach(function(line){
                        _this.db(line).update({selected: true});
                    });
                });
                _this.events.on_changed_block.show();
            },
            selectAllCols: function(e, obj) {
                _this.events.action_block.deselect(e, obj);
                _this.db().update({selected: false});
                _this.tables.forEach(function(table){
                    table.select_wrap.forEach(function(col, col_id){
                        table.onSelectCol(col_id, 'addClass');
                    });
                });
                _this.events.on_changed_block.show();
            },
            hideSelected: function(e, obj) {
                var selected_count = _this.db({selected: true, hidden_selected: false}).count();

                var fullscreen = false;
                if(_this.fullscreen) {
                    fullscreen = true;
                    _this.gridFullscreen();
                }

                //если есть выделенные записи, то сразу все скрываем и перерисовываем навигацию
                if(selected_count > 0) {
                    _this.db({selected: true}).update({hidden_selected: true/*, selected: false*/});
                    _this.drawNavigation();
                }

                _this.tables.forEach(function(table){
                    var selected_cols_length = table.selected_cols.filter(function(col_id) {
                        return table.hidden_cols.indexOf(col_id) === -1;
                    }).length;

                    //пропускаем если выделенного нет
                    if(selected_cols_length == 0 && selected_count == 0)
                        return;

                    table.hidden_cols = table.hidden_cols.concat(table.selected_cols);
                    //table.selected_cols = [];

                    table.render();
                });

                //если отрисовка была и был запущен фуллскрин - делаем фуллскрин еще раз, чтобы скрыть все косяки
                if(fullscreen) {
                    _this.gridFullscreen();
                }
                _this.events.on_changed_block.show();
            },
            hideOnlyDeselected: function(e, obj) {
                var selected_count = _this.db({selected: true, hidden_selected: false}).count();
                _this.events.on_changed_block.show();
                var fullscreen = false;
                if(_this.fullscreen) {
                    fullscreen = true;
                    _this.gridFullscreen();
                }

                _this.tables.forEach(function(table) {
                    var selected_cols_length = table.selected_cols.filter(function(col_id) {
                        return table.hidden_cols.indexOf(col_id) === -1;
                    }).length;

                    //пропускаем если выделенного нет
                    if(selected_cols_length == 0 && selected_count == 0)
                        return;

                    //если есть выделенные столбцы - работаем с ними
                    if(selected_cols_length > 0) {
                        var to_hidden = [];
                        table.select_wrap.map(function(field, field_id){
                            if(table.selected_cols.indexOf(field_id) === -1 && table.hidden_cols.indexOf(field_id) === -1)
                                to_hidden.push(field_id);
                        });

                        table.hidden_cols = table.hidden_cols.concat(to_hidden);
                    } else {
                        //иначе скрываем невыделенные строки (оч долго)
                        table.data.forEach(function(line){
                            if(!_this.db({___id: line.___id}).get()[0].selected)
                                _this.db({___id: line.___id}).update({hidden_selected: true})
                        })
                    }

                    table.render();
                });

                if(fullscreen) {
                    _this.gridFullscreen();
                }

                _this.drawNavigation();
            },
            returnHidden: function(e, obj) {
                var fullscreen = false;
                if(_this.fullscreen) {
                    fullscreen = true;
                    _this.gridFullscreen();
                }

                _this.db().update({hidden_selected: false});

                _this.drawNavigation();

                _this.tables.forEach(function(table){
                    table.hidden_cols = [];

                    table.render();
                });
                _this.events.on_changed_block.show();
                if(fullscreen) {
                    _this.gridFullscreen();
                }
            },
            deselect: function(e, obj, type) {
                if(typeof type == 'undefined' || type == 'rows')
                    _this.db().update({selected: false});

                _this.tables.forEach(function(table){
                    _this.events.action_block.deselect_table(table, type);
                });
                _this.events.on_changed_block.show();
            },
            deselect_table: function(table, type) {
                var content_locked = table.content_locked.find('.row-selected, .col-selected'),
                    content_wrap   = table.content_wrap.find('.row-selected, .col-selected');

                if(typeof type == 'undefined' || type == 'cols') {
                    table.selected_cols = [];
                    table.header_wrap.find('th').removeClass('selected');
                    content_locked.removeClass('col-selected');
                    content_wrap.removeClass('col-selected');
                }

                if(typeof type == 'undefined' || type == 'rows') {
                    content_locked.removeClass('row-selected');
                    content_wrap.removeClass('row-selected');
                }
            },
            reverse: function(e, obj) {
                if(!_this.checkedFiltersLength()) {
                    return true;
                }

                var html = _this.preview_left_column.html();
                _this.preview_left_column.html(_this.preview_top_column.html());
                _this.preview_top_column.html(html);

                _this.events.on_changed_block.show();
                _this.events.preview_block.refresh();
            },
            default_state: function(e, obj) {
                //откатываем фильтры
                _this.events.on_changed_block.hide();
                var value;
                Object.keys(_this.filters).forEach(function(filter_id){
                    _this.filters[filter_id].filter_block = null;
                    _this.filters[filter_id].all = _this.filters[filter_id].default_all;
                    Object.keys(_this.filters[filter_id].values).forEach(function(value_id){
                        value = _this.filters[filter_id].values[value_id];
                        value.load = false;
                        value.checked = value.default_checked;
                    });
                });

                _this.tables = [];
                _this.groups = _this.default_params.groups;
                //закидываем туда группы
                if(_this.groups.length > 0) {
                    _this.group_block.html('');
                    _this.groups.forEach(function (group_id) {
                        _this.group_block.append(
                            '<th class="k-header align_left ui-draggable" data-field="' + group_id + '" data-field-sort="' + group_id + '" style="display: inline; margin: 5px; padding: 5px; min-width: 150px; opacity: 1;">' +
                            _this.filters[group_id].title +
                            '<span class="k-icon k-group-delete"></span></th>'
                        );
                    })
                } else {
                    _this.group_block.html(_this.group_block_text);
                }

                //подменяем столбцы
                _this.left_columns = _this.default_params.left_columns;
                _this.top_columns = _this.default_params.top_columns;

                _this.preparePreview();
                //_this.updateFiltersBlock(false);
                _this.updateData();
            },
            fullscreen: function(e, obj) {
                if(!_this.checkedFiltersLength()) {
                    return true;
                }

                if(_this.fullscreen) {
                    obj.html('<span class="icon-expand"></span>Развернуть');
                } else {
                    obj.html('<span class="icon-join"></span>Свернуть');
                }

                _this.gridFullscreen();
            },
            show_graphic: function(e, obj) {
                if(_this.map_filter != null && _this.left_columns.filter(function(i){ return _this.groups.indexOf(i) === -1 }).length == 1 && _this.left_columns.indexOf(parseInt(_this.map_filter)) > -1) {
                    $('.agrid-graphics-type-map').show();
                } else {
                    $('.agrid-graphics-type-map').hide();
                }
                if(yearTimer != null)
                    mapStopAnimation();

                jQuery('#agrid-graphics-content').html('');
                _this.chart = null;
                _this.chart_title = null;
                _this.graphics_block.modal();
            }
        },

        widget: {
            modal: function(e, obj) {
                if(_this.editor != null && _this.editor.isEnabled()) {
                    return _this.editor.showOnEnabledMessage();
                }
                var title = [_this.title];
                $.each(_this.filters_block_content.find('input.inp_checkbox:checked'), function() {
                    title.push($(this).parent().text());
                });

                $('#new_widget_title').val(title.join('. '));
                $('#enter_widget_name').modal();
                return true;
            },
            save: function(e, obj) {

            }
        },

        preview_block: {
            refresh: function(e, obj) {
                if(!$('#agrid-settings-block').is(':hidden'))
                    _this.setting_tab_button.click();

                var left_arr = [];
                jQuery.each(_this.preview_left_column.find('p'), function() {
                    left_arr.push(jQuery(this).data('field'));
                });

                var top_arr = [];
                jQuery.each(_this.preview_top_column.find('p'), function() {
                    top_arr.push(jQuery(this).data('field'));
                });

                var groups = [];
                jQuery.each(_this.preview_grouping.find('p'), function(){
                    groups.push(jQuery(this).data('field'));
                });

                //Добавление объектов групп в левую область для запроса нужно, чтобы
                //возвращались записи, иначе не будет полей для группировки
                left_arr = groups.concat(left_arr);

                if(top_arr.length ==0) {
                    alert('Неверная настройка представления - должен быть указан минимум один столбец');
                    return false;
                }
                _this.events.on_changed_block.show();

                _this.preview_block.find('.agrid-preview-content').hide();

                if(left_arr.join() != _this.left_columns.join() ||  top_arr.join() != _this.top_columns.join() || groups.join() != _this.groups.join()) {
                    _this.left_columns = left_arr;
                    _this.top_columns = top_arr;

                    _this.need_load_data = true;

                    _this.groups = groups;
                    //закидываем туда группы
                    if(_this.groups.length > 0) {
                        _this.group_block.html('');
                        _this.groups.forEach(function (group_id) {
                            _this.group_block.append(
                                '<th class="k-header align_left ui-draggable" data-field="' + group_id + '" data-field-sort="' + group_id + '" style="display: inline; margin: 5px; padding: 5px; min-width: 150px; opacity: 1;">' +
                                _this.filters[group_id].title +
                                '<span class="k-icon k-group-delete"></span></th>'
                            );
                        })
                    } else {
                        _this.group_block.html(_this.group_block_text);
                    }

                    _this.updateFiltersBlock(false);

                    //порядок столбцов
                    _this.columns = [];
                    _this.left_columns.forEach(function(filter_id){
                        _this.columns.push({
                            field: filter_id,
                            title: _this.filters[filter_id].title,
                            locked: true
                        });
                    });

                    var prev_obj = null;
                    _this.top_columns.forEach(function(filter_id){

                        if(prev_obj == null) {
                            prev_obj = {
                                field: filter_id,
                                title: _this.filters[filter_id].title
                            };

                            _this.columns.push(prev_obj);
                        } else {
                            var obj = {
                                field: filter_id,
                                title: _this.filters[filter_id].title
                            };
                            prev_obj.under = obj;
                            prev_obj = obj;
                        }
                    });

                    _this.prepareHeaders();

                    //загружаем данные
                    _this.updateData(null, function() {
                        _this.showDialogIsNull();
                    });
                } else {
                    _this.showDialogIsNull();
                }

                _this.preview_block.find('.agrid-preview-block-content').hide();
            }
        }
    };

    _this.callCheck = function(expr, callback, args) {
        //todo при добавлении нового режима нужно учитывать возможность вызова двух режимов одновременно
        switch (expr) {
            case 'editor':
                if(_this.editor != null && _this.editor.isEnabled())
                    return _this.editor.showOnEnabledMessage();
        }

        return callback.apply(_this, args);
    };

    _this.bindEvents = function() {
        //события кликов
        _this.main_block.on('click', function(e) {
            var obj = jQuery(e.target);

            var response = (function(obj) {
                switch (true) {
                    //событие клика по заголовку таблицы
                    case obj.hasClass('k-link'):
                        return _this.events.theader.sort;
                    case obj.hasClass('agrid-group-a'):
                        return _this.events.groups.click;
                    case obj.hasClass('k-filter'):
                        return _this.events.filter.click;
                    case obj.hasClass('k-check-filter'):
                        return _this.events.filter.check_value;
                    case obj.hasClass('k-filter-load'):
                        return _this.events.filter.filter;
                    case obj.hasClass('k-grid-cover-title-a'):
                        obj.parent().toggleClass('k-grid-cover-title-act')
                            .next().toggle("slow");
                        return false;
                    case obj.hasClass('k-check-all'):
                        return _this.events.filter.checkAll;
                        break;
                    default :
                        return 'method-not-found';
                }
            })(obj);

            if(response !== 'method-not-found') {
                $('.dropdown').stop().slideUp(200); $(document).off('click.myEvent');
            }

            if(typeof response === 'function')
                return _this.callCheck('editor', response, [e, obj]);

            return response;
        });

        //todo перенести в events
        _this.filters_block_content.on('click', function(e) {
            var obj = jQuery(e.target);
            switch (true) {
                case obj.hasClass('agrid-filter-check'):
                    //текущий элемент
                    if(!obj.prop('checked')) {
                        return false;
                    }

                    //иначе происходит выделение, поэтому сбрасываем все фильтры и выделяем текущий
                    obj.closest('.dropdown').stop().slideUp(200).find('.agrid-filter-check').prop('checked', false);
                    obj.prop('checked', true);
                    $(document).off('click.myEvent');

                    var filter_id = obj.data('filter'),
                        checked_value = obj.data('field');

                    //удалим контекстный блок с фильтрами чтобы не париться, он все равно пересоздастся, но при этом будет актуальным
                    if(_this.filters[filter_id].filter_block != null) {
                        _this.filters[filter_id].filter_block.remove();
                        _this.filters[filter_id].filter_block = null;
                    }

                    Object.keys(_this.filters[filter_id].values).forEach(function(value_id){
                        _this.filters[filter_id].values[value_id].checked = (value_id == checked_value);
                        /*if(value_id == checked_value)
                            _this.filters[filter_id].values[value_id].checked = true;
                        else
                            _this.filters[filter_id].values[value_id].checked = false;*/
                    });

                    //обновляем грид
                    _this.events.filter.filter();
                    break;
                //return _this.events.filter.click(obj);
                case obj.hasClass('dropdown_trigger') && !obj.hasClass('tied'):
                    var $this = obj,
                        $dropdown = $this.closest('.dropdown_wrap').find('.dropdown');

                    if ($dropdown.css('display') != 'block') {
                        $dropdown.stop().slideToggle(200);

                        var t = true;
                        $(document).on('click.myEvent', function (e) {
                            if (!t && jQuery(e.target).closest($dropdown).length == 0) {
                                _this.filters_block_content.find('.dropdown').stop().slideUp(200);
                                $(document).off('click.myEvent');
                            }

                            t = false;
                        })
                    }
                    e.preventDefault();
                    break;
                default :
            }
        });

        _this.group_block.on('click', function(e){
            var obj = jQuery(e.target);
            switch (true) {
                //событие удаления группировки
                case obj.hasClass('k-group-delete'):
                    return _this.callCheck('editor', _this.events.group_block.drop, [e, obj]);
                default :
                //return false;
            }
        });

        _this.navigation_block.on('click', function(e){
            var obj = jQuery(e.target);
            switch (true) {
                case obj.hasClass('k-pager-nav') && !obj.hasClass('k-state-disabled'):
                    return _this.events.navigation.click(e, obj);
                case obj.parent().hasClass('k-pager-nav') && !obj.parent().hasClass('k-state-disabled'):
                    return _this.events.navigation.click(e, obj.parent());
                default :
            }
        });

        _this.action_block.on('click', function(e) {
            var obj = jQuery(e.target);

            var response = (function(obj){
                switch (true) {
                    case obj.hasClass('agrid-action-select-all-rows'):
                        return _this.events.action_block.selectAllRows;
                    case obj.hasClass('agrid-action-select-all-cols'):
                        return _this.events.action_block.selectAllCols;
                    case obj.hasClass('agrid-action-hide-selected'):
                        return _this.events.action_block.hideSelected;
                    case obj.hasClass('agrid-action-hide-only-deselected'):
                        return _this.events.action_block.hideOnlyDeselected;
                    case obj.hasClass('agrid-action-return-hidden'):
                        return _this.events.action_block.returnHidden;
                    case obj.hasClass('agrid-action-deselect'):
                        return _this.events.action_block.deselect;
                    case obj.hasClass('agrid-action-reverse'):
                        return _this.events.action_block.reverse;
                    case obj.hasClass('agrid-action-default-state'):
                        return _this.events.action_block.default_state;
                    case obj.hasClass('agrid-action-fullscreen'):
                        return _this.events.action_block.fullscreen;
                    case obj.hasClass('agrid-action-enable-editor'):
                        $('.dropdown').stop().slideUp(200); $(document).off('click.myEvent');
                        _this.editor.toggle();
                        return false;
                    case obj.hasClass('agrid-action-create-widget'):
                        return _this.events.widget.modal;
                    default :
                        return 'method-not-found';
                }
            })(obj);

            if(typeof response === 'function') {
                $('.dropdown').stop().slideUp(200); $(document).off('click.myEvent');
                return _this.callCheck('editor', response, [e, obj]);
            }

            return e.preventDefault();
        });

        $('#grid_to_widget').on('click', function(e){
            if(_this.checkedFiltersLength()) {
                return _this.callCheck('editor', _this.events.widget.modal, [e, jQuery(e.target)]);
            }

            return true;
        });

        $('#grid_to_widget2').click(function(){
            if(_this.editor != null && _this.editor.isEnabled()) {
                return _this.editor.showOnEnabledMessage();
            }
            var newWidgetTitle = $('#new_widget_title'),
                title = newWidgetTitle.val().replace(/^\s*/, '').replace(/\s*$/, '');

            if(title == '') {
                newWidgetTitle.parent().addClass('has-error');
                return false;
            }

            _this.saveGridWidget(title);
            $('#enter_widget_name').modal('hide');
            return false;
        });

        $('#download_excel_file').click(function(e){
            if (navigator.webdriver || !e.originalEvent || !e.originalEvent.isTrusted) return;
            if(_this.editor != null && _this.editor.enabled) {
                return _this.editor.showOnEnabledMessage();
            }
            _this.downloadFile('excel');
            return false;
        });

        $('#download_sdmx_file').click(function(e){
            if (navigator.webdriver || !e.originalEvent || !e.originalEvent.isTrusted) return;
            if(_this.editor != null && _this.editor.enabled) {
                return _this.editor.showOnEnabledMessage();
            }
            _this.downloadFile('sdmx');
            return false;
        });

        $('#agrid-action-create-graphic').click(function(){
            if(_this.editor != null && _this.editor.isEnabled()) {
                return _this.editor.showOnEnabledMessage();
            }

            if(_this.checkedFiltersLength()) {
                return _this.events.action_block.show_graphic($(this));
            }

            return true;
        });

        _this.preview_block.on('click', function(e) {
            var obj = jQuery(e.target);
            switch (true) {

                case _this.editor != null && _this.editor.isEnabled():
                    return _this.editor.showOnEnabledMessage();
                case obj.hasClass('agrid-action-preview-default-state'):
                    return _this.events.action_block.default_state(e, obj);
                case !_this.checkedFiltersLength():
                    return true;
                case obj.hasClass('agrid-action-preview-refresh'):
                    return _this.events.preview_block.refresh(e, obj);
                case obj.hasClass('agrid-action-preview-save'):
                    return _this.savePreview(obj);
            }
        });

        $("#agrid-action-default-state2").on('click', function(){
            if(_this.editor != null && _this.editor.isEnabled()) {
                return _this.editor.showOnEnabledMessage();
            }
            return _this.events.action_block.default_state();
        });

        _this.graphics_block.on('click', function(e){
            if(_this.editor != null && _this.editor.isEnabled()) {
                return _this.editor.showOnEnabledMessage();
            }
            var obj = jQuery(e.target);

            var mapTitle = jQuery('#agrid-graphics-content').find('.agrid-map-title');
            if(mapTitle.length) {
                _this.chart_title = mapTitle.html();
            }

            switch (true) {
                case obj.hasClass('agrid-graphics-type-line'):
                    _this.createGraphic('line');
                    break;
                case obj.hasClass('agrid-graphics-type-gist'):
                    _this.createGraphic('gist');
                    break;
                case obj.hasClass('agrid-graphics-type-map'):
                    _this.createGraphic('map');
                    break;
                case obj.hasClass('agrid-graphics-type-add-widget'):
                    _this.addToWidget();
                    _this.graphics_block.modal('hide');
                    _this.chart = null;
                    _this.chart_title = null;
                    break;
            }
        });
    };

    //блок с фильтрами, которые не показываются в гриде
    _this.filters_block_tab = jQuery('#agrid-filters-tab');
    _this.filters_block_content = jQuery('#agrid-filters-content');

    //блок со столбцами для группировки
    _this.group_block = jQuery('<div class="agrid-column-block" id="sortable">')
        .text(_this.group_block_text)
        .append('<span class="hidden-p"></span>')
        .sortable(_this.options.sortable)
    ;
    _this.group_block.find('.hidden-p').remove();

    //блок с настройками представления
    _this.preview_block = jQuery('#agrid-settings-block');
    _this.preview_block.disableSelection();
    _this.preview_left_column = _this.preview_block.find('div.agrid-preview-left-column');
    _this.preview_top_column = _this.preview_block.find('div.agrid-preview-top-column');
    _this.preview_grouping = _this.preview_block.find('div.agrid-preview-grouping');
    _this.preview_filters = _this.preview_block.find('div.agrid-preview-filters');

    _this.navigation_block = jQuery('<div class="k-pager-wrap k-grid-pager k-widget">').hide();

    _this.init = function(callback)
    {
        _this.root_block.empty().css({
            width: _this.field_params.main_block_width + 'px',
            overflow: 'hidden'
        });

        //выводим блоки
        _this.root_block.append([
            _this.header_block.append([
                _this.filters_main_block,
                _this.group_block
                //_this.preview_block
            ]),
            _this.main_block,
            _this.footer_block.append([
                _this.navigation_block,
                _this.loader,
                _this.graphics_block
            ])
        ]);

        _this.bindEvents();

        _this.prepareHeaders();

        _this.preparePreview();

        //загружаем данные
        _this.updateData(null, function() {
            if(typeof callback != 'undefined') callback();
            _this.showDialogIsNull();
        });
    };

    _this.preparePreview = function() {
        _this.updateFiltersBlock(false);

        var line_arr = [];
        _this.left_columns.forEach(function(filter_id){
            if(_this.groups.indexOf(filter_id) === -1)
                line_arr.push('<p data-field="'+ filter_id +'">'+ _this.filters[filter_id].title +'</p>');
        });
        _this.preview_left_column.html(line_arr.join(''));

        var column_arr = [];
        _this.top_columns.forEach(function(filter_id){
            if(_this.groups.indexOf(filter_id) === -1)
                column_arr.push('<p data-field="'+ filter_id +'">'+ _this.filters[filter_id].title +'</p>');
        });
        column_arr.push('<br clear="all">');
        _this.preview_top_column.html(column_arr.join(''));

        var groups = [];
        _this.group_block.html('');
        _this.groups.forEach(function(filter_id){
            groups.push('<p data-field="'+ filter_id +'">'+ _this.filters[filter_id].title +'</p>');

            _this.group_block.append([
                '<th class="k-header align_left ui-draggable" data-field="'+ filter_id +'" data-field-sort="'+ filter_id +'" style="display: inline; margin: 5px; padding: 5px; min-width: 150px; opacity: 1;">' +
                _this.filters[filter_id].title +
                '<span class="k-icon k-group-delete"></span>' +
                '</th>'
            ].join(''));
        });
        if(!_this.groups.length)
            _this.group_block.html(_this.group_block_text);
        _this.preview_grouping.html(groups.join(''));

        _this.preview_block.find('.agrid-preview-column').sortable({
            connectWith: ".agrid-preview-column",
            over: function(event, ui) {
                $(event.target).find('br').remove().end().append('<br clear="all">');
            },
            start: function(e,ui){
                ui.placeholder.height(ui.item.height()).width(ui.item.width());
            },
            //удаляем дублирующийся фильтр, перенесенный из другово блока
            receive: function(event, ui) {
                if(jQuery(event.target).find('p[data-field="'+ jQuery(ui.item).data('field') +'"]').length > 1)
                    jQuery(ui.item).remove();
            }
        });

        _this.preview_block.find('.hidden-p').remove();
    };

    //обновление блока неиспользуемых фильтров
    _this.updateFiltersBlock = function(need_filtration) {
        _this.filters_block_content.html('');

        var filters_arr = [], filters_count = 0, checked;//_this.system_filters
        Object.keys(_this.filters).forEach(function(filter_id){
            if(_this.left_columns.indexOf(parseInt(filter_id)) > -1 || _this.top_columns.indexOf(parseInt(filter_id)) > -1)
                return;

            if(_this.groups.indexOf(parseInt(filter_id)) === -1) {
                filters_arr.push('<p data-field="' + filter_id + '">' + _this.filters[filter_id].title + '</p>');
            } else {
                return;
            }

            if(_this.system_filters.indexOf(parseInt(filter_id)) > -1)
                return;

            filters_count++;

            checked = false;
            _this.filters_block_content.append([
                '<div class="sp_filname">',
                '<div class="dropdown_wrap"><span class="dropdown_trigger">'+ _this.filters[filter_id].title +'<span class="icon-arrow_down"></span></span>',
                '<div class="dropdown" style="max-height: 300px; overflow: auto"><ul>',
                _this.objectKeys(filter_id).map(function(value_id){
                    var value = _this.filters[filter_id].values[value_id],
                        this_checked = false;

                    if(!checked && value.checked) {
                        value.checked = this_checked = checked = true;
                    } else {
                        value.checked = false;
                    }

                    return [
                        '<li>',
                        '<div class="checkbox_wrap">',
                        '<label class="lbl_checbox">',
                        '<input type="checkbox" class="inp_checkbox agrid-filter-check hide" data-filter="'+ filter_id +'" data-field="'+ value_id +'" '+ (this_checked ? 'checked' : '') +'><span class="sp_checkbox"></span>' + value.title,
                        '</label>',
                        '</div>',
                        '</li>'
                    ].join('');
                }).join('') ,
                '</ul></div>',
                '</div>',
                '</div>'
            ].join(''));
        });

       // _this.filters_block_content.find('.dropdown');//.mCustomScrollbar(_this.options.mCustomScrollbar('y'));

        //если хоть один фильтр есть - показываем блок настройки
        if(filters_count) {
            _this.filters_block_tab.html('<span class="icon-filters"></span>Фильтры <span class="num">'+ filters_count +'</span>').show();
            if(_this.filters_block_tab.hasClass('cont_tit_act')) {
                _this.filters_block_content.show();
            }
        } else {
            //иначе скрываем
            _this.filters_block_tab.removeClass('cont_tit_act');
            _this.filters_block_content.hide();
            _this.filters_block_tab.hide();
        }

        filters_arr.push('<br clear="all">');
        _this.preview_filters.html(filters_arr.join(''));

        if(need_filtration)
            _this.events.filter.filter();
    };

    //ф-ия обновления данных
    _this.updateData = function(beforeUpdate, afterUpdate) {
        if(typeof beforeUpdate != 'undefined' && beforeUpdate != null) beforeUpdate();

        var fullscreen = false;
        if(_this.fullscreen) {
            fullscreen = true;
            _this.gridFullscreen();
        }

        _this.loadData(function(){
            //формируем заголовки
            _this.prepareHeaders();
            //создаем таблицы
            _this.createTables();
            //откатываем счетчик страниц
            _this.page = 1;
            //перерисовываем навигацию
            _this.drawNavigation();
            //в зависимости от навигации отрисовываем таблицы
            switch (_this.navType) {
                case _this.navTypes.maxTables:
                    //отображаем только видивые таблицы
                    var iterator = 0;
                    _this.tables.forEach(function(table){
                        if(iterator >= (_this.page - 1) * _this.groups_limit && iterator < (_this.page - 1) * _this.groups_limit + _this.groups_limit) {
                            if (!table.inited)
                                table.init();
                            if(!table.rendered)
                                table.render();

                            table.show();
                        }
                        else {
                            table.hide();
                        }
                        iterator++;
                    });
                    break;
                case _this.navTypes.maxRows:
                    _this.tables.forEach(function(table){
                        table.render();
                        table.show();
                    });
                    break;
                case _this.navTypes.is_default:
                    _this.tables.forEach(function(table) {
                        table.render();
                        table.show();
                    });
                    break;
            }

            if(fullscreen) {
                _this.gridFullscreen();
            }

            if(typeof afterUpdate != 'undefined' && afterUpdate != null) afterUpdate();
        });
    };

    _this.loadData = function(callback) {
        var url = _this.url + _this.id ;//+ '&';

        //параметры для строки запроса
        var params = [];
        //новые параметры(которые не были загружены)
        var new_params = [];

        _this.events.loader.show();

        var params_data = '';

        //а если их сразу сделать все видимые, а скрытые после скрыть? тогда они не будут пересекаться вроде
        _this.time('Скрытие отфильтрованных данных в базе');
        _this.db({hidden: {is: true}}).update('hidden', false);
        Object.keys(_this.filters).forEach(function(owner_id){
            var filter = _this.filters[owner_id];
            Object.keys(filter.values).forEach(function(filter_id){
                //непопадающие под фильтры записи скрываем
                var where = {hidden: false};
                var value = filter.values[filter_id];
                where['dim' + owner_id] = value.title;

                if(!filter.all && !value.checked) {
                    _this.db(where).update('hidden', true);
                } else {
                    params.push({owner_id: owner_id, filter_id: filter_id});
                    new_params.push({owner_id: owner_id, filter_id: filter_id});
                }
            })
        });
        _this.timeEnd('Скрытие отфильтрованных данных в базе');

        if(new_params.length == 0 && !_this.need_load_data) {
            _this.log('загрузка не потребовалась');
            callback();
            _this.events.loader.hide();
            return;
        }

        _this.need_load_data = false;

        //добавляем группы которые не определены в левом или правом столбцах
        var groups = _this.groups
            .filter(function(id){
                return _this.left_columns.indexOf(id) === -1 && _this.top_columns.indexOf(id) === -1;
            })
            .map(function(id){
                return 'lineObjectIds=' + id;
            });

        //добавим фильтры, которые не определены в левом или правом столбцах
        var filters = Object.keys(_this.filters)
            .filter(function(key){
                key = parseInt(key);
                return _this.left_columns.indexOf(key) === -1 && _this.top_columns.indexOf(key) === -1;
            })
            .map(function(id){
                return 'lineObjectIds=' + id;
            });

        params_data +=
            (filters.length ? filters.join('&') + '&' : '')
            + (groups.length ? groups.join('&') + '&' : '')
            + _this.left_columns.map(function(id) { return 'lineObjectIds=' + id; }).join('&')
            + '&'
            + _this.top_columns.map(function(id) { return 'columnObjectIds=' + id; }).join('&');

        params_data += '&' + params.map(function(param){
            return 'selectedFilterIds=' + param.owner_id + '_' + param.filter_id;
        }).join('&');

        jQuery.ajax({
            url: url,
            type: 'post',
            dataType: 'json',
            data: params_data,
            beforeSend: function(data) {
                _this.time('Загрузка данных с сервера');
            }
        }).done(function(data){
            if(typeof data.results != 'undefined') {
                //Преобразуем в наш формат и находим уникальные столбцы текущего набора данных
                var results = [];

                _this.d_i = {};

                //нужно сделать базу однородной, от этого зависит работа сортировки
                //задаем шаблон для вставляемых записей
                _this.db_template = {hidden: false, selected:false, hidden_selected: false, table_id: undefined};

                data.results.forEach(function(line, line_index){
                    var new_line = {}, value;
                    line.__id = line_index;
                    Object.keys(line).forEach(function(value_key){
                        if(!/.*?_d\d{0,}_i\d{0,}$/.test(value_key)) {
                            new_line[value_key] = line[value_key];
                            _this.db_template[value_key] = '';
                        } else {
                            var tmp = value_key.split('_'),
                                d_i = tmp.splice(tmp.length - 2, 2),
                                new_value_key = tmp.join('_');

                            if(typeof _this.d_i['line' + line.__id] == 'undefined') {
                                _this.d_i['line' + line.__id] = {};
                            }

                            value = line[value_key];
                            if (value) {
                                new_line[new_value_key] = parseFloat(value.toString().replace(',', '.'));
                            } else {
                                new_line[new_value_key] = 0;
                            }
                            //new_line[new_value_key] = line[new_value_key + '_' + d_i.join('_')];

                            _this.db_template[new_value_key] = _this.null_value;

                            _this.d_i['line' + line.__id][new_value_key] = {
                                d: d_i[0].replace('d', ''),
                                i: d_i[1].replace('i', '')
                            };
                        }
                    });
                    results.push(new_line);
                });

                _this.db = TAFFY();

                _this.groups.forEach(function(group){
                    if(Object.keys(_this.db_template).indexOf('dim' + group) === -1)
                        _this.db_template['dim' + group] = '';
                });

                _this.db.settings({template: _this.db_template});

                _this.db.insert(results);

                //скроем ненужные записи
                Object.keys(_this.filters).forEach(function(owner_id) {
                    var objectId = parseInt(owner_id);
                    var isFilterObject = _this.left_columns.indexOf(objectId) === -1 && _this.top_columns.indexOf(objectId) === -1 && _this.groups.indexOf(objectId) === -1;
                    Object.keys(_this.filters[owner_id].values).forEach(function (filter_id) {
                        var where = {hidden: false};
                        where['dim' + owner_id] = _this.filters[owner_id].values[filter_id].title;
                        if ((isFilterObject || !_this.filters[owner_id].all) && !_this.filters[owner_id].values[filter_id].checked) {
                            _this.db(where).update('hidden', true);
                        }
                    })
                })
            }

            params.forEach(function(param) {
                _this.filters[param.owner_id].values[param.filter_id].load = true;
            });

            _this.timeEnd('Загрузка данных с сервера');

            if(typeof callback != 'undefined')
                callback();

            _this.events.loader.hide();
        }).error(function(e){
            _this.log(e);
            _this.log('Ошибка при загрузке данных');
        });
    };

    /**
     * Здесь наша задача получить шаблон для вывода данных из базы и получить html для фикс и мульти заголовков
     */
    _this.prepareHeaders = function() {
        _this.tables = [];
        _this.line_template_fixed = [];
        _this.line_template_wrap = [];

        _this.time('Формирование заголовков');

        _this.locked_header.html('');
        _this.wrap_header.html('');

        _this.prepareFixedHeaders();

        _this.prepareWrapHeaders();

        _this.timeEnd('Формирование заголовков');
    };

    _this.prepareFixedHeaders = function()
    {
        var html_locked = [], column;

        _this.left_columns.forEach(function(column_id) {
            //если есть группировка по этому столбцу - не отрисовываем
            if (_this.groups.indexOf(column_id) > -1)
                return;

            column = _this.filters[column_id];

            html_locked.push(
                '<th class="k-header align_left" data-field="'+ column_id +'" data-field-sort="'+ column_id +'">' +  
                '<a class="k-grid-filter k-state-active" href="#" tabindex="-1"><span class="k-icon k-filter"></span></a>' +
                '<a class="k-link" href="#">'+ column.title +'</a>' + '</th>'
            );

            _this.line_template_fixed.push("dim" + column_id);
        });

        _this.locked_header.html('<table><thead><tr>'+ html_locked.join('') +'</tr></thead></table>');
    };

    _this.prepareWrapHeaders = function() {
        var top_columns = _this.top_columns.slice(),
            top_columns_length = top_columns.length,
            levels = [],
            masks = [];

        //формируем маски и значения столбцов
        top_columns.forEach(function(column, level_id){
            if(level_id == top_columns_length - 1) {
                //последний
            }

            if(typeof levels[level_id] == 'undefined')
                levels[level_id] = [];

            if(masks.length == 0) {
                //проход по первой строке
                if(_this.groups.indexOf(column) > -1) {
                    masks.push('{'+ column +'}');
                    return;
                }
                _this.objectKeys(column, true).forEach(function(value) {
                    masks.push(value);

                    levels[level_id].push({
                        title: _this.filters[column].values[value].title,
                        mask: value,
                        field: column
                    });
                });
            } else {
                var new_masks = [];
                masks.forEach(function(mask) {
                    if(_this.groups.indexOf(column) > -1) {
                        new_masks.push(mask + '_{'+ column +'}');
                        return;
                    }

                    _this.objectKeys(column, true).forEach(function(value) {
                        new_masks.push(mask + '_' + value );

                        levels[level_id].push({
                            title: _this.filters[column].values[value].title,
                            mask: mask + '_' + value,
                            field: column
                        });
                    });
                });

                masks = new_masks;
            }
        });

        //формируем столбцы
        var html = [];
        var last_level = null;// = levels[levels.length - 1] || null;
        //найдем последний непустой уровень
        for(var i = levels.length; i--;) {
            if(levels[i].length) {
                last_level = levels[i];
                break;
            }
        }

        levels.forEach(function(level, level_id){
            level.forEach(function(field, field_id){
                var colspan = 0;
                if(last_level != null && last_level.length > 0) {
                    colspan = last_level.length / level.length;
                }

                level[field_id] = [
                    '<th class="k-header" ' +
                    (colspan > 1 ? 'colspan="'+ colspan +'" data-colspan="'+ colspan +'"' : ''),
                    ' data-field-sort="'+ field.mask +'"',
                    ' data-field="'+ field.field +'" >',                    
                    (
                        level_id == top_columns_length - 1 ?
                        '<a class="k-grid-filter k-state-active" href="#" tabindex="-1"><span class="k-icon k-filter"></span></a><a class="k-link" href="#" style="text-align: center;">'+ field.title +'</a>' :
                        '<span class="k-gr-span">' + field.title + '</span><a class="k-grid-filter mrl22m k-state-active k-fil-non" href="#" tabindex="-1"><span class="k-icon k-filter"></span></a>'
                    ),
                    //'<a class="k-grid-filter k-state-active" href="#" tabindex="-1"><span class="k-icon k-filter"></span></a>',
                    '</th>'
                ].join('');
            });

            if(level.length > 0)
                html.push('<tr>'+ level.join('') +'</tr>');
        });

        _this.line_template_wrap = masks.map(function(mask) {
            return 'dim' + mask;
        });

        _this.wrap_header.html('<table><thead>'+ html.join('') +'</thead></table>')
    };

    _this.createTables = function()
    {
        var groups = _this.groups.slice();
        //очищаем старые данные
        _this.main_block.html('');

        if(groups.length > 0)
        {
            //если группы определены - создаем для каждой группы таблицу
            var group = groups.shift();
            //при отрисовке групповых таблиц будем сразу генерить настройку представления для виджетов
            _this.groupsToWidget = [];
            _this.createGroupTable(group, groups, [], _this.main_block, '');
            _this.groupsToWidget = _this.groupsToWidget.map(function(obj){
                return obj.parent_data.map(function(parent){
                    return parent.key.toString() + '_' + parent.val.toString();
                }).join('-');
            });
        }
        else
        {
            //иначе создаем одну таблицу
            var table = new FTable({
                grid: _this
            });

            //инициализируем ее
            table.init();

            //выводим ее обертку в наш главный блок
            _this.main_block.append(table.main_block);

            //и сохраняем в массиве таблиц для дальнейших операций
            _this.tables.push(table);
        }
    };

    _this.createGroupTable = function(group_id, _groups, prev, to_block, parent_title)
    {
        var groups = _groups.slice();

        var next_group = groups.length > 0 ? groups.shift() : false;

        _this.objectKeys(group_id).forEach(function(filter_id) {
            if(!_this.filters[group_id].all && !_this.filters[group_id].values[filter_id].checked)
                return;

            var parent_data = prev.slice();
            parent_data.push({
                key: group_id,
                val: filter_id
            });

            var group = _this.filters[group_id].values[filter_id];

            var group_block = jQuery('<div class="k-grid-group-block">');
            if(_this.navType == _this.navTypes.maxTables)
                group_block.addClass('k-grid-group-block-hidden');

            group_block.html("<div class='k-grid-cover-title'><a class='k-grid-cover-title-a' href='#'>"+ group.title +"</a><span class='k-icon k-filter' data-field='"+ group_id +"'></span></div>");

            var group_content = jQuery('<div class="k-grid-group-content">');

            //если есть следующая группа - выводим
            if(next_group !== false) {
                _this.createGroupTable(next_group, groups, parent_data, group_content, parent_title + group.title + ', ');
            }
            //иначе отрисовываем данные
            else {
                //столбцы в том порядке, в котором будем выводить
                var select_locked = _this.line_template_fixed;
                var select_wrap = _this.line_template_wrap;
                //условие для выборки
                var where = {};

                //преобразовываем строку запроса и заполняем условие
                parent_data.forEach(function(obj) {
                    select_locked = select_locked.map(function(r){
                        return r.replace('{' + obj.key + '}', obj.val);
                    });

                    select_wrap = select_wrap.map(function(r){
                        return r.replace('{' + obj.key + '}', obj.val);
                    });

                    var filter = _this.filters[obj.key];

                    //если поле фиксированное или не используется в отображении - делаем по нему выборку
                    if(_this.top_columns.indexOf(obj.key) === -1 && typeof _this.db_template['dim' + obj.key] != 'undefined') {
                        where["dim" + obj.key] = filter.values[obj.val].title.toString();
                    }
                });

                //если в select_wrap нет ни одного поля в db.template - не отрисовываем эту таблицу
                var empty = true;
                for(var i in select_wrap) {
                    if(typeof _this.db_template[select_wrap[i]] != 'undefined') {
                        empty = false;
                        break;
                    }
                }

                //console.log(select_wrap)

                if(!empty) {
                    var table = new FTable({
                        grid: _this,
                        where: where,
                        select_locked: select_locked,
                        select_wrap: select_wrap,
                        parent_data: parent_data,
                        title_to_graphic: parent_title + group.title + ', '//parent_title
                    });

                    _this.groupsToWidget.push({
                        id: table.id,
                        parent_data: parent_data
                    });

                    group_content.append(table.main_block);

                    _this.tables.push(table);
                }
            }

            //если группа пустая - не добавляем ее
            if(group_content.children().length) {
                group_block.append(group_content);
                to_block.append(group_block);
            }
        });

    };

    _this.getCheckedFilters = function(parent_id) {
        var filters = {};

        var objectId = parseInt(parent_id);
        var isFilterObject = _this.left_columns.indexOf(objectId) === -1 && _this.top_columns.indexOf(objectId) === -1 && _this.groups.indexOf(objectId) === -1;
        if (!isFilterObject && !!_this.filters[parent_id].all)
            return _this.filters[parent_id].values;

        _this.objectKeys(parent_id).forEach(function(filter_id){
            if(_this.filters[parent_id].values[filter_id].checked)
                filters[filter_id] = _this.filters[parent_id].values[filter_id];
        });

        return filters;
    };

    _this.drawNavigation = function() {
        //определяем тип навигации
        _this.navType = _this.navTypes.is_default;

        var tables_count = _this.tables.length ? _this.tables.length : 1;

        //todo
        if(tables_count >= 10) {
            //if(tables_count >= _this.db({hidden: false}).count()) {
            _this.navType = _this.navTypes.maxTables;
        } else if(_this.groups.length > 0) {
            _this.navType = _this.navTypes.maxRows;
        }

        //находим колво страниц для определенного типа
        switch (_this.navType) {
            case _this.navTypes.maxTables:
                _this.page_count = Math.ceil(tables_count / _this.groups_limit);
                _this.groups_iterator = 0;
                break;
            case _this.navTypes.maxRows:
                _this.page_count = 1;
                break;
            default :
                _this.page_count = Math.ceil( _this.db({hidden: false, hidden_selected: false}).count() / _this.limit);
        }

        if(_this.page_count <= 1) {
            _this.page = 1;
            _this.navigation_show = false;
            _this.navigation_block.empty().hide();
            return;
        }

        _this.navigation_show = true;

        //добавляем кнопки
        var html = [];
        html.push('<a href="#" title="Вернуться на первую страницу" class="k-link k-pager-nav k-pager-first '+ (_this.page == 1 ? 'k-state-disabled' : '') +'" data-page="1" tabindex="-1"><span class="sp_vper">‹‹</span></a>');
        html.push('<a href="#" title="Перейти на предыдущую страницу" class="k-link k-pager-nav '+ (_this.page == 1 ? 'k-state-disabled' : '') +'" data-page="'+ (_this.page - 1) +'" tabindex="-1"><span class="sp_vper">‹</span></a>');

        html.push('<ul class="k-pager-numbers k-reset">');

        //уменьшаем страницу если данные скрывались
        if(_this.page > _this.page_count)
            _this.page = _this.page_count;

        for(var i = _this.page - _this.page_count_visible + 1; i < _this.page + _this.page_count_visible; i++) {
            if(i >= 1 && (i <= _this.page_count || i == _this.page)) {
                //если текущая страница
                if(i == _this.page) {
                    html.push('<li><span class="k-state-selected">'+ i +'</span></li>');
                } else {
                    html.push('<li><a tabindex="-1" href="#" class="k-link k-pager-nav" data-page="'+ i +'">'+ i +'</a></li>');
                }
            }
        }
        html.push('</ul>');

        html.push('<a href="#" title="Перейдите на следующую страницу" class="k-link k-pager-nav '+ (_this.page == _this.page_count ? 'k-state-disabled' : '') +'" data-page="'+ (_this.page + 1) +'" tabindex="-1"><span class="sp_vper">›</span></a>');
        html.push('<a href="#" title="К последней странице" class="k-link k-pager-nav k-pager-last '+ (_this.page == _this.page_count ? 'k-state-disabled' : '') +'" data-page="'+ _this.page_count +'" tabindex="-1"><span class="sp_vper">››</span></a>');

        _this.navigation_block.html(html.join('')).show();
    };

    _this.gridFullscreen = function(save_size) {
        save_size = typeof save_size != 'undefined' ? save_size : true;
        var max_width = jQuery(window).width() - 100 - (_this.groups.length * _this.field_params.group_padding);

        //если уже развернутый - возвращаем по дефолту
        if(_this.fullscreen) {
            _this.root_block.css({
                width: _this.field_params.main_block_width,
                'margin-left': '0px'
            });

            _this.tables.forEach(function(table) {
                table.main_block.css({
                    width: table.table_size.prev.main_block_width
                });

                table.header_wrap.css({
                    width: table.table_size.prev.header_wrap_width
                });

                table.content_wrap.css({
                    width: table.table_size.prev.content_wrap_width
                });
                table.table_size.curr = jQuery.extend({}, table.table_size.prev);
            });
        } else {
            //иначе разворачиваем
            //находим первую таблицу
            _this.tables.forEach(function(table) {
                //для начала проверим, чтобы таблица заголовков была больше блока заголовков, иначе смысла в разворачивании нет
                if(table.header_wrap.width() >= table.header_wrap.find('table').width())
                    return;

                //требуемая ширина таблицы
                var table_width = table.content_locked.width() + table.content_wrap.find('table').width();
                if(save_size)
                    table.table_size.prev = jQuery.extend({}, table.table_size.curr);

                table.table_size.curr = {
                    content_wrap_table_width: table.table_size.prev.content_wrap_table_width
                };

                var new_root_block_width = 0;
                if(table_width < max_width) {
                    //разворачиваем полностью
                    new_root_block_width = (table_width + 2 + (_this.groups.length * _this.field_params.group_padding)) + 'px'; //+скролл на всякий случай
                    table.table_size.curr.main_block_width = table_width + 'px';
                    //нухай авто
                    table.table_size.curr.header_wrap_width = (table_width - table.content_locked.width() - 1) + 'px';//'auto';
                    table.table_size.curr.content_wrap_width = (table_width - table.content_locked.width()) + 'px';//'auto';
                } else {
                    //иначе разворачиваем только контент
                    new_root_block_width = (max_width + 4) + 'px'; //4 px - на всяк случай, бордеры и отступы
                    table.table_size.curr.main_block_width = (max_width) + 'px';
                    table.table_size.curr.header_wrap_width = (max_width - table.content_locked.width() - 1) + 'px';
                    table.table_size.curr.content_wrap_width = (max_width - table.content_locked.width()) + 'px';
                }

                table.table_size.curr.root_block_width = new_root_block_width;

                if(_this.root_block.width() < parseInt(table.table_size.curr.root_block_width)) {
                    _this.root_block.css({
                        width: table.table_size.curr.root_block_width,
                        'margin-left': ((parseInt(table.table_size.curr.root_block_width) - parseInt(table.table_size.prev.root_block_width)) * -1) / 2 + 'px'
                    });
                }

                table.main_block.css({
                    width: table.table_size.curr.main_block_width
                });

                table.header_wrap.css({
                    width: table.table_size.curr.header_wrap_width
                });

                table.content_wrap.css({
                    width: table.table_size.curr.content_wrap_width
                });
            })

        }

        _this.fullscreen = !_this.fullscreen;
    };

    _this.saveGridWidget = function (title) {
        var data = [];
        _this.events.loader.show();
        var groups = _this.groups.slice();

        _this.groupsToWidgetIterator = 0;
        if(groups.length > 0) {
            data = _this.createGroupsToWidget(groups.shift(), groups, '');
        }
        else {
            data.push({type:'table', table: _this.prepareTableToWidget(_this.tables[0])});
        }

        //console.log(data)
        //_this.events.loader.hide();
        //return;

        $.ajax({
            url: '/indicator/data.do?saveWidget=true&type=grid&id='+ _this.id,
            type: 'POST',
            data: {
                title: title,
                grid: JSON.stringify({
                    groups: _this.groups,
                    order: _this.order,
                    data: data
                })
            },
            success: function(data){
                //сохранили
                alert('Настройки сохранены');
                _this.events.loader.hide();
            },
            error: function(){
                alert('Не удалось сохранить настройки. Перезагрузите страницу и попробуйте еще раз');
                _this.events.loader.hide();
            }
        });
    };

    _this.createGroupsToWidget = function(group_id, groups, groups_mask) {
        //var is_last = !groups.length;
        var new_groups = [];
        var next_group_id = groups.shift();

        _this.objectKeys(group_id, true).forEach(function (filter_id) {
            var group = {
                type: 'group',
                title: _this.filters[group_id].values[filter_id].title
            };

            var new_groups_mask = (groups_mask == '' ? groups_mask : groups_mask + '-') + group_id + '_' + filter_id;

            if(!groups.length && typeof next_group_id == 'undefined') {
                if(_this.groupsToWidget.indexOf(new_groups_mask) > -1) {
                    group.table = {
                        type: 'table',
                        table: _this.prepareTableToWidget(_this.tables[_this.groupsToWidgetIterator])
                    };
                    _this.groupsToWidgetIterator++;
                    new_groups.push(group);
                }
            } else {
                group.groups = _this.createGroupsToWidget(next_group_id, groups.slice(), new_groups_mask );
                if(group.groups.length)
                    new_groups.push(group);
            }
        });

        return new_groups;
    };

    _this.prepareTableToWidget = function(table) {
        var table_data = {
            title: '',
            type: 'table',
            locked_titles: table.header_locked.find('th .k-link').toArray().map(function(title){
                return title.innerText;
            }),
            wrap_titles: [],
            locked_data: [],
            wrap_data: [],

            select_wrap: table.select_wrap.filter(function(field, field_index) {
                return table.hidden_cols.indexOf(field_index) === -1;
            }),
            select_locked: table.select_locked
        };

        //вложенные заголовки
        $.each(table.header_wrap.find('tr'), function(){
            var tr = $(this);

            var arr = tr.find('th:not(.hidden-col)').toArray().map(function(title){
                var $title = $(title);
                var obj = {
                    title:  title.innerText,
                    colspan: $title.attr('colspan')
                };

                if($title.find('.k-link').length)
                    obj.title = $title.find('.k-link').text();

                return obj;
            });

            if(arr.length)
                table_data.wrap_titles.push(arr);
        });

        //получаем контент
        var lines = _this.db(table.where);//.get();
        var order_str = '__id';
        if(_this.order.length) {
            order_str = 'dim' + _this.order.join(' ') + ', __id';
        }
        lines = lines.order(order_str).get();

        lines.forEach(function(line){
            table_data.locked_data.push(
                table.select_locked.map(function(field){
                    return line[field];
                })
            );

            table_data.wrap_data.push(
                table_data.select_wrap.map(function(field){
                    return line[field];
                })
            );
        });

        return table_data;
    };

    _this.createGraphic = function(type) {
        var lines = [],
            limit = 10,
            selected_rows = _this.db({selected: true, hidden_selected: false, hidden: false}).order('table_id').get(),
        //чтобы работало по столбцам - нужно сделать единые выделенные столбцы для всех таблиц
        //флаг, есть выделенные столбцы
            is_selected_cols = false,
            selected_cols = {},
            visible_cols = {}, //видимые столбцы для всех таблиц
            visible_tables = {}, //выдимые столбцы для каждой таблицы
        //заголовки столбцов
            x_titles = [],
            chart = {},
            decode = $('<div/>')
        ;

        //для выделенных данных нужно работать только с теми таблицами, в которых выделены данные
        var tables = _this.tables;
        if(selected_rows.length) {
            //отсеим все таблицы, кроме выделенных
            tables = [];
            var prev_line;
            selected_rows.forEach(function(line, line_index){
                prev_line = typeof selected_rows[line_index - 1] != 'undefined' ? selected_rows[line_index - 1] : false;
                if(prev_line && prev_line.table_id === line.table_id) {
                    //пропускаем
                } else {
                    tables.push(_this.tables[line.table_id]);
                }

            });
        }

        //найдем только выделенные столбцы
        var iterator = 0; //сколько записей уже показано - чтобы отсеять невходящие в набор столбцы
        tables.forEach(function(table, table_index) {
            if(table.selected_cols.length)
                iterator += table.data.length;

            table.selected_cols.forEach(function(col_id){
                if(table.hidden_cols.indexOf(col_id) === -1 && (type == 'map' || (iterator < 10 || table_index == 0))) {
                    selected_cols[col_id] = 1;
                }
            });

            //ищем только видимые столбцы
            table.select_wrap.forEach(function(c, col_id){
                if(table.hidden_cols.indexOf(col_id) === -1) {
                    if(typeof visible_tables[table.id] == 'undefined')
                        visible_tables[table.id] = {};

                    visible_tables[table.id][col_id] = 1;
                    visible_cols[col_id] = 1;
                }
            });
        });
        is_selected_cols = !!Object.keys(selected_cols).length;

        //собираем заголовки столбцов
        _this.top_columns.forEach(function(column) {
            if(x_titles.length == 0) {
                _this.objectKeys(column, true).forEach(function (filter_id) {
                    x_titles.push(_this.filters[column].values[filter_id].title)
                });
            } else {
                var new_x = [];
                x_titles.forEach(function(title){
                    _this.objectKeys(column, true).forEach(function (filter_id) {
                        new_x.push(title + ', ' + _this.filters[column].values[filter_id].title);
                        i++;
                    });
                });
                x_titles = new_x;
            }
        });
        x_titles = x_titles.filter(function(title, title_index){
            //отсеиваем заголовки скрытых столбцов
            if(!!!visible_cols[title_index])
                return false;

            //в случае выделенных - отсеиваем невыделенные заголовки
            if(is_selected_cols && !!!selected_cols[title_index])
                return false;

            return true;
        });
        x_titles = x_titles.map(function(title){
            return decode.html(title).text();
        });

        //выделенные строки
        if(selected_rows.length > 0) {
            lines = selected_rows;
        }
        //для карты все записи, если нет выделенных
        else if(type == 'map') {
            lines = _this.db({hidden_selected: false, hidden: false}).get();
        }
        else {
            //по дефолту 10 видимых строк из текущего набора
            break_for:
                for(var i = 0, tables_length = tables.length, table; i < tables_length; i++) {
                    table = tables[i];
                    for(var j = 0, data_length = table.data.length, line, cur_line; j < data_length; j++) {
                        line = table.data[j];
                        cur_line = _this.db({hidden: false, hidden_selected: false, ___id: line.___id}).get();
                        if(cur_line.length) {
                            cur_line[0].table_id = table.id;
                            lines.push(cur_line[0]);
                            if(lines.length >= limit)
                                break break_for;
                        }
                    }
                }
        }

        //кол-во записей во всех таблицах - для расчета выводить подсказку или нет
        var all_tables_data_count = 0;
        tables.forEach(function(table){
            all_tables_data_count += table.data.length;
        });

        //скрываем подсказку
        if((selected_rows.length) || all_tables_data_count <= 10 || type == 'map')
            $('#map_prompt').hide();
        else
            $('#map_prompt').show();

        var series = [], data, data_is_null, name, table_field;

        switch (type) {
            case 'map':
                mapValues = [];
                unitName = _this.unit;

                //собираем регионы
                var regions = {};
                Object.keys(_this.filters[_this.map_filter].values).forEach(function(value_id){
                    regions[_this.filters[_this.map_filter].values[value_id].title] = _this.filters[_this.map_filter].values[value_id].code
                });

                var points;
                var field_index_i = 0; //итератор - нужен чтобы получить пропущенный заголовок
                _this.line_template_wrap.forEach(function(field_id, field_index){
                    if(!!!visible_cols[field_index] || (is_selected_cols && !!!selected_cols[field_index])) {
                        //если поля вообще нет в наборе или оно не выделено - его не выводим
                        return;
                    }

                    var field_id_in_table;// = _this.tables[line.table_id].select_wrap[field_index];

                    points = {};
                    lines.forEach(function(line){
                        //костыль, проверить на видимые/скрытые поля
                        field_id_in_table = _this.tables[line.table_id].select_wrap[field_index];
                        points[regions[line['dim' + _this.map_filter]]] = line[field_id_in_table].toString().replace(/,/g, '.');
                    });

                    mapValues.push([x_titles[field_index_i], points]);
                    field_index_i++;
                })

                createMap('agrid-graphics-content', true);
                var mapTitle = jQuery('#agrid-graphics-content').find('.agrid-map-title');
                if(mapTitle.length) {
                    _this.chart_title = mapTitle.html();
                }
                else if(_this.chart != null) {
                    _this.chart_title = _this.chart.title.textStr;
                }

                $('#agrid-graphics-content').prepend('<div class="agrid-map-title">'+ _this.chart_title +'</div>');
                _this.chart = null;
                $('#map_colors').show();
                return;
            case 'gist':
                chart.type = 'bar';
                if(type == 'gist')
                    $('#map_prompt').text('* Гистограмма построена на данных из первых 10 строк таблицы. Вы можете выбрать отображаемые данные на гистограмме, если воспользуетесь фильтрами и выделением строк/колонок в таблице.');
            case 'line':
                if(type == 'line')
                    $('#map_prompt').text('* График построен на данных из первых 10 строк таблицы. Вы можете выбрать отображаемые данные на графике, если воспользуетесь фильтрами и выделением строк/колонок в таблице.');
            default :
                $('#map_colors').hide();
                lines.forEach(function(line){
                    data = [], data_is_null = true;
                    _this.line_template_wrap.forEach(function(field, field_index) {
                        if(!!!visible_cols[field_index]) {
                            //если поля вообще нет в наборе - его не выводим
                            return;
                        }

                        //избежание проблем с группировкой, т.к. в гриде шаблон вывода обощенный, а в таблице - текущий для нее
                        table_field = _this.tables[line.table_id].select_wrap[field_index];

                        //если столбец есть в общем наборе столбцов
                        if(!!visible_cols[field_index]) {
                            //var table = _this.tables[line.table_id];

                            //если столбец видим в наборе этой таблицы
                            if(!!visible_tables[line.table_id][field_index]) {
                                //если нет вообще выделенных столбцов - просто выводим данные
                                if(!is_selected_cols) {
                                    data.push(parseFloat(line[table_field].toString().replace(/,/g, '.')) || 0)
                                    data_is_null = false;
                                }
                                //если столбец входит в набор выделенных столбцов
                                else if(!!selected_cols[field_index]) {
                                    if(_this.tables[line.table_id].selected_cols.indexOf(field_index) > -1) {
                                        data.push(parseFloat(line[table_field].toString().replace(/,/g, '.')) || 0)
                                        data_is_null = false;
                                    } else {
                                        data.push(null);
                                    }
                                }
                            } else {
                                //иначе вставляем пропуск
                                data.push(null);
                            }
                        }
                    });

                    if(data.length && !data_is_null) {
                        name = _this.line_template_fixed.map(function (field) {
                            return line[field]
                        }).join(', ');

                        if(typeof line.table_id != 'undefined' && typeof _this.tables[line.table_id].title_to_graphic != 'undefined') {
                            name = _this.tables[line.table_id].title_to_graphic + name;
                        } else if(_this.groups.length) {
                            _this.groups.forEach(function(group_id){
                                name = line['dim' + group_id] + ', ' + name;
                            })
                        }

                        series.push({
                            name: name,
                            data: data
                        });
                    }
                });
        }

        if(jQuery('#agrid-graphics-content').find('.agrid-map-title').length) {
            _this.chart_title = jQuery('#agrid-graphics-content').find('.agrid-map-title').html();
        }
        else if(_this.chart != null) {
            _this.chart_title = _this.chart.title.textStr;
        }

        _this.graphics_content.html('');

        var container = $("<div class='agrid-chart-container' style='min-height: 700px;'>");

        _this.graphics_content.append(container);

        //содерем заголовок из вынесенных фильтров
        var title = [], value;
        if(_this.chart_title == null) {
            Object.keys(_this.filters).forEach(function (filter_id) {
                if (_this.left_columns.indexOf(parseInt(filter_id)) === -1 && _this.top_columns.indexOf(parseInt(filter_id)) === -1 && _this.system_filters.indexOf(parseInt(filter_id)) === -1) {
                    Object.keys(_this.filters[filter_id].values).forEach(function (value_id) {
                        value = _this.filters[filter_id].values[value_id];
                        if (value.checked)
                            title.push(value.title);
                    });
                }
            });
        }

        _this.chart_title = _this.chart_title == null ? '<span style="cursor: pointer" ondblclick="editHighchartsTitle(this); return false;">' + _this.title + (title.length ? ' (' + title.join(', ') + ')' : '') + '</span>' : _this.chart_title;

        var params = {
            title: {
                text: _this.chart_title,
                useHTML: true
                //x: -20 //center
            },
            yAxis: {
                title: {
                    text: _this.unit
                }
            },
            tooltip: {
                valueSuffix: ' ' + _this.unit
            },
            legend: {
                labelFormatter: function() {
                    var words = this.name.split(/[\s]+/);
                    var numWordsPerLine = 10;
                    var str = [];
                    var i = 0;
                    words.forEach(function(word){
                        str.push(word);

                        if(i >= numWordsPerLine) {
                            str.push('<br>');
                            i = 0;
                            return;
                        }
                        i++;
                    });

                    return str.join(' ');
                }
            },
            plotOptions: {
                series: {
                    connectNulls: true
                }
            },
            chart: chart,
            width: '100%',
            height: '100%',
            xAxis: {
                categories: x_titles
            },
            credits: {
                enabled: false
            },
            series: series
        };

        _this.chart_params = $.extend({}, params);

        container.highcharts(params);

        _this.chart = container.highcharts();
    };

    _this.savePreview = function(get_params) {

        var data = 'id=' + _this.id;
        _this.events.loader.show();
        jQuery.each(_this.preview_left_column.find('p'), function() {
            data += '&lineObjectIds=' + jQuery(this).data('field');
        });

        jQuery.each(_this.preview_top_column.find('p'), function() {
            data += '&columnObjectIds=' + jQuery(this).data('field');
        });

        _this.preview_grouping.find('p').each(function(){
            data += '&groupObjectIds=' + $(this).data('field');
        });

        Object.keys(_this.filters).forEach(function(filter_id){
            Object.keys(_this.getCheckedFilters(filter_id)).forEach(function(value_id){
                data += '&selectedFilterIds=' + filter_id + '_' + value_id;
            });
        });

        $.each(_this.preview_filters.find('p'), function(){
            data += '&filterObjectIds=' + $(this).data('field');
        });

        if(get_params === true) {
            return data;
        }

        $.ajax({
            url: '/indicator/data.do?saveSettings=true',
            type: 'POST',
            data: data,
            success: function(data){
                _this.events.preview_block.refresh();
                //сохранили
                alert('Настройки сохранены');
                _this.events.loader.hide();
            },
            error: function(){
                alert('Не удалось сохранить настройки. Перезагрузите страницу и попробуйте еще раз');
                _this.events.loader.hide();
            }
        });
    };

    _this.addToWidget = function(){

        var type, data;

        _this.events.loader.show();

        if(_this.chart == null) {
            type = 'map';

            data = {title: jQuery(_this.chart_title).text(), chart: JSON.stringify([mapValues[$('.selectedYear').closest('.barChartItem').index()]])};
        } else {
            var chart = {};
            type = 'chart';
            if(typeof _this.chart_params.chart.type != 'undefined') {
                chart.type = _this.chart_params.chart.type;
                type = chart.type;
            }

            _this.chart_params.chart = chart;
            _this.chart_params.title.text = jQuery(_this.chart.title.textStr).text();
            data = {title: _this.chart_params.title.text, chart: JSON.stringify(_this.chart_params)};
        }

        $.ajax({
            url: '/indicator/data.do?saveWidget=true&type='+ type+'&id='+grid.id,
            type: 'POST',
            data: data,
            success: function(data){
                //сохранили
                alert('Настройки сохранены');
                _this.events.loader.hide();
            },
            error: function(){
                alert('Не удалось сохранить настройки. Перезагрузите страницу и попробуйте еще раз');
                _this.events.loader.hide();
            }
        });
    };
};

FGrid.prototype.objectKeys = function(filter_id, only_checked) {
    if(typeof only_checked == 'undefined')
        only_checked = false;

    var filter = this.filters[filter_id];

    return Object.keys(filter.values)
        .filter(function(value_id){
            return !!filter.all || !(only_checked && !filter.values[value_id].checked);
        }, this)
        .sort((function(a, b) {
            return filter.values[a].order - filter.values[b].order;
        }).bind(this));
};

FGrid.prototype.showDialogIsNull = function(){
    if(this.checkIsNull()) {
        if(!this.is_default_state)
            this.dialog_data_is_null.modal();
        if(!this.dialog_data_is_null.hasClass('modal-inited')) {
            this.dialog_data_is_null.addClass('modal-inited');
            this.dialog_data_is_null.on('hide.bs.modal', (function(){
//                if(!this.is_default_state)
//                    this.events.action_block.default_state();
                if(this.checkIsNull() && !this.setting_tab_button.hasClass('cont_tit_act')) {
                    this.setting_tab_button.click();
                }
            }).bind(this))
        }
    }
};

FGrid.prototype.checkIsNull = function() {
    return this.tables.every(function(table){
        return table.checkIsNull();
    });
};

FGrid.prototype.console = function(f, p) {
    this.logs.push({func: f, params: p});
    if(this.debug) window.console[f](p);
};
FGrid.prototype.log = function(t) {
    this.console('log', t);
};
FGrid.prototype.time = function(t) {
    this.console('time', t);
};
FGrid.prototype.timeEnd = function(t) {
    this.console('timeEnd', t);
};
FGrid.prototype.group = function(t) {
    this.console('group', t);
};
FGrid.prototype.groupEnd = function(t) {
    this.console('groupEnd', t);
};
FGrid.prototype.info = function(t) {
    this.console('info', t)
};

FGrid.prototype.checkedFiltersLength = function (showModal) {
    var valid = true;
    var _this = this;
    showModal = typeof showModal == 'undefined' ? true : showModal;

    if($('#dialog_filters_is_empty').hasClass('in'))
        return false;

    for(var filterId in this.filters) {
        if(!Object.keys(this.getCheckedFilters(filterId)).length) {
            valid = false;
            break;
        }
    }

    if(!valid) {
        var modal = $('#dialog_filters_is_empty');
        modal.off('hidden.bs.modal').on('hidden.bs.modal', function (e) {
            if(!!_this.lastClickedFilter && (_this.lastClickedFilter.data('field') == filterId || _this.lastClickedFilter.closest('[data-field]').data('field') == filterId)) {
                _this.lastClickedFilter.click();
            } else {
                _this.main_block.find('th.k-header[data-field="' + filterId + '"]:not(.hidden-col):first .k-filter').click();
            }
        });//.modal();

        if(showModal) {
            modal.modal();
        }
    }

    return valid;
};

FGrid.prototype.downloadFile = function(format) {
    var data = this.savePreview(true);

    var title = [];//[_this.title];
    $.each(this.filters_block_content.find('input.inp_checkbox:checked'), function() {
        title.push($(this).parent().text());
    });

    title =  title.join(', ') != '' ? this.title + ' (' + title.join(', ') + ')' : this.title;

    var form = $('<form method="post" action="/indicator/downloadData.do?format='+format+'">');

    form.append('<input type="hidden" name="title" value="'+ title +'">');
    form.append('<input type="hidden" name="struts.token.name" value="'
        + $('#downloadTokenHolder input[name="struts.token.name"]').val() + '">');
    form.append('<input type="hidden" name="token" value="'
        + $('#downloadTokenHolder input[name="token"]').val() + '">');

    form.append(
        data.split('&').map(function(r){
            var tmp = r.split('=');
            return '<input type="hidden" name="'+ tmp[0] +'" value="'+ tmp[1] +'">';
        }).join('')
    ).hide().appendTo('body').submit();

    this.events.loader.hide();
};

function editHighchartsTitle(obj) {
    obj = jQuery(obj);

    var height = obj.height(),
        offset = obj.offset();

    obj.hide();

    var text_block = jQuery('<div class="text_zamena">').css({
        height: height,
        width: 600
    });

    var text_area = jQuery('<textarea rows="4" style="height: auto" class="form-control">'+ obj.html().replace(/<br>/g, '\n') +'</textarea>');

    text_block.append([
        text_area,
        jQuery('<button class="btn blue_btn">Сохранить</button>').click(function(){
            var chartContainer = $('#agrid-graphics-content .agrid-chart-container');
            if(chartContainer.length) {
                chartContainer.highcharts().setTitle({
                    text: '<span style="cursor: pointer" ondblclick="editHighchartsTitle(this); return false;">' + text_area.val().replace(/\n/g, '<br>') + '</span>'
                });
            } else {
                jQuery('#agrid-graphics-content').find('.agrid-map-title').html('<span style="cursor: pointer" ondblclick="editHighchartsTitle(this); return false;">' + text_area.val().replace(/\n/g, '<br>') + '</span>');
            }
            text_block.remove();
            obj.show();
        }),
        jQuery('<button class="btn white_btn mr8">Отменить</button>').click(function(){
            text_block.remove();
            obj.show();
        })
    ]);

    $('#agrid-graphics-content').prepend(text_block);
    //text_block.insertBefore(obj.closest('.highcharts-container'));

    var top_nug = offset.top - $('.text_zamena').offset().top;

    text_block.css({
        top: top_nug,
        left: '50%',
        'margin-left': -300
    });
    text_block.wrap('<div class="pos_rel_all">');
}

// Production steps of ECMA-262, Edition 5, 15.4.4.18
// Reference: http://es5.github.io/#x15.4.4.18
if (!Array.prototype.forEach) {

    Array.prototype.forEach = function(callback, thisArg) {

        var T, k;

        if (this == null) {
            throw new TypeError(' this is null or not defined');
        }

        // 1. Let O be the result of calling ToObject passing the |this| value as the argument.
        var O = Object(this);

        // 2. Let lenValue be the result of calling the Get internal method of O with the argument "length".
        // 3. Let len be ToUint32(lenValue).
        var len = O.length >>> 0;

        // 4. If IsCallable(callback) is false, throw a TypeError exception.
        // See: http://es5.github.com/#x9.11
        if (typeof callback !== "function") {
            throw new TypeError(callback + ' is not a function');
        }

        // 5. If thisArg was supplied, let T be thisArg; else let T be undefined.
        if (arguments.length > 1) {
            T = thisArg;
        }

        // 6. Let k be 0
        k = 0;

        // 7. Repeat, while k < len
        while (k < len) {

            var kValue;

            // a. Let Pk be ToString(k).
            //   This is implicit for LHS operands of the in operator
            // b. Let kPresent be the result of calling the HasProperty internal method of O with argument Pk.
            //   This step can be combined with c
            // c. If kPresent is true, then
            if (k in O) {

                // i. Let kValue be the result of calling the Get internal method of O with argument Pk.
                kValue = O[k];

                // ii. Call the Call internal method of callback with T as the this value and
                // argument list containing kValue, k, and O.
                callback.call(T, kValue, k, O);
            }
            // d. Increase k by 1.
            k++;
        }
        // 8. return undefined
    };
}

// Production steps of ECMA-262, Edition 5, 15.4.4.14
// Reference: http://es5.github.io/#x15.4.4.14
if (!Array.prototype.indexOf) {
    Array.prototype.indexOf = function(searchElement, fromIndex) {

        var k;

        // 1. Let O be the result of calling ToObject passing
        //    the this value as the argument.
        if (this == null) {
            throw new TypeError('"this" is null or not defined');
        }

        var O = Object(this);

        // 2. Let lenValue be the result of calling the Get
        //    internal method of O with the argument "length".
        // 3. Let len be ToUint32(lenValue).
        var len = O.length >>> 0;

        // 4. If len is 0, return -1.
        if (len === 0) {
            return -1;
        }

        // 5. If argument fromIndex was passed let n be
        //    ToInteger(fromIndex); else let n be 0.
        var n = +fromIndex || 0;

        if (Math.abs(n) === Infinity) {
            n = 0;
        }

        // 6. If n >= len, return -1.
        if (n >= len) {
            return -1;
        }

        // 7. If n >= 0, then Let k be n.
        // 8. Else, n<0, Let k be len - abs(n).
        //    If k is less than 0, then let k be 0.
        k = Math.max(n >= 0 ? n : len - Math.abs(n), 0);

        // 9. Repeat, while k < len
        while (k < len) {
            // a. Let Pk be ToString(k).
            //   This is implicit for LHS operands of the in operator
            // b. Let kPresent be the result of calling the
            //    HasProperty internal method of O with argument Pk.
            //   This step can be combined with c
            // c. If kPresent is true, then
            //    i.  Let elementK be the result of calling the Get
            //        internal method of O with the argument ToString(k).
            //   ii.  Let same be the result of applying the
            //        Strict Equality Comparison Algorithm to
            //        searchElement and elementK.
            //  iii.  If same is true, return k.
            if (k in O && O[k] === searchElement) {
                return k;
            }
            k++;
        }
        return -1;
    };
}

if (!Array.prototype.filter) {
    Array.prototype.filter = function(fun/*, thisArg*/) {
        'use strict';

        if (this === void 0 || this === null) {
            throw new TypeError();
        }

        var t = Object(this);
        var len = t.length >>> 0;
        if (typeof fun !== 'function') {
            throw new TypeError();
        }

        var res = [];
        var thisArg = arguments.length >= 2 ? arguments[1] : void 0;
        for (var i = 0; i < len; i++) {
            if (i in t) {
                var val = t[i];

                // NOTE: Technically this should Object.defineProperty at
                //       the next index, as push can be affected by
                //       properties on Object.prototype and Array.prototype.
                //       But that method's new, and collisions should be
                //       rare, so use the more-compatible alternative.
                if (fun.call(thisArg, val, i, t)) {
                    res.push(val);
                }
            }
        }

        return res;
    };
}

if (!Function.prototype.bind) {
    Function.prototype.bind = function(oThis) {
        if (typeof this !== 'function') {
            // closest thing possible to the ECMAScript 5
            // internal IsCallable function
            throw new TypeError('Function.prototype.bind - what is trying to be bound is not callable');
        }

        var aArgs   = Array.prototype.slice.call(arguments, 1),
            fToBind = this,
            fNOP    = function() {},
            fBound  = function() {
                return fToBind.apply(this instanceof fNOP
                        ? this
                        : oThis,
                    aArgs.concat(Array.prototype.slice.call(arguments)));
            };

        if (this.prototype) {
            // native functions don't have a prototype
            fNOP.prototype = this.prototype;
        }
        fBound.prototype = new fNOP();

        return fBound;
    };
}

// Production steps of ECMA-262, Edition 5, 15.4.4.19
// Reference: http://es5.github.io/#x15.4.4.19
if (!Array.prototype.map) {

    Array.prototype.map = function(callback, thisArg) {

        var T, A, k;

        if (this == null) {
            throw new TypeError(' this is null or not defined');
        }

        // 1. Let O be the result of calling ToObject passing the |this|
        //    value as the argument.
        var O = Object(this);

        // 2. Let lenValue be the result of calling the Get internal
        //    method of O with the argument "length".
        // 3. Let len be ToUint32(lenValue).
        var len = O.length >>> 0;

        // 4. If IsCallable(callback) is false, throw a TypeError exception.
        // See: http://es5.github.com/#x9.11
        if (typeof callback !== 'function') {
            throw new TypeError(callback + ' is not a function');
        }

        // 5. If thisArg was supplied, let T be thisArg; else let T be undefined.
        if (arguments.length > 1) {
            T = thisArg;
        }

        // 6. Let A be a new array created as if by the expression new Array(len)
        //    where Array is the standard built-in constructor with that name and
        //    len is the value of len.
        A = new Array(len);

        // 7. Let k be 0
        k = 0;

        // 8. Repeat, while k < len
        while (k < len) {

            var kValue, mappedValue;

            // a. Let Pk be ToString(k).
            //   This is implicit for LHS operands of the in operator
            // b. Let kPresent be the result of calling the HasProperty internal
            //    method of O with argument Pk.
            //   This step can be combined with c
            // c. If kPresent is true, then
            if (k in O) {

                // i. Let kValue be the result of calling the Get internal
                //    method of O with argument Pk.
                kValue = O[k];

                // ii. Let mappedValue be the result of calling the Call internal
                //     method of callback with T as the this value and argument
                //     list containing kValue, k, and O.
                mappedValue = callback.call(T, kValue, k, O);

                // iii. Call the DefineOwnProperty internal method of A with arguments
                // Pk, Property Descriptor
                // { Value: mappedValue,
                //   Writable: true,
                //   Enumerable: true,
                //   Configurable: true },
                // and false.

                // In browsers that support Object.defineProperty, use the following:
                // Object.defineProperty(A, k, {
                //   value: mappedValue,
                //   writable: true,
                //   enumerable: true,
                //   configurable: true
                // });

                // For best browser support, use the following:
                A[k] = mappedValue;
            }
            // d. Increase k by 1.
            k++;
        }

        // 9. return A
        return A;
    };
}

if (!Array.prototype.every) {
    Array.prototype.every = function(callbackfn, thisArg) {
        'use strict';
        var T, k;

        if (this == null) {
            throw new TypeError('this is null or not defined');
        }

        // 1. Let O be the result of calling ToObject passing the this
        //    value as the argument.
        var O = Object(this);

        // 2. Let lenValue be the result of calling the Get internal method
        //    of O with the argument "length".
        // 3. Let len be ToUint32(lenValue).
        var len = O.length >>> 0;

        // 4. If IsCallable(callbackfn) is false, throw a TypeError exception.
        if (typeof callbackfn !== 'function') {
            throw new TypeError();
        }

        // 5. If thisArg was supplied, let T be thisArg; else let T be undefined.
        if (arguments.length > 1) {
            T = thisArg;
        }

        // 6. Let k be 0.
        k = 0;

        // 7. Repeat, while k < len
        while (k < len) {

            var kValue;

            // a. Let Pk be ToString(k).
            //   This is implicit for LHS operands of the in operator
            // b. Let kPresent be the result of calling the HasProperty internal
            //    method of O with argument Pk.
            //   This step can be combined with c
            // c. If kPresent is true, then
            if (k in O) {

                // i. Let kValue be the result of calling the Get internal method
                //    of O with argument Pk.
                kValue = O[k];

                // ii. Let testResult be the result of calling the Call internal method
                //     of callbackfn with T as the this value and argument list
                //     containing kValue, k, and O.
                var testResult = callbackfn.call(T, kValue, k, O);

                // iii. If ToBoolean(testResult) is false, return false.
                if (!testResult) {
                    return false;
                }
            }
            k++;
        }
        return true;
    };
}

/*
 * ******************************************************************************
 *  jquery.mb.components
 *  file: jquery.mb.browser.js
 *
 *  Copyright (c) 2001-2014. Matteo Bicocchi (Pupunzi);
 *  Open lab srl, Firenze - Italy
 *  email: matteo@open-lab.com
 *  site: 	http://pupunzi.com
 *  blog:	http://pupunzi.open-lab.com
 * 	http://open-lab.com
 *
 *  Licences: MIT, GPL
 *  http://www.opensource.org/licenses/mit-license.php
 *  http://www.gnu.org/licenses/gpl.html
 *
 *  last modified: 27/01/14 19.58
 *  *****************************************************************************
 */

/*******************************************************************************
 *
 * jquery.mb.browser
 * Author: pupunzi
 * Creation date: 16/01/13
 *
 ******************************************************************************/
/*Browser detection patch*/

if(!jQuery.browser){

    jQuery.browser = {};
    jQuery.browser.mozilla = false;
    jQuery.browser.webkit = false;
    jQuery.browser.opera = false;
    jQuery.browser.safari = false;
    jQuery.browser.chrome = false;
    jQuery.browser.msie = false;
    jQuery.browser.android = false;
    jQuery.browser.blackberry = false;
    jQuery.browser.ios = false;
    jQuery.browser.operaMobile = false;
    jQuery.browser.windowsMobile = false;
    jQuery.browser.mobile = false;

    var nAgt = navigator.userAgent;
    jQuery.browser.ua = nAgt;

    jQuery.browser.name  = navigator.appName;
    jQuery.browser.fullVersion  = ''+parseFloat(navigator.appVersion);
    jQuery.browser.majorVersion = parseInt(navigator.appVersion,10);
    var nameOffset,verOffset,ix;

// In Opera, the true version is after "Opera" or after "Version"
    if ((verOffset=nAgt.indexOf("Opera"))!=-1) {
        jQuery.browser.opera = true;
        jQuery.browser.name = "Opera";
        jQuery.browser.fullVersion = nAgt.substring(verOffset+6);
        if ((verOffset=nAgt.indexOf("Version"))!=-1)
            jQuery.browser.fullVersion = nAgt.substring(verOffset+8);
    }

// In MSIE < 11, the true version is after "MSIE" in userAgent
    else if ( (verOffset=nAgt.indexOf("MSIE"))!=-1) {
        jQuery.browser.msie = true;
        jQuery.browser.name = "Microsoft Internet Explorer";
        jQuery.browser.fullVersion = nAgt.substring(verOffset+5);
    }

// In TRIDENT (IE11) => 11, the true version is after "rv:" in userAgent
    else if (nAgt.indexOf("Trident")!=-1 ) {
        jQuery.browser.msie = true;
        jQuery.browser.name = "Microsoft Internet Explorer";
        var start = nAgt.indexOf("rv:")+3;
        var end = start+4;
        jQuery.browser.fullVersion = nAgt.substring(start,end);
    }

// In Chrome, the true version is after "Chrome"
    else if ((verOffset=nAgt.indexOf("Chrome"))!=-1) {
        jQuery.browser.webkit = true;
        jQuery.browser.chrome = true;
        jQuery.browser.name = "Chrome";
        jQuery.browser.fullVersion = nAgt.substring(verOffset+7);
    }
// In Safari, the true version is after "Safari" or after "Version"
    else if ((verOffset=nAgt.indexOf("Safari"))!=-1) {
        jQuery.browser.webkit = true;
        jQuery.browser.safari = true;
        jQuery.browser.name = "Safari";
        jQuery.browser.fullVersion = nAgt.substring(verOffset+7);
        if ((verOffset=nAgt.indexOf("Version"))!=-1)
            jQuery.browser.fullVersion = nAgt.substring(verOffset+8);
    }
// In Safari, the true version is after "Safari" or after "Version"
    else if ((verOffset=nAgt.indexOf("AppleWebkit"))!=-1) {
        jQuery.browser.webkit = true;
        jQuery.browser.name = "Safari";
        jQuery.browser.fullVersion = nAgt.substring(verOffset+7);
        if ((verOffset=nAgt.indexOf("Version"))!=-1)
            jQuery.browser.fullVersion = nAgt.substring(verOffset+8);
    }
// In Firefox, the true version is after "Firefox"
    else if ((verOffset=nAgt.indexOf("Firefox"))!=-1) {
        jQuery.browser.mozilla = true;
        jQuery.browser.name = "Firefox";
        jQuery.browser.fullVersion = nAgt.substring(verOffset+8);
    }
// In most other browsers, "name/version" is at the end of userAgent
    else if ( (nameOffset=nAgt.lastIndexOf(' ')+1) < (verOffset=nAgt.lastIndexOf('/')) ){
        jQuery.browser.name = nAgt.substring(nameOffset,verOffset);
        jQuery.browser.fullVersion = nAgt.substring(verOffset+1);
        if (jQuery.browser.name.toLowerCase()==jQuery.browser.name.toUpperCase()) {
            jQuery.browser.name = navigator.appName;
        }
    }

    /*Check all mobile environments*/
    jQuery.browser.android = (/Android/i).test(nAgt);
    jQuery.browser.blackberry = (/BlackBerry/i).test(nAgt);
    jQuery.browser.ios = (/iPhone|iPad|iPod/i).test(nAgt);
    jQuery.browser.operaMobile = (/Opera Mini/i).test(nAgt);
    jQuery.browser.windowsMobile = (/IEMobile/i).test(nAgt);
    jQuery.browser.mobile = jQuery.browser.android || jQuery.browser.blackberry || jQuery.browser.ios || jQuery.browser.windowsMobile || jQuery.browser.operaMobile;


// trim the fullVersion string at semicolon/space if present
    if ((ix=jQuery.browser.fullVersion.indexOf(";"))!=-1)
        jQuery.browser.fullVersion=jQuery.browser.fullVersion.substring(0,ix);
    if ((ix=jQuery.browser.fullVersion.indexOf(" "))!=-1)
        jQuery.browser.fullVersion=jQuery.browser.fullVersion.substring(0,ix);

    jQuery.browser.majorVersion = parseInt(''+jQuery.browser.fullVersion,10);
    if (isNaN(jQuery.browser.majorVersion)) {
        jQuery.browser.fullVersion  = ''+parseFloat(navigator.appVersion);
        jQuery.browser.majorVersion = parseInt(navigator.appVersion,10);
    }
    jQuery.browser.version = jQuery.browser.majorVersion;
}

function checkBrowser()
{
    var valid = false;
    switch (true) {
        case $.browser.chrome && $.browser.version >= 45:
        case $.browser.msie && $.browser.version >= 10:
        case $.browser.mozilla && $.browser.version >= 32:
        case $.browser.opera && $.browser.version >= 24:
        case $.browser.ios && $.browser.version >= 8:
            valid = true;
            break;
    }
    
    return valid;
}