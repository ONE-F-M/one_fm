/*
 *  Project: RV Font Size jQuery Plugin
 *  Description: An easy and flexible jquery plugin to give font size accessibility control.
 *  URL: https://github.com/ramonvictor/rv-jquery-fontsize/
 *  Author: Ramon Victor (https://github.com/ramonvictor/)
 *  License: Licensed under the MIT license:
 *  http://www.opensource.org/licenses/mit-license.php
 *  Any and all use of this script must be accompanied by this copyright/license notice in its present form.
 */

;(function ($, window, document, undefined) {
    "use strict";

    var rvFontsize = "rvFontsize",
        defaults = {
            targetSection: 'body',
            store: false,
            storeIsDefined: !(typeof store === "undefined"),
            variations: 7,
            controllers: {
                append: true,
                appendTo: 'body',
                showResetButton: false,
                template : ''
            }
        };

    function Plugin(element, options) {
        var _self = this;

        _self.element = element;
        _self.options = $.extend({}, defaults, options);

        _self._defaults = defaults;
        _self._name = rvFontsize;

        _self.init();
    }

    Plugin.prototype = {

        init: function() {
            var _self = this,
                fn = function(){
                    _self.defineElements();
                    _self.getDefaultFontSize();
                };

            fn();

            if( _self.options.store === true && !(_self.options.storeIsDefined) ) {
               _self.dependencyWarning();
            }
        },

        dependencyWarning : function(){
            console.warn('When you difine "store: true", store script is required (https://github.com/ramonvictor/rv-jquery-fontsize/blob/master/js/store.min.js)'); 
        },

        bindControlerHandlers: function(){
           
            var _self = this;               
            
            // decrease fn
            _self.$decreaseButton = $('.rvfs-decrease');
            if( _self.$decreaseButton.length > 0){
                
                _self.$decreaseButton.on('click', function(e){
                    e.preventDefault();                    
                    var $el = $(this);

                    if(!$el.hasClass('disabled')){
                        var n = _self.getCurrentVariation();
                        if(n > 1){
                            _self.$target.removeClass('rvfs-' + n);
                            _self.$target.attr('data-rvfs', n-1);
                            if ( _self.options.store === true){
                                _self.storeCurrentSize();
                            }
                            _self.fontsizeChanged();
                        } 
                    }
                });
            }
            
            // increase fn
            _self.$increaseButton = $('.rvfs-increase');
            if( _self.$increaseButton.length > 0){
                _self.$increaseButton.on('click', function(e) { 
                    e.preventDefault();
                    var $el = $(this);

                    if(!$el.hasClass('disabled')){
                        var n = _self.getCurrentVariation();
                        if(n < _self.options.variations){
                            _self.$target.removeClass('rvfs-' + n);
                            _self.$target.attr('data-rvfs', n+1);
                            
                            if ( _self.options.store === true){
                                _self.storeCurrentSize();
                            }
                            _self.fontsizeChanged();
                        }
                    } 
                });
            }
            
            // reset the font size to its default
            _self.$resetButton = $(".rvfs-reset");
            if( _self.$resetButton.length > 0){
                _self.$resetButton.on('click', function(e){
                    e.preventDefault();
                    var $el = $(this);

                    if(!$el.hasClass('disabled')){
                        var n = _self.getCurrentVariation();
                        _self.$target.removeClass('rvfs-' + n);

                        _self.$target.attr('data-rvfs', _self.defaultFontsize);
                        if ( _self.options.store === true){
                            _self.storeCurrentSize();
                        }
                        _self.fontsizeChanged();
                    }
                });
            }

        },

        defineElements: function() {
            var _self = this;
            _self.$target = $( _self.options.targetSection );
          
            if( _self.options.controllers.append !== false ){
                var resetButton = _self.options.controllers.showResetButton ? '<a href="#" class="rvfs-reset btn" title="Default font size">A</a>' : '';
                var template = _self.options.controllers.template,
                    controllersHtml = '';
                _self.$appendTo = $( _self.options.controllers.appendTo );
                
                if( $.trim(template).length > 0 ){
                     controllersHtml = template;
                } else {
                    controllersHtml = '<div class="btn-group">' +
                                            '<a href="#" class="rvfs-decrease btn" title="Decrease font size">A-</a></li>' +
                                            resetButton +
                                            '<a href="#" class="rvfs-increase btn" title="Increase font size">A+</a></li>' +
                                      '</div>';
                }

                _self.$appendTo.html( controllersHtml );

                _self.bindControlerHandlers();
            }
        },
        
        getDefaultFontSize: function () {
            var _self = this,
                v = _self.options.variations;
            _self.defaultFontsize = 0;

            if(v % 2 === 0){
                _self.defaultFontsize = (v/2) + 1;
            } else {
                _self.defaultFontsize = parseInt((v/2) + 1, 10);
            }

            _self.setDefaultFontSize();
        },

        setDefaultFontSize: function(){
            var _self = this;
            
            if( _self.options.store === true && _self.options.storeIsDefined ){
                var currentFs = store.get('rvfs') || _self.defaultFontsize;
                _self.$target.attr("data-rvfs", currentFs );
            } else {
                _self.$target.attr("data-rvfs", _self.defaultFontsize );
            }

            _self.fontsizeChanged();
        },

        storeCurrentSize : function() {
            var _self = this;
            if( _self.options.storeIsDefined ) {
                store.set('rvfs', _self.$target.attr("data-rvfs"));                
            } else {
                _self.dependencyWarning();
            }
        },

        getCurrentVariation : function(){
            return parseInt( this.$target.attr("data-rvfs"), 10 );
        },

        fontsizeChanged : function(){
            var _self = this,
                currentFs = _self.getCurrentVariation();
            _self.$target.addClass( "rvfs-" +  currentFs);

            if(currentFs === _self.defaultFontsize){
                _self.$resetButton.addClass('disabled');
            } else{
                _self.$resetButton.removeClass('disabled');
            }

            if(currentFs === _self.options.variations){
                _self.$increaseButton.addClass('disabled');
            } else {
                _self.$increaseButton.removeClass('disabled');
            }

            if(currentFs === 1){
                _self.$decreaseButton.addClass('disabled');
            } else {
                _self.$decreaseButton.removeClass('disabled');
            }
        }
    };

    
    $.fn[rvFontsize] = function (options) {
        var _self = this;
        return _self.each(function () {
            if (!$.data(_self, "plugin_" + rvFontsize)) {
                $.data(_self, "plugin_" + rvFontsize, new Plugin(_self, options));
            }
        });
    };

    $[rvFontsize] = function() {
        var $window = $(window);
        return $window.rvFontsize.apply($window, Array.prototype.slice.call(arguments, 0));
    };


})(jQuery, window, document);