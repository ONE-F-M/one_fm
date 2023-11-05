/*!
 * artplayer.js v3.5.26
 * Github: https://github.com/zhw2590582/ArtPlayer#readme
 * (c) 2017-2020 Harvey Zack
 * Released under the MIT License.
 */

!(function (t, e) {
  "object" == typeof exports && "undefined" != typeof module
    ? (module.exports = e())
    : "function" == typeof define && define.amd
    ? define(e)
    : ((t =
        "undefined" != typeof globalThis
          ? globalThis
          : t || self).Artplayer = e());
})(this, function () {
  "use strict";
  var t = function (t, e) {
    if (!(t instanceof e))
      throw new TypeError("Cannot call a class as a function");
  };
  function e(t, e) {
    for (var r = 0; r < e.length; r++) {
      var n = e[r];
      (n.enumerable = n.enumerable || !1),
        (n.configurable = !0),
        "value" in n && (n.writable = !0),
        Object.defineProperty(t, n.key, n);
    }
  }
  var r = function (t, r, n) {
    return r && e(t.prototype, r), n && e(t, n), t;
  };
  var n = function (t) {
    if (void 0 === t)
      throw new ReferenceError(
        "this hasn't been initialised - super() hasn't been called"
      );
    return t;
  };
  "undefined" != typeof globalThis
    ? globalThis
    : "undefined" != typeof window
    ? window
    : "undefined" != typeof global
    ? global
    : "undefined" != typeof self && self;
  function o(t, e) {
    return t((e = { exports: {} }), e.exports), e.exports;
  }
  var i = o(function (t) {
    function e(r, n) {
      return (
        (t.exports = e =
          Object.setPrototypeOf ||
          function (t, e) {
            return (t.__proto__ = e), t;
          }),
        e(r, n)
      );
    }
    t.exports = e;
  });
  var a = function (t, e) {
      if ("function" != typeof e && null !== e)
        throw new TypeError(
          "Super expression must either be null or a function"
        );
      (t.prototype = Object.create(e && e.prototype, {
        constructor: { value: t, writable: !0, configurable: !0 },
      })),
        e && i(t, e);
    },
    c = o(function (t) {
      function e(r) {
        return (
          "function" == typeof Symbol && "symbol" == typeof Symbol.iterator
            ? (t.exports = e = function (t) {
                return typeof t;
              })
            : (t.exports = e = function (t) {
                return t &&
                  "function" == typeof Symbol &&
                  t.constructor === Symbol &&
                  t !== Symbol.prototype
                  ? "symbol"
                  : typeof t;
              }),
          e(r)
        );
      }
      t.exports = e;
    });
  var l = function (t, e) {
      return !e || ("object" !== c(e) && "function" != typeof e) ? n(t) : e;
    },
    s = o(function (t) {
      function e(r) {
        return (
          (t.exports = e = Object.setPrototypeOf
            ? Object.getPrototypeOf
            : function (t) {
                return t.__proto__ || Object.getPrototypeOf(t);
              }),
          e(r)
        );
      }
      t.exports = e;
    });
  !(function (t, e) {
    void 0 === e && (e = {});
    var r = e.insertAt;
    if (t && "undefined" != typeof document) {
      var n = document.head || document.getElementsByTagName("head")[0],
        o = document.createElement("style");
      (o.type = "text/css"),
        "top" === r && n.firstChild
          ? n.insertBefore(o, n.firstChild)
          : n.appendChild(o),
        o.styleSheet
          ? (o.styleSheet.cssText = t)
          : o.appendChild(document.createTextNode(t));
    }
  })(
    '.art-undercover{background:#000;position:fixed;top:0;left:0;display:none;height:100%;width:100%;opacity:.9;z-index:10}.art-video-player{display:-webkit-box;display:-ms-flexbox;display:flex;position:relative;margin:0 auto;z-index:20;width:100%;height:489px !important;outline:0;zoom:1;font-family:Roboto,Arial,Helvetica,sans-serif;color:#eee;background-color:#000;text-align:left;direction:ltr;font-size:14px;line-height:1.3;-webkit-user-select:none;-moz-user-select:none;-ms-user-select:none;user-select:none;-webkit-tap-highlight-color:rgba(0,0,0,0);-ms-touch-action:manipulation;touch-action:manipulation;-ms-high-contrast-adjust:none}.art-video-player *{margin:0;padding:0;-webkit-box-sizing:border-box;box-sizing:border-box}.art-video-player ::-webkit-scrollbar{width:5px}.art-video-player ::-webkit-scrollbar-thumb{background-color:#666}.art-video-player ::-webkit-scrollbar-thumb:hover{background-color:#ccc}.art-video-player .art-icon{display:-webkit-inline-box;display:-ms-inline-flexbox;display:inline-flex;-webkit-box-pack:center;-ms-flex-pack:center;justify-content:center;-webkit-box-align:center;-ms-flex-align:center;align-items:center;line-height:1.5}.art-video-player .art-icon svg{fill:#6b7780;}.art-video-player img{max-width:100%;vertical-align:top}@supports ((-webkit-backdrop-filter:initial) or (backdrop-filter:initial)){.art-video-player .art-backdrop-filter{-webkit-backdrop-filter:saturate(180%) blur(20px);backdrop-filter:saturate(180%) blur(20px);background-color:rgba(0,0,0,.7)!important}}.art-video-player .art-video{position:absolute;z-index:10;left:0;top:0;right:0;bottom:0;width:100%;height:100%;background-color:#000;cursor:pointer}.art-video-player .art-subtitle{display:none;position:absolute;z-index:20;bottom:10px;width:100%;padding:0 20px;text-align:center;color:#fff;font-size:20px;pointer-events:none;text-shadow:.5px .5px .5px rgba(0,0,0,.5)}.art-video-player .art-subtitle p{word-break:break-all;height:-webkit-fit-content;height:-moz-fit-content;height:fit-content;margin:5px 0 0;line-height:1.2}.art-video-player .art-bilingual p:nth-child(n+2){-webkit-transform:scale(.6);transform:scale(.6);-webkit-transform-origin:center top;transform-origin:center top}.art-video-player.art-subtitle-show .art-subtitle{display:block}.art-video-player.art-control-show .art-subtitle{bottom:50px}.art-video-player .art-danmuku{z-index:30}.art-video-player .art-danmuku,.art-video-player .art-layers{position:absolute;left:0;top:0;right:0;bottom:0;width:100%;height:100%;overflow:hidden;pointer-events:none}.art-video-player .art-layers{display:none;z-index:40}.art-video-player .art-layers .art-layer{pointer-events:auto}.art-video-player.art-layer-show .art-layers{display:block}.art-video-player .art-mask{display:none;z-index:50;left:0;top:0;right:0;bottom:0;width:100%;height:100%;overflow:hidden;pointer-events:none}.art-video-player .art-mask,.art-video-player .art-mask .art-state{-webkit-box-align:center;-ms-flex-align:center;align-items:center;-webkit-box-pack:center;-ms-flex-pack:center;justify-content:center;position:absolute}.art-video-player .art-mask .art-state{right:auto;left:50%;bottom:auto;top:50%;opacity:1;transform:translateX(-50%) translateY(-50%);}.art-video-player.art-mask-show .art-mask,.art-video-player .art-mask .art-state{display:-webkit-box;display:-ms-flexbox;display:flex}.art-video-player .art-loading{display:none;position:absolute;z-index:70;left:0;top:0;right:0;bottom:0;width:100%;height:100%;-webkit-box-align:center;-ms-flex-align:center;align-items:center;-webkit-box-pack:center;-ms-flex-pack:center;justify-content:center;pointer-events:none}.art-video-player.art-loading-show .art-loading{display:-webkit-box;display:-ms-flexbox;display:flex}.art-video-player .art-bottom{position:absolute;z-index:60;left:0;right:0;bottom:-44px;height:44px;padding:0px 0px 0;overflow:hidden;opacity:0;visibility:hidden;-webkit-transition:all .2s ease-in-out;transition:all .2s ease-in-out;pointer-events:none;background:#fff;}.art-video-player .art-bottom .art-progress{position:relative;pointer-events:auto;background:#889bb3;}.art-video-player .art-bottom .art-progress .art-control-progress{position:relative;display:-webkit-box;display:-ms-flexbox;display:flex;-webkit-box-orient:horizontal;-webkit-box-direction:normal;-ms-flex-direction:row;flex-direction:row;-webkit-box-align:center;-ms-flex-align:center;align-items:center;height:4px;cursor:pointer}.art-video-player .art-bottom .art-progress .art-control-progress .art-control-progress-inner{position:relative;height:50%;width:100%;}.art-video-player .art-bottom .art-progress .art-control-progress .art-control-progress-inner .art-progress-loaded{position:absolute;z-index:10;left:0;top:0;right:0;bottom:0;height:100%;width:0;}.art-video-player .art-bottom .art-progress .art-control-progress .art-control-progress-inner .art-progress-played{position:absolute;z-index:20;left:0;top:0;right:0;bottom:0;height:100%;width:0}.art-video-player .art-bottom .art-progress .art-control-progress .art-control-progress-inner .art-progress-highlight{position:absolute;z-index:30;left:0;top:0;right:0;bottom:0;height:100%;pointer-events:none}.art-video-player .art-bottom .art-progress .art-control-progress .art-control-progress-inner .art-progress-highlight span{display:inline-block;position:absolute;left:0;top:0;width:7px;height:100%;background:#fff;pointer-events:auto}.art-video-player .art-bottom .art-progress .art-control-progress .art-control-progress-inner .art-progress-indicator{display:none;position:absolute;z-index:40;top:-5px;left:-6.5px;width:13px;height:13px;border-radius:50%}.art-video-player .art-bottom .art-progress .art-control-progress .art-control-progress-inner .art-progress-indicator.art-show-indicator{display:block}.art-video-player .art-bottom .art-progress .art-control-progress .art-control-progress-inner .art-progress-tip{display:none;position:absolute;z-index:50;top:-25px;left:0;height:20px;padding:0 5px;line-height:20px;color:#fff;font-size:12px;text-align:center;background:rgba(0,0,0,.7);border-radius:3px;font-weight:700;white-space:nowrap}.art-video-player .art-bottom .art-progress .art-control-progress:hover .art-control-progress-inner{height:100%}.art-video-player .art-bottom .art-progress .art-control-progress:hover .art-control-progress-inner .art-progress-indicator,.art-video-player .art-bottom .art-progress .art-control-progress:hover .art-control-progress-inner .art-progress-tip{display:block}.art-video-player .art-bottom .art-progress .art-control-thumbnails{display:none;position:absolute;bottom:8px;left:0;pointer-events:none;background-color:rgba(0,0,0,.7)}.art-video-player .art-bottom .art-progress .art-control-loop{display:none;position:absolute;width:100%;height:100%;left:0;top:0;right:0;bottom:0;pointer-events:none}.art-video-player .art-bottom .art-progress .art-control-loop .art-loop-point{position:absolute;left:0;top:-2px;width:2px;height:8px;background:hsla(0,0%,100%,.75)}.art-video-player .art-bottom .art-controls{position:relative;pointer-events:auto;-webkit-box-align:center;-ms-flex-align:center;align-items:center;-webkit-box-pack:justify;-ms-flex-pack:justify;justify-content:space-between;height:40px;padding:5px 0}.art-video-player .art-bottom .art-controls,.art-video-player .art-bottom .art-controls .art-controls-left,.art-video-player .art-bottom .art-controls .art-controls-right{display:-webkit-box;display:-ms-flexbox;display:flex}.art-video-player .art-bottom .art-controls .art-control{opacity:.9;font-size:12px;height:36px;min-width:36px;line-height:36px;text-align:center;cursor:pointer;white-space:nowrap;color:#6b7780;}.art-video-player .art-bottom .art-controls .art-control .art-icon{display:-webkit-box;display:-ms-flexbox;display:flex;-webkit-box-align:center;-ms-flex-align:center;align-items:center;-webkit-box-pack:center;-ms-flex-pack:center;justify-content:center;float:left;height:36px;width:36px}.art-video-player .art-bottom .art-controls .art-control:hover{opacity:1}.art-video-player .art-bottom .art-controls .art-control-onlyText{padding:0 10px}.art-video-player .art-bottom .art-controls .art-control-volume .art-volume-panel{position:relative;float:left;width:0;height:100%;-webkit-transition:margin .2s cubic-bezier(.4,0,1,1),width .2s cubic-bezier(.4,0,1,1);transition:margin .2s cubic-bezier(.4,0,1,1),width .2s cubic-bezier(.4,0,1,1);overflow:hidden}.art-video-player .art-bottom .art-controls .art-control-volume .art-volume-panel .art-volume-slider-handle{position:absolute;top:50%;left:0;width:12px;height:12px;border-radius:12px;margin-top:-6px;background:#a1abb3;}.art-video-player .art-bottom .art-controls .art-control-volume .art-volume-panel .art-volume-slider-handle:before{left:-54px;background:#a1abb3;}.art-video-player .art-bottom .art-controls .art-control-volume .art-volume-panel .art-volume-slider-handle:after{left:6px;background:#e3e6e6;}.art-video-player .art-bottom .art-controls .art-control-volume .art-volume-panel .art-volume-slider-handle:after,.art-video-player .art-bottom .art-controls .art-control-volume .art-volume-panel .art-volume-slider-handle:before{content:"";position:absolute;display:block;top:50%;height:3px;margin-top:-2px;width:60px}.art-video-player .art-bottom .art-controls .art-control-volume:hover .art-volume-panel{width:60px}.art-video-player .art-bottom .art-controls .art-control-quality{position:relative;z-index:30}.art-video-player .art-bottom .art-controls .art-control-quality .art-qualitys{display:none;position:absolute;bottom:35px;width:100px;padding:5px 0;text-align:center;color:#fff;background:rgba(0,0,0,.8);border-radius:3px}.art-video-player .art-bottom .art-controls .art-control-quality .art-qualitys .art-quality-item{height:30px;line-height:30px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;text-shadow:0 0 2px rgba(0,0,0,.5)}.art-video-player .art-bottom .art-controls .art-control-quality .art-qualitys .art-quality-item:hover{background-color:hsla(0,0%,100%,.1)}.art-video-player .art-bottom .art-controls .art-control-quality:hover .art-qualitys{display:block}.art-video-player.art-control-show .art-bottom,.art-video-player.art-hover .art-bottom{opacity:1;visibility:visible}.art-video-player.art-destroy .art-progress-indicator,.art-video-player.art-destroy .art-progress-tip,.art-video-player.art-error .art-progress-indicator,.art-video-player.art-error .art-progress-tip{display:none!important}.art-video-player .art-notice{display:none;font-size:14px;position:absolute;z-index:80;left:0;top:0;padding:10px;width:100%;pointer-events:none}.art-video-player .art-notice .art-notice-inner{display:inline-block;padding:5px 10px;color:#fff;background:rgba(0,0,0,.6);border-radius:3px}.art-video-player.art-notice-show .art-notice{display:-webkit-box;display:-ms-flexbox;display:flex}.art-video-player .art-contextmenus{display:none;-webkit-box-orient:vertical;-webkit-box-direction:normal;-ms-flex-direction:column;flex-direction:column;position:absolute;z-index:120;left:0;top:0;min-width:200px;padding:5px 0;background:rgba(0,0,0,.9);border-radius:3px}.art-video-player .art-contextmenus .art-contextmenu{cursor:pointer;font-size:12px;display:block;color:#fff;padding:10px 15px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;text-shadow:0 0 2px rgba(0,0,0,.5);border-bottom:1px solid hsla(0,0%,100%,.1)}.art-video-player .art-contextmenus .art-contextmenu a{color:#fff;text-decoration:none}.art-video-player .art-contextmenus .art-contextmenu span{display:inline-block;padding:0 7px}.art-video-player .art-contextmenus .art-contextmenu span.art-current,.art-video-player .art-contextmenus .art-contextmenu span:hover{color:#00c9ff}.art-video-player .art-contextmenus .art-contextmenu:hover{background-color:hsla(0,0%,100%,.1)}.art-video-player .art-contextmenus .art-contextmenu:last-child{border-bottom:none}.art-video-player.art-contextmenu-show .art-contextmenus,.art-video-player .art-settings{display:-webkit-box;display:-ms-flexbox;display:flex}.art-video-player .art-settings{-webkit-box-align:center;-ms-flex-align:center;align-items:center;-webkit-box-pack:center;-ms-flex-pack:center;justify-content:center;position:absolute;z-index:90;left:0;top:0;height:100%;width:100%;opacity:0;visibility:hidden;pointer-events:none;overflow:hidden}.art-video-player .art-settings .art-setting-inner{position:absolute;top:0;right:-300px;bottom:0;width:300px;height:100%;font-size:12px;background:rgba(0,0,0,.9);-webkit-transition:all .2s ease-in-out;transition:all .2s ease-in-out;overflow:auto}.art-video-player .art-settings .art-setting-inner .art-setting-body{overflow-y:auto;width:100%;height:100%}.art-video-player .art-settings .art-setting-inner .art-setting-body .art-setting{border-bottom:1px solid hsla(0,0%,100%,.1);padding:10px 15px}.art-video-player .art-settings .art-setting-inner .art-setting-body .art-setting .art-setting-header{margin-bottom:5px}.art-video-player .art-settings .art-setting-radio{display:-webkit-box;display:-ms-flexbox;display:flex}.art-video-player .art-settings .art-setting-radio .art-radio-item{-webkit-box-flex:1;-ms-flex:1;flex:1;padding:0 2px}.art-video-player .art-settings .art-setting-radio .art-radio-item button{height:22px;width:100%;border:none;outline:none;color:#fff;background:hsla(0,0%,100%,.2);border-radius:2px}.art-video-player .art-settings .art-setting-radio .art-radio-item.current button,.art-video-player .art-settings .art-setting-radio .art-radio-item button:active{background-color:#00a1d6}.art-video-player .art-settings .art-setting-range input{width:100%;height:3px;outline:none;-webkit-appearance:none;-moz-appearance:none;appearance:none;background-color:hsla(0,0%,100%,.5)}.art-video-player .art-settings .art-setting-checkbox{display:-webkit-box;display:-ms-flexbox;display:flex;-webkit-box-align:center;-ms-flex-align:center;align-items:center}.art-video-player .art-settings .art-setting-checkbox input{height:14px;width:14px;margin-right:5px}.art-video-player .art-settings .art-setting-upload{display:-webkit-box;display:-ms-flexbox;display:flex}.art-video-player .art-settings .art-setting-upload .art-upload-btn{width:80px;height:22px;line-height:22px;border:none;outline:none;color:#fff;background:hsla(0,0%,100%,.2);border-radius:2px;text-align:center}.art-video-player .art-settings .art-setting-upload .art-upload-value{-webkit-box-flex:1;-ms-flex:1;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;height:22px;line-height:22px;padding-left:10px}.art-video-player.art-setting-show .art-settings{opacity:1;visibility:visible;pointer-events:auto}.art-video-player.art-setting-show .art-settings .art-setting-inner{right:0}.art-video-player .art-info{display:none;-webkit-box-orient:vertical;-webkit-box-direction:normal;-ms-flex-direction:column;flex-direction:column;position:absolute;left:10px;top:10px;z-index:100;width:350px;min-height:150px;padding:10px;color:#fff;font-size:12px;font-family:Noto Sans CJK SC DemiLight,Roboto,Segoe UI,Tahoma,Arial,Helvetica,sans-serif;-webkit-font-smoothing:antialiased;background:rgba(0,0,0,.9)}.art-video-player .art-info .art-info-item{display:-webkit-box;display:-ms-flexbox;display:flex;margin-bottom:5px}.art-video-player .art-info .art-info-item .art-info-title{width:100px;text-align:right}.art-video-player .art-info .art-info-item .art-info-content{-webkit-box-flex:1;-ms-flex:1;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding-left:5px}.art-video-player .art-info .art-info-close{position:absolute;top:5px;right:5px;cursor:pointer}.art-video-player.art-info-show .art-info{display:-webkit-box;display:-ms-flexbox;display:flex}.art-video-player.art-hide-cursor *{cursor:none!important}.art-video-player[data-aspect-ratio] video{-webkit-box-sizing:content-box;box-sizing:content-box;-o-object-fit:fill;object-fit:fill}.art-video-player.art-fullscreen-web{position:fixed;z-index:9999;width:100%!important;height:100%!important;left:0;top:0;right:0;bottom:0}.art-fullscreen-rotate{position:fixed;z-index:9999;width:100%;height:100%;left:0;top:0;right:0;bottom:0;background:#000}.art-video-player .art-mini-header{display:none;position:absolute;z-index:110;left:0;top:0;right:0;height:35px;line-height:35px;color:#fff;background:rgba(0,0,0,.5);-webkit-box-align:center;-ms-flex-align:center;align-items:center;-webkit-box-pack:justify;-ms-flex-pack:justify;justify-content:space-between;opacity:0;visibility:hidden;-webkit-transition:all .2s ease-in-out;transition:all .2s ease-in-out}.art-video-player .art-mini-header .art-mini-title{-webkit-box-flex:1;-ms-flex:1;flex:1;padding:0 10px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;cursor:move}.art-video-player .art-mini-header .art-mini-close{width:35px;text-align:center;font-size:22px;cursor:pointer}.art-video-player.art-is-dragging{opacity:.7}.art-video-player.art-mini{position:fixed;z-index:9999;width:400px;height:225px;-webkit-box-shadow:0 2px 5px 0 rgba(0,0,0,.16),0 3px 6px 0 rgba(0,0,0,.2);box-shadow:0 2px 5px 0 rgba(0,0,0,.16),0 3px 6px 0 rgba(0,0,0,.2)}.art-video-player.art-mini .art-mini-header{display:-webkit-box;display:-ms-flexbox;display:flex;-webkit-user-select:none;-moz-user-select:none;-ms-user-select:none;user-select:none}.art-video-player.art-mini.art-hover .art-mini-header{opacity:1;visibility:visible}.art-video-player.art-mini .art-mask .art-state{position:static}.art-video-player.art-mini .art-bottom,.art-video-player.art-mini .art-contextmenu,.art-video-player.art-mini .art-danmu,.art-video-player.art-mini .art-info,.art-video-player.art-mini .art-layers,.art-video-player.art-mini .art-notice,.art-video-player.art-mini .art-setting,.art-video-player.art-mini .art-subtitle{display:none!important}.art-auto-size{display:-webkit-box;display:-ms-flexbox;display:flex;-webkit-box-align:center;-ms-flex-align:center;align-items:center;-webkit-box-pack:center;-ms-flex-pack:center;justify-content:center}.art-video-player[data-flip=horizontal] .art-video{-webkit-transform:scaleX(-1);transform:scaleX(-1)}.art-video-player[data-flip=vertical] .art-video{-webkit-transform:scaleY(-1);transform:scaleY(-1)}.art-video-player .art-control-selector{position:relative}.art-video-player .art-control-selector .art-selector-list{display:none;position:absolute;bottom:35px;width:100px;padding:5px 0;text-align:center;color:#fff;background:rgba(0,0,0,.8);border-radius:3px}.art-video-player .art-control-selector .art-selector-list .art-selector-item{height:30px;line-height:30px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;text-shadow:0 0 2px rgba(0,0,0,.5)}.art-video-player .art-control-selector .art-selector-list .art-selector-item:hover{background-color:hsla(0,0%,100%,.1)}.art-video-player .art-control-selector:hover .art-selector-list{display:block}:root{--balloon-color:rgba(16,16,16,0.95);--balloon-font-size:12px;--balloon-move:4px}button[aria-label][data-balloon-pos]{overflow:visible}[aria-label][data-balloon-pos]{position:relative;cursor:pointer}[aria-label][data-balloon-pos]:after{text-indent:0;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Oxygen,Ubuntu,Cantarell,Open Sans,Helvetica Neue,sans-serif;font-weight:400;font-style:normal;text-shadow:none;font-size:var(--balloon-font-size);background:var(--balloon-color);border-radius:2px;color:#fff;content:attr(aria-label);padding:.5em 1em;white-space:nowrap;line-height:1.2}[aria-label][data-balloon-pos]:after,[aria-label][data-balloon-pos]:before{opacity:0;pointer-events:none;-webkit-transition:all .18s ease-out .18s;transition:all .18s ease-out .18s;position:absolute;z-index:10}[aria-label][data-balloon-pos]:before{width:0;height:0;border:5px solid transparent;border-top:5px solid var(--balloon-color);content:""}[aria-label][data-balloon-pos]:hover:after,[aria-label][data-balloon-pos]:hover:before{opacity:1;pointer-events:none}[aria-label][data-balloon-pos][data-balloon-pos=up]:after{margin-bottom:10px}[aria-label][data-balloon-pos][data-balloon-pos=up]:after,[aria-label][data-balloon-pos][data-balloon-pos=up]:before{bottom:100%;left:50%;-webkit-transform:translate(-50%,var(--balloon-move));transform:translate(-50%,var(--balloon-move));-webkit-transform-origin:top;transform-origin:top}[aria-label][data-balloon-pos][data-balloon-pos=up]:hover:after,[aria-label][data-balloon-pos][data-balloon-pos=up]:hover:before{-webkit-transform:translate(-50%);transform:translate(-50%)}'
  );
  var u = o(function (t, e) {
      t.exports = (function () {
        function t(e) {
          return (t =
            "function" == typeof Symbol && "symbol" == typeof Symbol.iterator
              ? function (t) {
                  return typeof t;
                }
              : function (t) {
                  return t &&
                    "function" == typeof Symbol &&
                    t.constructor === Symbol &&
                    t !== Symbol.prototype
                    ? "symbol"
                    : typeof t;
                })(e);
        }
        var e = Object.prototype.toString,
          r = function (r) {
            if (void 0 === r) return "undefined";
            if (null === r) return "null";
            var o = t(r);
            if ("boolean" === o) return "boolean";
            if ("string" === o) return "string";
            if ("number" === o) return "number";
            if ("symbol" === o) return "symbol";
            if ("function" === o)
              return (function (t) {
                return "GeneratorFunction" === n(t);
              })(r)
                ? "generatorfunction"
                : "function";
            if (
              (function (t) {
                return Array.isArray ? Array.isArray(t) : t instanceof Array;
              })(r)
            )
              return "array";
            if (
              (function (t) {
                return (
                  !(
                    !t.constructor ||
                    "function" != typeof t.constructor.isBuffer
                  ) && t.constructor.isBuffer(t)
                );
              })(r)
            )
              return "buffer";
            if (
              (function (t) {
                try {
                  if (
                    "number" == typeof t.length &&
                    "function" == typeof t.callee
                  )
                    return !0;
                } catch (t) {
                  if (-1 !== t.message.indexOf("callee")) return !0;
                }
                return !1;
              })(r)
            )
              return "arguments";
            if (
              (function (t) {
                return (
                  t instanceof Date ||
                  ("function" == typeof t.toDateString &&
                    "function" == typeof t.getDate &&
                    "function" == typeof t.setDate)
                );
              })(r)
            )
              return "date";
            if (
              (function (t) {
                return (
                  t instanceof Error ||
                  ("string" == typeof t.message &&
                    t.constructor &&
                    "number" == typeof t.constructor.stackTraceLimit)
                );
              })(r)
            )
              return "error";
            if (
              (function (t) {
                return (
                  t instanceof RegExp ||
                  ("string" == typeof t.flags &&
                    "boolean" == typeof t.ignoreCase &&
                    "boolean" == typeof t.multiline &&
                    "boolean" == typeof t.global)
                );
              })(r)
            )
              return "regexp";
            switch (n(r)) {
              case "Symbol":
                return "symbol";
              case "Promise":
                return "promise";
              case "WeakMap":
                return "weakmap";
              case "WeakSet":
                return "weakset";
              case "Map":
                return "map";
              case "Set":
                return "set";
              case "Int8Array":
                return "int8array";
              case "Uint8Array":
                return "uint8array";
              case "Uint8ClampedArray":
                return "uint8clampedarray";
              case "Int16Array":
                return "int16array";
              case "Uint16Array":
                return "uint16array";
              case "Int32Array":
                return "int32array";
              case "Uint32Array":
                return "uint32array";
              case "Float32Array":
                return "float32array";
              case "Float64Array":
                return "float64array";
            }
            if (
              (function (t) {
                return (
                  "function" == typeof t.throw &&
                  "function" == typeof t.return &&
                  "function" == typeof t.next
                );
              })(r)
            )
              return "generator";
            switch ((o = e.call(r))) {
              case "[object Object]":
                return "object";
              case "[object Map Iterator]":
                return "mapiterator";
              case "[object Set Iterator]":
                return "setiterator";
              case "[object String Iterator]":
                return "stringiterator";
              case "[object Array Iterator]":
                return "arrayiterator";
            }
            return o.slice(8, -1).toLowerCase().replace(/\s/g, "");
          };
        function n(t) {
          return t.constructor ? t.constructor.name : null;
        }
        function o(t, e) {
          var n =
            2 < arguments.length && void 0 !== arguments[2]
              ? arguments[2]
              : ["option"];
          return (
            i(t, e, n),
            a(t, e, n),
            (function (t, e, n) {
              var c = r(e),
                l = r(t);
              if ("object" === c) {
                if ("object" !== l)
                  throw new Error(
                    "[Type Error]: '"
                      .concat(n.join("."), "' require 'object' type, but got '")
                      .concat(l, "'")
                  );
                Object.keys(e).forEach(function (r) {
                  var c = t[r],
                    l = e[r],
                    s = n.slice();
                  s.push(r), i(c, l, s), a(c, l, s), o(c, l, s);
                });
              }
              if ("array" === c) {
                if ("array" !== l)
                  throw new Error(
                    "[Type Error]: '"
                      .concat(n.join("."), "' require 'array' type, but got '")
                      .concat(l, "'")
                  );
                t.forEach(function (r, c) {
                  var l = t[c],
                    s = e[c] || e[0],
                    u = n.slice();
                  u.push(c), i(l, s, u), a(l, s, u), o(l, s, u);
                });
              }
            })(t, e, n),
            t
          );
        }
        function i(t, e, n) {
          if ("string" === r(e)) {
            var o = r(t);
            if (
              ("?" === e[0] && (e = e.slice(1) + "|undefined"),
              !(-1 < e.indexOf("|")
                ? e
                    .split("|")
                    .map(function (t) {
                      return t.toLowerCase().trim();
                    })
                    .filter(Boolean)
                    .some(function (t) {
                      return o === t;
                    })
                : e.toLowerCase().trim() === o))
            )
              throw new Error(
                "[Type Error]: '"
                  .concat(n.join("."), "' require '")
                  .concat(e, "' type, but got '")
                  .concat(o, "'")
              );
          }
        }
        function a(t, e, n) {
          if ("function" === r(e)) {
            var o = e(t, r(t), n);
            if (!0 !== o) {
              var i = r(o);
              throw "string" === i
                ? new Error(o)
                : "error" === i
                ? o
                : new Error(
                    "[Validator Error]: The scheme for '"
                      .concat(
                        n.join("."),
                        "' validator require return true, but got '"
                      )
                      .concat(o, "'")
                  );
            }
          }
        }
        return (o.kindOf = r), o;
      })();
    }),
    p = (function () {
      function e() {
        t(this, e);
      }
      return (
        r(e, [
          {
            key: "on",
            value: function (t, e, r) {
              var n = this.e || (this.e = {});
              return (n[t] || (n[t] = [])).push({ fn: e, ctx: r }), this;
            },
          },
          {
            key: "once",
            value: function (t, e, r) {
              var n = this;
              function o() {
                n.off(t, o);
                for (
                  var i = arguments.length, a = new Array(i), c = 0;
                  c < i;
                  c++
                )
                  a[c] = arguments[c];
                e.apply(r, a);
              }
              return (o._ = e), this.on(t, o, r);
            },
          },
          {
            key: "emit",
            value: function (t) {
              for (
                var e = ((this.e || (this.e = {}))[t] || []).slice(),
                  r = arguments.length,
                  n = new Array(r > 1 ? r - 1 : 0),
                  o = 1;
                o < r;
                o++
              )
                n[o - 1] = arguments[o];
              for (var i = 0; i < e.length; i += 1) e[i].fn.apply(e[i].ctx, n);
              return this;
            },
          },
          {
            key: "off",
            value: function (t, e) {
              var r = this.e || (this.e = {}),
                n = r[t],
                o = [];
              if (n && e)
                for (var i = 0, a = n.length; i < a; i += 1)
                  n[i].fn !== e && n[i].fn._ !== e && o.push(n[i]);
              return o.length ? (r[t] = o) : delete r[t], this;
            },
          },
        ]),
        e
      );
    })(),
    f = window.navigator.userAgent,
    d = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
      f
    ),
    h = /^((?!chrome|android).)*safari/i.test(f),
    y = /MicroMessenger/i.test(f);
  function b(t) {
    var e =
      arguments.length > 1 && void 0 !== arguments[1] ? arguments[1] : document;
    return e.querySelector(t);
  }
  function v(t) {
    var e =
      arguments.length > 1 && void 0 !== arguments[1] ? arguments[1] : document;
    return Array.from(e.querySelectorAll(t));
  }
  function g(t, e) {
    return t.classList.add(e);
  }
  function m(t, e) {
    return t.classList.remove(e);
  }
  function w(t, e) {
    return t.classList.contains(e);
  }
  function x(t, e) {
    return (
      e instanceof Element
        ? t.appendChild(e)
        : t.insertAdjacentHTML("beforeend", String(e)),
      t.lastElementChild || t.lastChild
    );
  }
  function O(t, e, r) {
    return (t.style[e] = r), t;
  }
  function k(t, e) {
    return (
      Object.keys(e).forEach(function (r) {
        O(t, r, e[r]);
      }),
      t
    );
  }
  function j(t, e) {
    var r = !(arguments.length > 2 && void 0 !== arguments[2]) || arguments[2],
      n = window.getComputedStyle(t, null).getPropertyValue(e);
    return r ? parseFloat(n) : n;
  }
  function P(t) {
    return Array.from(t.parentElement.children).filter(function (e) {
      return e !== t;
    });
  }
  function S(t, e) {
    P(t).forEach(function (t) {
      return m(t, e);
    }),
      g(t, e);
  }
  function R(t, e) {
    var r =
      arguments.length > 2 && void 0 !== arguments[2] ? arguments[2] : "up";
    d ||
      (t.setAttribute("aria-label", e), t.setAttribute("data-balloon-pos", r));
  }
  function E(t) {
    var e = t.getBoundingClientRect(),
      r = window.innerHeight || document.documentElement.clientHeight,
      n = window.innerWidth || document.documentElement.clientWidth,
      o = e.top <= r && e.top + e.height >= 0,
      i = e.left <= n && e.left + e.width >= 0;
    return o && i;
  }
  function D(t, e) {
    return t.composedPath && t.composedPath().indexOf(e) > -1;
  }
  var $ = function (t) {
    return -1 !== Function.toString.call(t).indexOf("[native code]");
  };
  var T = function () {
      if ("undefined" == typeof Reflect || !Reflect.construct) return !1;
      if (Reflect.construct.sham) return !1;
      if ("function" == typeof Proxy) return !0;
      try {
        return (
          Date.prototype.toString.call(
            Reflect.construct(Date, [], function () {})
          ),
          !0
        );
      } catch (t) {
        return !1;
      }
    },
    z = o(function (t) {
      function e(r, n, o) {
        return (
          T()
            ? (t.exports = e = Reflect.construct)
            : (t.exports = e = function (t, e, r) {
                var n = [null];
                n.push.apply(n, e);
                var o = new (Function.bind.apply(t, n))();
                return r && i(o, r.prototype), o;
              }),
          e.apply(null, arguments)
        );
      }
      t.exports = e;
    });
  function A(t) {
    var e = (function () {
      if ("undefined" == typeof Reflect || !Reflect.construct) return !1;
      if (Reflect.construct.sham) return !1;
      if ("function" == typeof Proxy) return !0;
      try {
        return (
          Date.prototype.toString.call(
            Reflect.construct(Date, [], function () {})
          ),
          !0
        );
      } catch (t) {
        return !1;
      }
    })();
    return function () {
      var r,
        n = s(t);
      if (e) {
        var o = s(this).constructor;
        r = Reflect.construct(n, arguments, o);
      } else r = n.apply(this, arguments);
      return l(this, r);
    };
  }
  var C = (function (e) {
    a(o, e);
    var r = A(o);
    function o(e, i) {
      var a;
      return (
        t(this, o),
        (a = r.call(this, e)),
        "function" == typeof Error.captureStackTrace &&
          Error.captureStackTrace(n(a), i || a.constructor),
        (a.name = "ArtPlayerError"),
        a
      );
    }
    return o;
  })(
    o(function (t) {
      function e(r) {
        var n = "function" == typeof Map ? new Map() : void 0;
        return (
          (t.exports = e = function (t) {
            if (null === t || !$(t)) return t;
            if ("function" != typeof t)
              throw new TypeError(
                "Super expression must either be null or a function"
              );
            if (void 0 !== n) {
              if (n.has(t)) return n.get(t);
              n.set(t, e);
            }
            function e() {
              return z(t, arguments, s(this).constructor);
            }
            return (
              (e.prototype = Object.create(t.prototype, {
                constructor: {
                  value: e,
                  enumerable: !1,
                  writable: !0,
                  configurable: !0,
                },
              })),
              i(e, t)
            );
          }),
          e(r)
        );
      }
      t.exports = e;
    })(Error)
  );
  function L(t, e) {
    if (!t) throw new C(e);
    return t;
  }
  function M(t) {
    return "WEBVTT \r\n\r\n".concat(
      t
        .replace(/{[\s\S]*?}/g, "")
        .replace(/\{\\([ibu])\}/g, "</$1>")
        .replace(/\{\\([ibu])1\}/g, "<$1>")
        .replace(/\{([ibu])\}/g, "<$1>")
        .replace(/\{\/([ibu])\}/g, "</$1>")
        .replace(/(\d\d:\d\d:\d\d),(\d\d\d)/g, "$1.$2")
        .concat("\r\n\r\n")
    );
  }
  function q(t) {
    return URL.createObjectURL(new Blob([t], { type: "text/vtt" }));
  }
  function F(t) {
    var e = new RegExp(
      "Dialogue:\\s\\d,(\\d+:\\d\\d:\\d\\d.\\d\\d),(\\d+:\\d\\d:\\d\\d.\\d\\d),([^,]*),([^,]*),(?:[^,]*,){4}([\\s\\S]*)$",
      "i"
    );
    function r() {
      var t =
        arguments.length > 0 && void 0 !== arguments[0] ? arguments[0] : "";
      return t
        .split(/[:.]/)
        .map(function (t, e, r) {
          if (e === r.length - 1) {
            if (1 === t.length) return ".".concat(t, "00");
            if (2 === t.length) return ".".concat(t, "0");
          } else if (1 === t.length) return (0 === e ? "0" : ":0") + t;
          return 0 === e
            ? t
            : e === r.length - 1
            ? ".".concat(t)
            : ":".concat(t);
        })
        .join("");
    }
    return "WEBVTT\n\n".concat(
      t
        .split(/\r?\n/)
        .map(function (t) {
          var n = t.match(e);
          return n
            ? {
                start: r(n[1].trim()),
                end: r(n[2].trim()),
                text: n[5]
                  .replace(/{[\s\S]*?}/g, "")
                  .replace(/(\\N)/g, "\n")
                  .trim()
                  .split(/\r?\n/)
                  .map(function (t) {
                    return t.trim();
                  })
                  .join("\n"),
              }
            : null;
        })
        .filter(function (t) {
          return t;
        })
        .map(function (t, e) {
          return t
            ? ""
                .concat(e + 1, "\n")
                .concat(t.start, " --\x3e ")
                .concat(t.end, "\n")
                .concat(t.text)
            : "";
        })
        .filter(function (t) {
          return t.trim();
        })
        .join("\n\n")
    );
  }
  function H(t) {
    return t.includes("?")
      ? H(t.split("?")[0])
      : t.includes("#")
      ? H(t.split("#")[0])
      : t.trim().toLowerCase().split(".").pop();
  }
  function W(t, e) {
    var r = document.createElement("a");
    (r.style.display = "none"),
      (r.href = t),
      (r.download = e),
      document.body.appendChild(r),
      r.click(),
      document.body.removeChild(r);
  }
  var I = function (t, e) {
    (null == e || e > t.length) && (e = t.length);
    for (var r = 0, n = new Array(e); r < e; r++) n[r] = t[r];
    return n;
  };
  var V = function (t) {
    if (Array.isArray(t)) return I(t);
  };
  var B = function (t) {
    if ("undefined" != typeof Symbol && Symbol.iterator in Object(t))
      return Array.from(t);
  };
  var N = function (t, e) {
    if (t) {
      if ("string" == typeof t) return I(t, e);
      var r = Object.prototype.toString.call(t).slice(8, -1);
      return (
        "Object" === r && t.constructor && (r = t.constructor.name),
        "Map" === r || "Set" === r
          ? Array.from(t)
          : "Arguments" === r ||
            /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(r)
          ? I(t, e)
          : void 0
      );
    }
  };
  var U = function () {
    throw new TypeError(
      "Invalid attempt to spread non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method."
    );
  };
  var _ = function (t) {
      return V(t) || B(t) || N(t) || U();
    },
    X = Object.defineProperty,
    Y = Object.prototype.hasOwnProperty;
  function Z(t, e) {
    return Y.call(t, e);
  }
  function J(t) {
    for (
      var e = arguments.length, r = new Array(e > 1 ? e - 1 : 0), n = 1;
      n < e;
      n++
    )
      r[n - 1] = arguments[n];
    return r.reduce(function (t, e) {
      return (
        Object.getOwnPropertyNames(e).forEach(function (r) {
          L(!Z(t, r), "Target attribute name is duplicated: ".concat(r)),
            X(t, r, Object.getOwnPropertyDescriptor(e, r));
        }),
        t
      );
    }, t);
  }
  function Q() {
    for (
      var t = function (t) {
          return t && "object" === c(t) && !Array.isArray(t);
        },
        e = arguments.length,
        r = new Array(e),
        n = 0;
      n < e;
      n++
    )
      r[n] = arguments[n];
    return r.reduce(function (e, r) {
      return (
        Object.keys(r).forEach(function (n) {
          var o = e[n],
            i = r[n];
          Array.isArray(o) && Array.isArray(i)
            ? (e[n] = o.concat.apply(o, _(i)))
            : !t(o) || !t(i) || i instanceof Element
            ? (e[n] = i)
            : (e[n] = Q(o, i));
        }),
        e
      );
    }, {});
  }
  function G() {
    var t = arguments.length > 0 && void 0 !== arguments[0] ? arguments[0] : 0;
    return new Promise(function (e) {
      return setTimeout(e, t);
    });
  }
  function K(t, e, r) {
    var n;
    function o() {
      for (var o = arguments.length, i = new Array(o), a = 0; a < o; a++)
        i[a] = arguments[a];
      var c = function () {
        (n = null), t.apply(r, i);
      };
      clearTimeout(n), (n = setTimeout(c, e));
    }
    return (
      (o.clearTimeout = function () {
        clearTimeout(n);
      }),
      o
    );
  }
  function tt(t, e) {
    var r,
      n,
      o = !1;
    return function i() {
      for (var a = arguments.length, c = new Array(a), l = 0; l < a; l++)
        c[l] = arguments[l];
      if (o) return (r = c), void (n = this);
      (o = !0),
        t.apply(this, c),
        setTimeout(function () {
          (o = !1), r && (i.apply(n, r), (r = null), (n = null));
        }, e);
    };
  }
  function et(t, e, r) {
    return Math.max(Math.min(t, Math.max(e, r)), Math.min(e, r));
  }
  function rt(t) {
    var e = Math.floor(t / 3600),
      r = Math.floor((t - 3600 * e) / 60),
      n = Math.floor(t - 3600 * e - 60 * r);
    return (e > 0 ? [e, r, n] : [r, n])
      .map(function (t) {
        return t < 10 ? "0".concat(t) : String(t);
      })
      .join(":");
  }
  function nt(t) {
    return t.replace(/[&<>'"]/g, function (t) {
      return (
        { "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[
          t
        ] || t
      );
    });
  }
  var ot = Object.freeze({
    __proto__: null,
    query: b,
    queryAll: v,
    addClass: g,
    removeClass: m,
    hasClass: w,
    append: x,
    remove: function (t) {
      return t.parentNode.removeChild(t);
    },
    setStyle: O,
    setStyles: k,
    getStyle: j,
    sublings: P,
    inverseClass: S,
    tooltip: R,
    isInViewport: E,
    includeFromEvent: D,
    ArtPlayerError: C,
    errorHandle: L,
    srtToVtt: M,
    vttToBlob: q,
    assToVtt: F,
    getExt: H,
    download: W,
    def: X,
    has: Z,
    proxyPropertys: J,
    mergeDeep: Q,
    sleep: G,
    debounce: K,
    throttle: tt,
    clamp: et,
    secondToTime: rt,
    escape: nt,
    userAgent: f,
    isMobile: d,
    isSafari: h,
    isWechat: y,
  });
  var it = function (t, e, r) {
    return (
      e in t
        ? Object.defineProperty(t, e, {
            value: r,
            enumerable: !0,
            configurable: !0,
            writable: !0,
          })
        : (t[e] = r),
      t
    );
  };
  function at(t, e) {
    var r = Object.keys(t);
    if (Object.getOwnPropertySymbols) {
      var n = Object.getOwnPropertySymbols(t);
      e &&
        (n = n.filter(function (e) {
          return Object.getOwnPropertyDescriptor(t, e).enumerable;
        })),
        r.push.apply(r, n);
    }
    return r;
  }
  function ct(t) {
    for (var e = 1; e < arguments.length; e++) {
      var r = null != arguments[e] ? arguments[e] : {};
      e % 2
        ? at(Object(r), !0).forEach(function (e) {
            it(t, e, r[e]);
          })
        : Object.getOwnPropertyDescriptors
        ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(r))
        : at(Object(r)).forEach(function (e) {
            Object.defineProperty(t, e, Object.getOwnPropertyDescriptor(r, e));
          });
    }
    return t;
  }
  var lt = "boolean",
    st = "string",
    ut = "number",
    pt = "object",
    ft = "function";
  function dt(t, e, r) {
    return L(
      e === st || t instanceof Element,
      "".concat(r.join("."), " require '").concat(st, "' or 'Element' type")
    );
  }
  var ht = {
      html: dt,
      disable: "?".concat(lt),
      name: "?".concat(st),
      index: "?".concat(ut),
      style: "?".concat(pt),
      click: "?".concat(ft),
      mounted: "?".concat(ft),
      tooltip: "?".concat(st),
      selector: "?".concat("array"),
      onSelect: "?".concat(ft),
    },
    yt = {
      container: dt,
      url: st,
      poster: st,
      title: st,
      theme: st,
      lang: st,
      volume: ut,
      isLive: lt,
      muted: lt,
      autoplay: lt,
      autoSize: lt,
      autoMini: lt,
      loop: lt,
      flip: lt,
      rotate: lt,
      playbackRate: lt,
      aspectRatio: lt,
      screenshot: lt,
      setting: lt,
      hotkey: lt,
      pip: lt,
      mutex: lt,
      light: lt,
      backdrop: lt,
      fullscreen: lt,
      fullscreenWeb: lt,
      subtitleOffset: lt,
      miniProgressBar: lt,
      localVideo: lt,
      localSubtitle: lt,
      networkMonitor: lt,
      plugins: [ft],
      whitelist: ["".concat(st, "|").concat(ft, "|").concat("regexp")],
      layers: [ht],
      contextmenu: [ht],
      controls: [
        ct(
          ct({}, ht),
          {},
          {
            position: function (t, e, r) {
              var n = ["top", "left", "right"];
              return L(
                n.includes(t),
                ""
                  .concat(r.join("."), " only accept ")
                  .concat(n.toString(), " as parameters")
              );
            },
          }
        ),
      ],
      quality: [{ default: "?".concat(lt), name: st, url: st }],
      highlight: [{ time: ut, text: st }],
      thumbnails: { url: st, number: ut, width: ut, height: ut, column: ut },
      subtitle: { url: st, style: pt, encoding: st, bilingual: lt },
      moreVideoAttr: pt,
      icons: pt,
      customType: pt,
    },
    bt = {
      propertys: [
        "audioTracks",
        "autoplay",
        "buffered",
        "controller",
        "controls",
        "crossOrigin",
        "currentSrc",
        "currentTime",
        "defaultMuted",
        "defaultPlaybackRate",
        "duration",
        "ended",
        "error",
        "loop",
        "mediaGroup",
        "muted",
        "networkState",
        "paused",
        "playbackRate",
        "played",
        "preload",
        "readyState",
        "seekable",
        "seeking",
        "src",
        "startDate",
        "textTracks",
        "videoTracks",
        "volume",
      ],
      methods: ["addTextTrack", "canPlayType", "load", "play", "pause"],
      events: [
        "abort",
        "canplay",
        "canplaythrough",
        "durationchange",
        "emptied",
        "ended",
        "error",
        "loadeddata",
        "loadedmetadata",
        "loadstart",
        "pause",
        "play",
        "playing",
        "progress",
        "ratechange",
        "seeked",
        "seeking",
        "stalled",
        "suspend",
        "timeupdate",
        "volumechange",
        "waiting",
      ],
    },
    vt = function e(r) {
      t(this, e);
      var n = r.constructor.kindOf,
        o = r.option.whitelist;
      this.state =
        !r.isMobile ||
        o.some(function (t) {
          switch (n(t)) {
            case "string":
              return "*" === t || r.userAgent.indexOf(t) > -1;
            case "function":
              return t(r.userAgent);
            case "regexp":
              return t.test(r.userAgent);
            default:
              return !1;
          }
        });
    },
    gt = (function () {
      function e(r) {
        var n = this;
        t(this, e),
          (this.art = r),
          r.option.container instanceof Element
            ? (this.$container = r.option.container)
            : ((this.$container = b(r.option.container)),
              L(
                this.$container,
                "No container element found by ".concat(r.option.container)
              )),
          L(
            r.constructor.instances.every(function (t) {
              return t.template.$container !== n.$container;
            }),
            "Cannot mount multiple instances on the same dom element"
          ),
          r.whitelist.state ? this.desktop() : this.mobile();
      }
      return (
        r(e, [
          {
            key: "query",
            value: function (t) {
              return b(t, this.$container);
            },
          },
          {
            key: "desktop",
            value: function () {
              var t = this.art.option,
                e = t.theme,
                r = t.backdrop;
              (this.$container.innerHTML = '<div class="art-undercover"></div><div class="art-video-player art-subtitle-show art-layer-show" style="--theme: '.concat(
                e,
                '"><video class="art-video"></video><div class="art-subtitle"></div><div class="art-danmuku"></div><div class="art-layers"></div><div class="art-mask"><div class="art-state"></div></div><div class="art-bottom"><div class="art-progress"></div><div class="art-controls"><div class="art-controls-left"></div><div class="art-controls-right"></div></div></div><div class="art-loading"></div><div class="art-notice"><div class="art-notice-inner"></div></div><div class="art-settings"><div class="art-setting-inner"><div class="art-setting-body"></div></div></div><div class="art-info"><div class="art-info-panel"><div class="art-info-item"><div class="art-info-title">Player version:</div><div class="art-info-content">3.5.26</div></div><div class="art-info-item"><div class="art-info-title">Video url:</div><div class="art-info-content" data-video="src"></div></div><div class="art-info-item"><div class="art-info-title">Video volume:</div><div class="art-info-content" data-video="volume"></div></div><div class="art-info-item"><div class="art-info-title">Video time:</div><div class="art-info-content" data-video="currentTime"></div></div><div class="art-info-item"><div class="art-info-title">Video duration:</div><div class="art-info-content" data-video="duration"></div></div><div class="art-info-item"><div class="art-info-title">Video resolution:</div><div class="art-info-content"><span data-video="videoWidth"></span> x <span data-video="videoHeight"></span></div></div></div><div class="art-info-close">[x]</div></div><div class="art-mini-header"><div class="art-mini-title"></div><div class="art-mini-close">xD7</div></div><div class="art-contextmenus"></div></div>'
              )),
                (this.$undercover = this.query(".art-undercover")),
                (this.$player = this.query(".art-video-player")),
                (this.$video = this.query(".art-video")),
                (this.$subtitle = this.query(".art-subtitle")),
                (this.$danmuku = this.query(".art-danmuku")),
                (this.$bottom = this.query(".art-bottom")),
                (this.$progress = this.query(".art-progress")),
                (this.$controls = this.query(".art-controls")),
                (this.$controlsLeft = this.query(".art-controls-left")),
                (this.$controlsRight = this.query(".art-controls-right")),
                (this.$layer = this.query(".art-layers")),
                (this.$loading = this.query(".art-loading")),
                (this.$notice = this.query(".art-notice")),
                (this.$noticeInner = this.query(".art-notice-inner")),
                (this.$mask = this.query(".art-mask")),
                (this.$state = this.query(".art-state")),
                (this.$setting = this.query(".art-settings")),
                (this.$settingInner = this.query(".art-setting-inner")),
                (this.$settingBody = this.query(".art-setting-body")),
                (this.$info = this.query(".art-info")),
                (this.$infoPanel = this.query(".art-info-panel")),
                (this.$infoClose = this.query(".art-info-close")),
                (this.$miniHeader = this.query(".art-mini-header")),
                (this.$miniTitle = this.query(".art-mini-title")),
                (this.$miniClose = this.query(".art-mini-close")),
                (this.$contextmenu = this.query(".art-contextmenus")),
                r &&
                  (g(this.$settingInner, "art-backdrop-filter"),
                  g(this.$info, "art-backdrop-filter"),
                  g(this.$contextmenu, "art-backdrop-filter")),
                this.art.isMobile && g(this.$container, "art-mobile");
            },
          },
          {
            key: "mobile",
            value: function () {
              (this.$container.innerHTML =
                '<div class="art-video-player"><video class="art-video"></video></div>'),
                (this.$player = this.query(".art-video-player")),
                (this.$video = this.query(".art-video"));
            },
          },
          {
            key: "destroy",
            value: function (t) {
              t
                ? (this.$container.innerHTML = "")
                : g(this.$player, "art-destroy");
            },
          },
        ]),
        e
      );
    })(),
    mt = {
      "Video info": "统计信息",
      Close: "关闭",
      "Light Off": "关灯",
      "Light On": "开灯",
      "Video load failed": "加载失败",
      Volume: "音量",
      Play: "播放",
      Pause: "暂停",
      Rate: "速度",
      Mute: "静音",
      Flip: "翻转",
      Rotate: "旋转",
      Horizontal: "水平",
      Vertical: "垂直",
      Reconnect: "重新连接",
      "Hide subtitle": "隐藏字幕",
      "Show subtitle": "显示字幕",
      "Hide danmu": "隐藏弹幕",
      "Show danmu": "显示弹幕",
      "Show setting": "显示设置",
      "Hide setting": "隐藏设置",
      Screenshot: "截图",
      "Play speed": "播放速度",
      "Aspect ratio": "画面比例",
      Default: "默认",
      Normal: "正常",
      Open: "打开",
      "Switch video": "切换",
      "Switch subtitle": "切换字幕",
      Fullscreen: "全屏",
      "Exit fullscreen": "退出全屏",
      "Web fullscreen": "网页全屏",
      "Exit web fullscreen": "退出网页全屏",
      "Mini player": "迷你播放器",
      "PIP mode": "画中画模式",
      "Exit PIP mode": "退出画中画模式",
      "PIP not supported": "不支持画中画模式",
      "Fullscreen not supported": "不支持全屏模式",
      "Local Subtitle": "本地字幕",
      "Local Video": "本地视频",
      "Subtitle offset time": "字幕偏移时间",
      "No subtitles found": "未发现字幕",
    },
    wt = {
      "Video info": "統計訊息",
      Close: "關閉",
      "Light Off": "關燈",
      "Light On": "開燈",
      "Video load failed": "載入失敗",
      Volume: "音量",
      Play: "播放",
      Pause: "暫停",
      Rate: "速度",
      Mute: "靜音",
      Flip: "翻轉",
      Rotate: "旋轉",
      Horizontal: "水平",
      Vertical: "垂直",
      Reconnect: "重新連接",
      "Hide subtitle": "隱藏字幕",
      "Show subtitle": "顯示字幕",
      "Hide danmu": "隱藏彈幕",
      "Show danmu": "顯示彈幕",
      "Show setting": "顯示设置",
      "Hide setting": "隱藏设置",
      Screenshot: "截圖",
      "Play speed": "播放速度",
      "Aspect ratio": "畫面比例",
      Default: "默認",
      Normal: "正常",
      Open: "打開",
      "Switch video": "切換",
      "Switch subtitle": "切換字幕",
      Fullscreen: "全屏",
      "Exit fullscreen": "退出全屏",
      "Web fullscreen": "網頁全屏",
      "Exit web fullscreen": "退出網頁全屏",
      "Mini player": "迷你播放器",
      "PIP mode": "畫中畫模式",
      "Exit PIP mode": "退出畫中畫模式",
      "PIP not supported": "不支持畫中畫模式",
      "Fullscreen not supported": "不支持全屏模式",
      "Local Subtitle": "本地字幕",
      "Local Video": "本地視頻",
      "Subtitle offset time": "字幕偏移時間",
      "No subtitles found": "未發現字幕",
    },
    xt = (function () {
      function e(r) {
        t(this, e),
          (this.art = r),
          (this.languages = { "zh-cn": mt, "zh-tw": wt }),
          this.init();
      }
      return (
        r(e, [
          {
            key: "init",
            value: function () {
              var t = this.art.option.lang.toLowerCase();
              this.language = this.languages[t] || {};
            },
          },
          {
            key: "get",
            value: function (t) {
              return this.language[t] || t;
            },
          },
          {
            key: "update",
            value: function (t) {
              (this.languages = Q(this.languages, t)), this.init();
            },
          },
        ]),
        e
      );
    })();
  var Ot = o(function (t) {
    !(function () {
      var e =
          "undefined" != typeof window && void 0 !== window.document
            ? window.document
            : {},
        r = t.exports,
        n = (function () {
          for (
            var t,
              r = [
                [
                  "requestFullscreen",
                  "exitFullscreen",
                  "fullscreenElement",
                  "fullscreenEnabled",
                  "fullscreenchange",
                  "fullscreenerror",
                ],
                [
                  "webkitRequestFullscreen",
                  "webkitExitFullscreen",
                  "webkitFullscreenElement",
                  "webkitFullscreenEnabled",
                  "webkitfullscreenchange",
                  "webkitfullscreenerror",
                ],
                [
                  "webkitRequestFullScreen",
                  "webkitCancelFullScreen",
                  "webkitCurrentFullScreenElement",
                  "webkitCancelFullScreen",
                  "webkitfullscreenchange",
                  "webkitfullscreenerror",
                ],
                [
                  "mozRequestFullScreen",
                  "mozCancelFullScreen",
                  "mozFullScreenElement",
                  "mozFullScreenEnabled",
                  "mozfullscreenchange",
                  "mozfullscreenerror",
                ],
                [
                  "msRequestFullscreen",
                  "msExitFullscreen",
                  "msFullscreenElement",
                  "msFullscreenEnabled",
                  "MSFullscreenChange",
                  "MSFullscreenError",
                ],
              ],
              n = 0,
              o = r.length,
              i = {};
            n < o;
            n++
          )
            if ((t = r[n]) && t[1] in e) {
              for (n = 0; n < t.length; n++) i[r[0][n]] = t[n];
              return i;
            }
          return !1;
        })(),
        o = { change: n.fullscreenchange, error: n.fullscreenerror },
        i = {
          request: function (t) {
            return new Promise(
              function (r, o) {
                var i = function () {
                  this.off("change", i), r();
                }.bind(this);
                this.on("change", i);
                var a = (t = t || e.documentElement)[n.requestFullscreen]();
                a instanceof Promise && a.then(i).catch(o);
              }.bind(this)
            );
          },
          exit: function () {
            return new Promise(
              function (t, r) {
                if (this.isFullscreen) {
                  var o = function () {
                    this.off("change", o), t();
                  }.bind(this);
                  this.on("change", o);
                  var i = e[n.exitFullscreen]();
                  i instanceof Promise && i.then(o).catch(r);
                } else t();
              }.bind(this)
            );
          },
          toggle: function (t) {
            return this.isFullscreen ? this.exit() : this.request(t);
          },
          onchange: function (t) {
            this.on("change", t);
          },
          onerror: function (t) {
            this.on("error", t);
          },
          on: function (t, r) {
            var n = o[t];
            n && e.addEventListener(n, r, !1);
          },
          off: function (t, r) {
            var n = o[t];
            n && e.removeEventListener(n, r, !1);
          },
          raw: n,
        };
      n
        ? (Object.defineProperties(i, {
            isFullscreen: {
              get: function () {
                return Boolean(e[n.fullscreenElement]);
              },
            },
            element: {
              enumerable: !0,
              get: function () {
                return e[n.fullscreenElement];
              },
            },
            isEnabled: {
              enumerable: !0,
              get: function () {
                return Boolean(e[n.fullscreenEnabled]);
              },
            },
          }),
          r ? (t.exports = i) : (window.screenfull = i))
        : r
        ? (t.exports = { isEnabled: !1 })
        : (window.screenfull = { isEnabled: !1 });
    })();
  });
  Ot.isEnabled;
  function kt(t, e) {
    var r = t.i18n,
      n = t.notice,
      o = t.template.$video;
    t.once("ready", function () {
      Ot.isEnabled
        ? (function (t, e) {
            var r = t.template.$player;
            X(e, "fullscreen", {
              get: function () {
                return Ot.isFullscreen;
              },
              set: function (n) {
                n
                  ? Ot.request(r).then(function () {
                      g(r, "art-fullscreen"),
                        (e.aspectRatioReset = !0),
                        t.emit("resize"),
                        t.emit("fullscreen", !0);
                    })
                  : Ot.exit().then(function () {
                      m(r, "art-fullscreen"),
                        (e.aspectRatioReset = !0),
                        (e.autoSize = t.option.autoSize),
                        t.emit("resize"),
                        t.emit("fullscreen");
                    });
              },
            });
          })(t, e)
        : o.webkitSupportsFullscreen
        ? (function (t, e) {
            var r = t.template.$video;
            X(e, "fullscreen", {
              get: function () {
                return r.webkitDisplayingFullscreen;
              },
              set: function (t) {
                t ? r.webkitEnterFullscreen() : r.webkitExitFullscreen();
              },
            });
          })(t, e)
        : X(e, "fullscreen", {
            get: function () {
              return !1;
            },
            set: function () {
              n.show = r.get("Fullscreen not supported");
            },
          });
    }),
      X(e, "fullscreenToggle", {
        set: function (t) {
          t && (e.fullscreen = !e.fullscreen);
        },
      });
  }
  function jt(t, e) {
    var r = t.i18n,
      n = t.notice,
      o = t.template.$video;
    document.pictureInPictureEnabled
      ? (function (t, e) {
          var r = t.template.$video,
            n = t.events.proxy,
            o = t.notice;
          (r.disablePictureInPicture = !1),
            X(e, "pip", {
              get: function () {
                return document.pictureInPictureElement;
              },
              set: function (t) {
                t
                  ? r.requestPictureInPicture().catch(function (t) {
                      throw ((o.show = t), t);
                    })
                  : document.exitPictureInPicture().catch(function (t) {
                      throw ((o.show = t), t);
                    });
              },
            }),
            n(r, "enterpictureinpicture", function () {
              t.emit("pip", !0);
            }),
            n(r, "leavepictureinpicture", function () {
              t.emit("pip");
            });
        })(t, e)
      : o.webkitSupportsPresentationMode
      ? (function (t, e) {
          var r = t.template.$video;
          r.webkitSetPresentationMode("inline"),
            X(e, "pip", {
              get: function () {
                return "picture-in-picture" === r.webkitPresentationMode;
              },
              set: function (e) {
                e
                  ? (r.webkitSetPresentationMode("picture-in-picture"),
                    t.emit("pip", !0))
                  : (r.webkitSetPresentationMode("inline"), t.emit("pip"));
              },
            });
        })(t, e)
      : X(e, "pip", {
          get: function () {
            return !1;
          },
          set: function () {
            n.show = r.get("PIP not supported");
          },
        }),
      X(e, "pipToggle", {
        set: function (t) {
          t && (e.pip = !e.pip);
        },
      });
  }
  var Pt = function e(r) {
    var n;
    t(this, e),
      (function (t, e) {
        var r = t.option,
          n = t.template.$video;
        X(e, "url", {
          get: function () {
            return n.src;
          },
          set: function (e) {
            var o = r.type || H(e),
              i = r.customType[o];
            o && i
              ? G().then(function () {
                  t.loading.show = !0;
                  var r = i.call(t, n, e, t);
                  X(t, o, { value: r });
                })
              : ((n.src = e), (t.option.url = e), t.emit("url", e));
          },
        });
      })(r, this),
      (function (t, e) {
        var r = t.option,
          n = t.events.proxy,
          o = t.template,
          i = o.$player,
          a = o.$video,
          c = t.i18n,
          l = t.notice,
          s = 0;
        n(a, "click", function () {
          e.toggle = !0;
        }),
          bt.events.forEach(function (e) {
            n(a, e, function (e) {
              t.emit("video:".concat(e.type), e);
            });
          }),
          t.on("video:canplay", function () {
            (s = 0), (t.loading.show = !1);
          }),
          t.once("video:canplay", function () {
            (t.loading.show = !1),
              (t.controls.show = !0),
              (t.mask.show = !0),
              t.emit("ready");
          }),
          t.on("video:ended", function () {
            r.loop
              ? ((e.seek = 0),
                (e.play = !0),
                (t.controls.show = !1),
                (t.mask.show = !1))
              : ((t.controls.show = !0), (t.mask.show = !0));
          }),
          t.on("video:error", function () {
            s < 5
              ? G(1e3).then(function () {
                  (s += 1),
                    (e.url = r.url),
                    (l.show = "".concat(c.get("Reconnect"), ": ").concat(s));
                })
              : ((t.loading.show = !1),
                (t.controls.show = !1),
                g(i, "art-error"),
                G(1e3).then(function () {
                  (l.show = c.get("Video load failed")), t.destroy(!1);
                }));
          }),
          t.once("video:loadedmetadata", function () {
            (e.autoSize = r.autoSize),
              t.isMobile &&
                ((t.loading.show = !1),
                (t.controls.show = !0),
                (t.mask.show = !0),
                t.emit("ready"));
          }),
          t.on("video:loadstart", function () {
            t.loading.show = !0;
          }),
          t.on("video:pause", function () {
            (t.controls.show = !0), (t.mask.show = !0);
          }),
          t.on("video:play", function () {
            t.mask.show = !1;
          }),
          t.on("video:playing", function () {
            t.mask.show = !1;
          }),
          t.on("video:seeked", function () {
            t.loading.show = !1;
          }),
          t.on("video:seeking", function () {
            t.loading.show = !0;
          }),
          t.on("video:timeupdate", function () {
            t.mask.show = !1;
          }),
          t.on("video:waiting", function () {
            t.loading.show = !0;
          });
      })(r, this),
      (function (t, e) {
        var r = t.option,
          n = t.storage,
          o = t.template.$video;
        Object.keys(r.moreVideoAttr).forEach(function (t) {
          o[t] = r.moreVideoAttr[t];
        }),
          r.muted && (o.muted = r.muted),
          r.volume && (o.volume = et(r.volume, 0, 1));
        var i = n.get("volume");
        i && (o.volume = et(i, 0, 1)),
          r.poster && (o.poster = r.poster),
          r.autoplay && (o.autoplay = r.autoplay),
          (o.controls = !1),
          (e.url = r.url);
      })(r, this),
      (function (t, e) {
        var r,
          n = [
            "mini",
            "pip",
            "fullscreen",
            "fullscreenWeb",
            "fullscreenRotate",
          ];
        (r = n).forEach(function (n) {
          t.on(n, function () {
            e[n] &&
              r
                .filter(function (t) {
                  return t !== n;
                })
                .forEach(function (t) {
                  e[t] && (e[t] = !1);
                });
          });
        }),
          X(e, "normalSize", {
            get: function () {
              return n.every(function (t) {
                return !e[t];
              });
            },
          });
      })(r, this),
      (function (t, e) {
        var r = t.i18n,
          n = t.notice,
          o = t.constructor.instances,
          i = t.option.mutex,
          a = t.template.$video;
        X(e, "play", {
          set: function (c) {
            if (c) {
              var l = a.play();
              l.then &&
                l.then().catch(function (t) {
                  throw ((n.show = t), t);
                }),
                i &&
                  o
                    .filter(function (e) {
                      return e !== t;
                    })
                    .forEach(function (t) {
                      t.player.pause = !0;
                    }),
                (n.show = r.get("Play")),
                t.emit("play");
            } else e.pause = !0;
          },
        });
      })(r, this),
      (function (t, e) {
        var r = t.template.$video,
          n = t.i18n,
          o = t.notice;
        X(e, "pause", {
          get: function () {
            return r.paused;
          },
          set: function (i) {
            i
              ? (r.pause(), (o.show = n.get("Pause")), t.emit("pause"))
              : (e.play = !0);
          },
        });
      })(r, this),
      X((n = this), "toggle", {
        set: function (t) {
          t && (n.playing ? (n.pause = !0) : (n.play = !0));
        },
      }),
      (function (t, e) {
        var r = t.notice;
        X(e, "seek", {
          set: function (n) {
            (e.currentTime = n),
              t.emit("seek", e.currentTime),
              e.duration &&
                (r.show = ""
                  .concat(rt(e.currentTime), " / ")
                  .concat(rt(e.duration)));
          },
        }),
          X(e, "forward", {
            set: function (t) {
              e.seek = e.currentTime + t;
            },
          }),
          X(e, "backward", {
            set: function (t) {
              e.seek = e.currentTime - t;
            },
          });
      })(r, this),
      (function (t, e) {
        var r = t.template.$video,
          n = t.i18n,
          o = t.notice,
          i = t.storage;
        X(e, "volume", {
          get: function () {
            return r.volume || 0;
          },
          set: function (e) {
            (r.volume = et(e, 0, 1)),
              (o.show = ""
                .concat(n.get("Volume"), ": ")
                .concat(parseInt(100 * r.volume, 10))),
              0 !== r.volume && i.set("volume", r.volume),
              t.emit("volume", r.volume);
          },
        }),
          X(e, "muted", {
            get: function () {
              return r.muted;
            },
            set: function (e) {
              (r.muted = e), t.emit("volume", r.volume);
            },
          });
      })(r, this),
      (function (t, e) {
        var r = t.template.$video;
        X(e, "currentTime", {
          get: function () {
            return r.currentTime || 0;
          },
          set: function (t) {
            r.currentTime = et(t, 0, e.duration);
          },
        });
      })(r, this),
      (function (t, e) {
        X(e, "duration", {
          get: function () {
            return t.template.$video.duration || 0;
          },
        });
      })(r, this),
      (function (t, e) {
        var r = t.i18n,
          n = t.notice;
        function o(o, i, a) {
          if (o !== e.url) {
            URL.revokeObjectURL(e.url);
            var c = e.playing;
            (e.url = o),
              t.once("video:canplay", function () {
                (e.playbackRate = !1),
                  (e.aspectRatio = !1),
                  (e.flip = "normal"),
                  (e.autoSize = !0),
                  (e.currentTime = a),
                  c && (e.play = !0);
              }),
              i && (n.show = "".concat(r.get("Switch video"), ": ").concat(i)),
              t.emit("switch", o);
          }
        }
        X(e, "switchQuality", {
          value: function (t, r) {
            return o(t, r, e.currentTime);
          },
        }),
          X(e, "switchUrl", {
            value: function (t, e) {
              return o(t, e, 0);
            },
          });
      })(r, this),
      (function (t, e) {
        var r = t.template,
          n = r.$video,
          o = r.$player,
          i = t.i18n,
          a = t.notice;
        X(e, "playbackRate", {
          get: function () {
            return o.dataset.playbackRate;
          },
          set: function (r) {
            if (r) {
              if (r === o.dataset.playbackRate) return;
              var c = [0.5, 0.75, 1, 1.25, 1.5, 1.75, 2];
              L(
                c.includes(r),
                "'playbackRate' only accept ".concat(
                  c.toString(),
                  " as parameters"
                )
              ),
                (n.playbackRate = r),
                (o.dataset.playbackRate = r),
                (a.show = ""
                  .concat(i.get("Rate"), ": ")
                  .concat(1 === r ? i.get("Normal") : "".concat(r, "x"))),
                t.emit("playbackRate", r);
            } else
              e.playbackRate &&
                ((e.playbackRate = 1),
                delete o.dataset.playbackRate,
                t.emit("playbackRate"));
          },
        }),
          X(e, "playbackRateReset", {
            set: function (t) {
              if (t) {
                var r = o.dataset.playbackRate;
                r && (e.playbackRate = Number(r));
              }
            },
          });
      })(r, this),
      (function (t, e) {
        var r = t.template,
          n = r.$video,
          o = r.$player,
          i = t.i18n,
          a = t.notice;
        X(e, "aspectRatio", {
          get: function () {
            return o.dataset.aspectRatio || "";
          },
          set: function (e) {
            e || (e = "default");
            var r = ["default", "4:3", "16:9"];
            if (
              (L(
                r.includes(e),
                "'aspectRatio' only accept ".concat(
                  r.toString(),
                  " as parameters"
                )
              ),
              "default" === e)
            )
              O(n, "width", null),
                O(n, "height", null),
                O(n, "padding", null),
                delete o.dataset.aspectRatio;
            else {
              var c = e.split(":"),
                l = n.videoWidth,
                s = n.videoHeight,
                u = o.clientWidth,
                p = o.clientHeight,
                f = l / s,
                d = c[0] / c[1];
              if (f > d) {
                var h = (d * s) / l;
                O(n, "width", "".concat(100 * h, "%")),
                  O(n, "height", "100%"),
                  O(n, "padding", "0 ".concat((u - u * h) / 2, "px"));
              } else {
                var y = l / d / s;
                O(n, "width", "100%"),
                  O(n, "height", "".concat(100 * y, "%")),
                  O(n, "padding", "".concat((p - p * y) / 2, "px 0"));
              }
              o.dataset.aspectRatio = e;
            }
            (a.show = ""
              .concat(i.get("Aspect ratio"), ": ")
              .concat("default" === e ? i.get("Default") : e)),
              t.emit("aspectRatio", e);
          },
        }),
          X(e, "aspectRatioReset", {
            set: function (t) {
              if (t && e.aspectRatio) {
                var r = e.aspectRatio;
                e.aspectRatio = r;
              }
            },
          });
      })(r, this),
      (function (t, e) {
        var r = t.option,
          n = t.notice,
          o = t.template.$video,
          i = document.createElement("canvas");
        X(e, "getDataURL", {
          value: function () {
            return new Promise(function (t, e) {
              try {
                (i.width = o.videoWidth),
                  (i.height = o.videoHeight),
                  i.getContext("2d").drawImage(o, 0, 0),
                  t(i.toDataURL("image/png"));
              } catch (t) {
                (n.show = t), e(t);
              }
            });
          },
        }),
          X(e, "getBlobUrl", {
            value: function () {
              return new Promise(function (t, e) {
                try {
                  (i.width = o.videoWidth),
                    (i.height = o.videoHeight),
                    i.getContext("2d").drawImage(o, 0, 0),
                    i.toBlob(function (e) {
                      t(URL.createObjectURL(e));
                    });
                } catch (t) {
                  (n.show = t), e(t);
                }
              });
            },
          }),
          X(e, "screenshot", {
            value: function () {
              e.getDataURL().then(function (e) {
                W(
                  e,
                  ""
                    .concat(r.title || "artplayer", "_")
                    .concat(rt(o.currentTime), ".png")
                ),
                  t.emit("screenshot", e);
              });
            },
          });
      })(r, this),
      kt(r, this),
      (function (t, e) {
        var r = t.template.$player;
        X(e, "fullscreenWeb", {
          get: function () {
            return w(r, "art-fullscreen-web");
          },
          set: function (n) {
            n
              ? (g(r, "art-fullscreen-web"),
                (e.aspectRatioReset = !0),
                t.emit("resize"),
                t.emit("fullscreenWeb", !0))
              : (m(r, "art-fullscreen-web"),
                (e.aspectRatioReset = !0),
                (e.autoSize = t.option.autoSize),
                t.emit("resize"),
                t.emit("fullscreenWeb"));
          },
        }),
          X(e, "fullscreenWebToggle", {
            set: function (t) {
              t && (e.fullscreenWeb = !e.fullscreenWeb);
            },
          });
      })(r, this),
      (function (t, e) {
        var r = t.template,
          n = r.$container,
          o = r.$player;
        X(e, "fullscreenRotate", {
          get: function () {
            return w(n, "art-fullscreen-rotate");
          },
          set: function (r) {
            if (r) {
              g(n, "art-fullscreen-rotate"), (e.autoSize = !0);
              var i = document.body,
                a = i.clientHeight,
                c = i.clientWidth,
                l = o.clientHeight,
                s = o.clientWidth;
              if (c / a < s / l) {
                var u = Math.min(a / s, c / l).toFixed(2);
                O(
                  o,
                  "transform",
                  "rotate(90deg) scale(".concat(u, ",").concat(u, ")")
                ),
                  t.emit("resize"),
                  t.emit("fullscreenRotate", !0);
              }
            } else
              m(n, "art-fullscreen-rotate"),
                (e.autoSize = t.option.autoSize),
                O(o, "transform", null),
                t.emit("resize"),
                t.emit("fullscreenRotate");
          },
        }),
          X(e, "fullscreenRotateToggle", {
            set: function (t) {
              t && (e.fullscreenRotate = !e.fullscreenRotate);
            },
          });
      })(r, this),
      jt(r, this),
      (function (t, e) {
        var r = t.template.$video;
        X(e, "loaded", {
          get: function () {
            return e.loadedTime / r.duration;
          },
        }),
          X(e, "loadedTime", {
            get: function () {
              return r.buffered.length
                ? r.buffered.end(r.buffered.length - 1)
                : 0;
            },
          });
      })(r, this),
      (function (t, e) {
        X(e, "played", {
          get: function () {
            return e.currentTime / e.duration;
          },
        });
      })(0, this),
      (function (t, e) {
        var r = t.template.$video;
        X(e, "playing", {
          get: function () {
            return !!(
              r.currentTime > 0 &&
              !r.paused &&
              !r.ended &&
              r.readyState > 2
            );
          },
        });
      })(r, this),
      (function (t, e) {
        var r = t.template,
          n = r.$container,
          o = r.$player,
          i = r.$video;
        X(e, "autoSize", {
          get: function () {
            return w(n, "art-auto-size");
          },
          set: function (r) {
            if (r) {
              var a = i.videoWidth,
                c = i.videoHeight,
                l = n.getBoundingClientRect(),
                s = l.width,
                u = l.height,
                p = a / c,
                f = s / u;
              if ((g(n, "art-auto-size"), f > p))
                O(o, "width", "".concat(((u * p) / s) * 100, "%")),
                  O(o, "height", "100%");
              else {
                var d = (s / p / u) * 100;
                O(o, "width", "100%"), O(o, "height", "".concat(d, "%"));
              }
              t.emit("autoSize", { width: e.width, height: e.height });
            } else
              m(n, "art-auto-size"),
                O(o, "width", null),
                O(o, "height", null),
                t.emit("autoSize");
          },
        });
      })(r, this),
      (function (t, e) {
        X(e, "rect", {
          get: function () {
            return t.template.$player.getBoundingClientRect();
          },
        }),
          ["bottom", "height", "left", "right", "top", "width"].forEach(
            function (t) {
              X(e, t, {
                get: function () {
                  return e.rect[t];
                },
              });
            }
          ),
          X(e, "x", {
            get: function () {
              return e.left + window.pageXOffset;
            },
          }),
          X(e, "y", {
            get: function () {
              return e.top + window.pageYOffset;
            },
          });
      })(r, this),
      (function (t, e) {
        var r = t.template.$player,
          n = t.i18n,
          o = t.notice;
        X(e, "flip", {
          get: function () {
            return r.dataset.flip;
          },
          set: function (i) {
            i || (i = "normal");
            var a = ["normal", "horizontal", "vertical"];
            L(
              a.includes(i),
              "'flip' only accept ".concat(a.toString(), " as parameters")
            ),
              "normal" === i
                ? delete r.dataset.flip
                : ((e.rotate = !1), (r.dataset.flip = i));
            var c = i.replace(i[0], i[0].toUpperCase());
            (o.show = "".concat(n.get("Flip"), ": ").concat(n.get(c))),
              t.emit("flip", i);
          },
        }),
          X(e, "flipReset", {
            set: function (t) {
              if (t && e.flip) {
                var r = e.flip;
                e.flip = r;
              }
            },
          });
      })(r, this),
      (function (t, e) {
        var r = t.template.$undercover;
        X(e, "light", {
          get: function () {
            return "none" !== j(r, "display", !1);
          },
          set: function (e) {
            O(r, "display", e ? "block" : "none"), t.emit("light", e);
          },
        });
      })(r, this),
      (function (t, e) {
        var r = t.i18n,
          n = t.option,
          o = t.storage,
          i = t.events.proxy,
          a = t.template,
          c = a.$player,
          l = a.$miniClose,
          s = a.$miniTitle,
          u = a.$miniHeader,
          p = "",
          f = !1,
          d = 0,
          h = 0,
          y = 0,
          b = 0;
        i(u, "mousedown", function (t) {
          (f = !0), (d = t.pageX), (h = t.pageY), (y = e.left), (b = e.top);
        }),
          i(document, "mousemove", function (t) {
            if (f) {
              g(c, "art-is-dragging");
              var e = b + t.pageY - h,
                r = y + t.pageX - d;
              O(c, "top", "".concat(e, "px")),
                O(c, "left", "".concat(r, "px")),
                o.set("top", e),
                o.set("left", r);
            }
          }),
          i(document, "mouseup", function () {
            (f = !1), m(c, "art-is-dragging");
          }),
          i(l, "click", function () {
            (e.mini = !1), (f = !1), m(c, "art-is-dragging");
          }),
          x(s, n.title || r.get("Mini player")),
          X(e, "mini", {
            get: function () {
              return w(c, "art-mini");
            },
            set: function (r) {
              if (r) {
                (e.autoSize = !1), (p = c.style.cssText), g(c, "art-mini");
                var i = o.get("top"),
                  a = o.get("left");
                if (i && a)
                  O(c, "top", "".concat(i, "px")),
                    O(c, "left", "".concat(a, "px")),
                    E(u) || (o.del("top"), o.del("left"), (e.mini = !0));
                else {
                  var l = document.body,
                    s = l.clientHeight - e.height - 50,
                    f = l.clientWidth - e.width - 50;
                  o.set("top", s),
                    o.set("left", f),
                    O(c, "top", "".concat(s, "px")),
                    O(c, "left", "".concat(f, "px"));
                }
                (e.aspectRatio = !1), (e.playbackRate = !1), t.emit("mini", !0);
              } else
                (c.style.cssText = p),
                  m(c, "art-mini"),
                  O(c, "top", null),
                  O(c, "left", null),
                  (e.aspectRatio = !1),
                  (e.playbackRate = !1),
                  (e.autoSize = n.autoSize),
                  t.emit("mini");
            },
          }),
          X(e, "miniToggle", {
            set: function (t) {
              t && (e.mini = !e.mini);
            },
          });
      })(r, this),
      (function (t, e) {
        var r = [];
        X(e, "loop", {
          get: function () {
            return r;
          },
          set: function (n) {
            if (
              Array.isArray(n) &&
              "number" == typeof n[0] &&
              "number" == typeof n[1]
            ) {
              var o = et(n[0], 0, Math.min(n[1], e.duration)),
                i = et(n[1], o, e.duration);
              i - o >= 1
                ? ((r = [o, i]), t.emit("loop", r))
                : ((r = []), t.emit("loop"));
            } else (r = []), t.emit("loop");
          },
        }),
          t.on("video:timeupdate", function () {
            r.length &&
              (e.currentTime < r[0] || e.currentTime > r[1]) &&
              (e.seek = r[0]);
          });
      })(r, this),
      (function (t, e) {
        var r = t.template,
          n = r.$video,
          o = r.$player,
          i = t.i18n,
          a = t.notice;
        X(e, "rotate", {
          get: function () {
            return Number(o.dataset.rotate) || 0;
          },
          set: function (r) {
            r || (r = 0);
            var c = [-270, -180, -90, 0, 90, 180, 270];
            if (
              (L(
                c.includes(r),
                "'rotate' only accept ".concat(c.toString(), " as parameters")
              ),
              0 === r)
            )
              delete o.dataset.rotate, O(n, "transform", null);
            else {
              (e.flip = !1), (o.dataset.rotate = r);
              var l = function () {
                  var t = n.videoWidth,
                    e = n.videoHeight;
                  return t > e ? e / t : t / e;
                },
                s = 0,
                u = 1;
              switch (r) {
                case -270:
                  (s = 90), (u = l());
                  break;
                case -180:
                  s = 180;
                  break;
                case -90:
                  (s = 270), (u = l());
                  break;
                case 90:
                  (s = 90), (u = l());
                  break;
                case 180:
                  s = 180;
                  break;
                case 270:
                  (s = 270), (u = l());
              }
              O(
                n,
                "transform",
                "rotate(".concat(s, "deg) scale(").concat(u, ")")
              );
            }
            (a.show = "".concat(i.get("Rotate"), ": ").concat(r, "°")),
              t.emit("rotate", r);
          },
        }),
          X(e, "rotateReset", {
            set: function (t) {
              if (t && e.rotate) {
                var r = e.rotate;
                e.rotate = r;
              }
            },
          });
      })(r, this),
      J(r, this);
  };
  var St = function (t, e) {
      for (
        ;
        !Object.prototype.hasOwnProperty.call(t, e) && null !== (t = s(t));

      );
      return t;
    },
    Rt = o(function (t) {
      function e(r, n, o) {
        return (
          "undefined" != typeof Reflect && Reflect.get
            ? (t.exports = e = Reflect.get)
            : (t.exports = e = function (t, e, r) {
                var n = St(t, e);
                if (n) {
                  var o = Object.getOwnPropertyDescriptor(n, e);
                  return o.get ? o.get.call(r) : o.value;
                }
              }),
          e(r, n, o || r)
        );
      }
      t.exports = e;
    }),
    Et = (function () {
      function e(r) {
        t(this, e),
          (this.id = 0),
          (this.art = r),
          (this.add = this.add.bind(this));
      }
      return (
        r(e, [
          {
            key: "add",
            value: function (t) {
              var e = this,
                r = "function" == typeof t ? t(this.art) : t;
              if (this.$parent && this.name && !r.disable) {
                var n = r.name || "".concat(this.name).concat(this.id);
                L(
                  !Z(this, n),
                  "Cannot add an existing name ["
                    .concat(n, "] to the [")
                    .concat(this.name, "]")
                ),
                  (this.id += 1);
                var o = document.createElement("div");
                g(o, "art-".concat(this.name)),
                  g(o, "art-".concat(this.name, "-").concat(n));
                var i = Array.from(this.$parent.children);
                o.dataset.index = r.index || this.id;
                var a = i.find(function (t) {
                  return Number(t.dataset.index) >= Number(o.dataset.index);
                });
                a
                  ? a.insertAdjacentElement("beforebegin", o)
                  : x(this.$parent, o),
                  r.html && x(o, r.html),
                  r.style && k(o, r.style),
                  r.tooltip && R(o, r.tooltip),
                  r.click &&
                    this.art.events.proxy(o, "click", function (t) {
                      t.preventDefault(), r.click.call(e.art, e, t);
                    }),
                  r.selector &&
                    ["left", "right"].includes(r.position) &&
                    this.selector(r, o),
                  r.mounted && r.mounted.call(this.art, o),
                  1 === o.childNodes.length &&
                    3 === o.childNodes[0].nodeType &&
                    g(o, "art-control-onlyText");
              }
            },
          },
          {
            key: "selector",
            value: function (t, e) {
              var r = this,
                n = this.art.events,
                o = n.hover,
                i = n.proxy;
              g(e, "art-control-selector");
              var a = document.createElement("div");
              g(a, "art-selector-value"),
                x(a, t.html),
                (e.innerText = ""),
                x(e, a);
              var c = t.selector
                  .map(function (t) {
                    return '<div class="art-selector-item">'.concat(
                      t.name,
                      "</div>"
                    );
                  })
                  .join(""),
                l = document.createElement("div");
              g(l, "art-selector-list"), x(l, c), x(e, l);
              var s = function () {
                l.style.left = "-".concat(
                  j(l, "width") / 2 - j(e, "width") / 2,
                  "px"
                );
              };
              o(e, s),
                i(e, "click", function (e) {
                  if (w(e.target, "art-selector-item")) {
                    var n = e.target.innerText;
                    if (a.innerText === n) return;
                    var o = t.selector.find(function (t) {
                      return t.name === n;
                    });
                    (a.innerText = n),
                      s(),
                      o &&
                        (t.onSelect && t.onSelect.call(r.art, o),
                        r.art.emit("selector", o));
                  }
                });
            },
          },
          {
            key: "show",
            get: function () {
              return w(
                this.art.template.$player,
                "art-".concat(this.name, "-show")
              );
            },
            set: function (t) {
              var e = this.art.template.$player,
                r = "art-".concat(this.name, "-show");
              t ? g(e, r) : m(e, r), this.art.emit(this.name, t);
            },
          },
          {
            key: "toggle",
            set: function (t) {
              t && (this.show = !this.show);
            },
          },
        ]),
        e
      );
    })();
  function Dt(t, e) {
    var r = Object.keys(t);
    if (Object.getOwnPropertySymbols) {
      var n = Object.getOwnPropertySymbols(t);
      e &&
        (n = n.filter(function (e) {
          return Object.getOwnPropertyDescriptor(t, e).enumerable;
        })),
        r.push.apply(r, n);
    }
    return r;
  }
  function $t(t) {
    for (var e = 1; e < arguments.length; e++) {
      var r = null != arguments[e] ? arguments[e] : {};
      e % 2
        ? Dt(Object(r), !0).forEach(function (e) {
            it(t, e, r[e]);
          })
        : Object.getOwnPropertyDescriptors
        ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(r))
        : Dt(Object(r)).forEach(function (e) {
            Object.defineProperty(t, e, Object.getOwnPropertyDescriptor(r, e));
          });
    }
    return t;
  }
  function Tt(t, e) {
    var r = Object.keys(t);
    if (Object.getOwnPropertySymbols) {
      var n = Object.getOwnPropertySymbols(t);
      e &&
        (n = n.filter(function (e) {
          return Object.getOwnPropertyDescriptor(t, e).enumerable;
        })),
        r.push.apply(r, n);
    }
    return r;
  }
  function zt(t) {
    for (var e = 1; e < arguments.length; e++) {
      var r = null != arguments[e] ? arguments[e] : {};
      e % 2
        ? Tt(Object(r), !0).forEach(function (e) {
            it(t, e, r[e]);
          })
        : Object.getOwnPropertyDescriptors
        ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(r))
        : Tt(Object(r)).forEach(function (e) {
            Object.defineProperty(t, e, Object.getOwnPropertyDescriptor(r, e));
          });
    }
    return t;
  }
  function At(t, e) {
    var r = Object.keys(t);
    if (Object.getOwnPropertySymbols) {
      var n = Object.getOwnPropertySymbols(t);
      e &&
        (n = n.filter(function (e) {
          return Object.getOwnPropertyDescriptor(t, e).enumerable;
        })),
        r.push.apply(r, n);
    }
    return r;
  }
  function Ct(t) {
    for (var e = 1; e < arguments.length; e++) {
      var r = null != arguments[e] ? arguments[e] : {};
      e % 2
        ? At(Object(r), !0).forEach(function (e) {
            it(t, e, r[e]);
          })
        : Object.getOwnPropertyDescriptors
        ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(r))
        : At(Object(r)).forEach(function (e) {
            Object.defineProperty(t, e, Object.getOwnPropertyDescriptor(r, e));
          });
    }
    return t;
  }
  function Lt(t, e) {
    var r = Object.keys(t);
    if (Object.getOwnPropertySymbols) {
      var n = Object.getOwnPropertySymbols(t);
      e &&
        (n = n.filter(function (e) {
          return Object.getOwnPropertyDescriptor(t, e).enumerable;
        })),
        r.push.apply(r, n);
    }
    return r;
  }
  function Mt(t) {
    for (var e = 1; e < arguments.length; e++) {
      var r = null != arguments[e] ? arguments[e] : {};
      e % 2
        ? Lt(Object(r), !0).forEach(function (e) {
            it(t, e, r[e]);
          })
        : Object.getOwnPropertyDescriptors
        ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(r))
        : Lt(Object(r)).forEach(function (e) {
            Object.defineProperty(t, e, Object.getOwnPropertyDescriptor(r, e));
          });
    }
    return t;
  }
  function qt(t, e) {
    var r = Object.keys(t);
    if (Object.getOwnPropertySymbols) {
      var n = Object.getOwnPropertySymbols(t);
      e &&
        (n = n.filter(function (e) {
          return Object.getOwnPropertyDescriptor(t, e).enumerable;
        })),
        r.push.apply(r, n);
    }
    return r;
  }
  function Ft(t) {
    for (var e = 1; e < arguments.length; e++) {
      var r = null != arguments[e] ? arguments[e] : {};
      e % 2
        ? qt(Object(r), !0).forEach(function (e) {
            it(t, e, r[e]);
          })
        : Object.getOwnPropertyDescriptors
        ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(r))
        : qt(Object(r)).forEach(function (e) {
            Object.defineProperty(t, e, Object.getOwnPropertyDescriptor(r, e));
          });
    }
    return t;
  }
  function Ht(t, e) {
    var r = t.template.$progress,
      n = t.player,
      o = r.getBoundingClientRect().left,
      i = et(e.pageX - o, 0, r.clientWidth),
      a = (i / r.clientWidth) * n.duration;
    return {
      second: a,
      time: rt(a),
      width: i,
      percentage: et(i / r.clientWidth, 0, 1),
    };
  }
  function Wt(t) {
    return function (e) {
      var r = e.option,
        n = r.highlight,
        o = r.theme,
        i = e.events.proxy,
        a = e.player;
      return Ft(
        Ft({}, t),
        {},
        {
          html: '<div class="art-control-progress-inner"><div class="art-progress-loaded"></div><div class="art-progress-played" style="background: '
            .concat(
              o,
              '"></div><div class="art-progress-highlight"></div><div class="art-progress-indicator" style="background: '
            )
            .concat(
              o,
              '"></div><div class="art-progress-tip art-tip"></div></div>'
            ),
          mounted: function (t) {
            var r = !1,
              o = b(".art-progress-loaded", t),
              c = b(".art-progress-played", t),
              l = b(".art-progress-highlight", t),
              s = b(".art-progress-indicator", t),
              u = b(".art-progress-tip", t);
            function p(t, e) {
              "loaded" === t && O(o, "width", "".concat(100 * e, "%")),
                "played" === t &&
                  (O(c, "width", "".concat(100 * e, "%")),
                  O(
                    s,
                    "left",
                    "calc("
                      .concat(100 * e, "% - ")
                      .concat(j(s, "width") / 2, "px)")
                  ));
            }
            n.forEach(function (t) {
              var e = (et(t.time, 0, a.duration) / a.duration) * 100;
              x(
                l,
                '<span data-text="'
                  .concat(t.text, '" data-time="')
                  .concat(t.time, '" style="left: ')
                  .concat(e, '%"></span>')
              );
            }),
              p("loaded", a.loaded),
              e.on("video:progress", function () {
                p("loaded", a.loaded);
              }),
              e.on("video:timeupdate", function () {
                p("played", a.played);
              }),
              e.on("video:ended", function () {
                p("played", 1);
              }),
              i(t, "mousemove", function (r) {
                O(u, "display", "block"),
                  D(r, l)
                    ? (function (r) {
                        var n = Ht(e, r).width,
                          o = r.target.dataset.text;
                        u.innerHTML = o;
                        var i = u.clientWidth;
                        n <= i / 2
                          ? O(u, "left", 0)
                          : n > t.clientWidth - i / 2
                          ? O(u, "left", "".concat(t.clientWidth - i, "px"))
                          : O(u, "left", "".concat(n - i / 2, "px"));
                      })(r)
                    : (function (r) {
                        var n = Ht(e, r),
                          o = n.width,
                          i = n.time;
                        u.innerHTML = i;
                        var a = u.clientWidth;
                        o <= a / 2
                          ? O(u, "left", 0)
                          : o > t.clientWidth - a / 2
                          ? O(u, "left", "".concat(t.clientWidth - a, "px"))
                          : O(u, "left", "".concat(o - a / 2, "px"));
                      })(r);
              }),
              i(t, "mouseout", function () {
                O(u, "display", "none");
              }),
              i(t, "click", function (t) {
                if (t.target !== s) {
                  var r = Ht(e, t),
                    n = r.second;
                  p("played", r.percentage), (a.seek = n);
                }
              }),
              i(s, "mousedown", function () {
                r = !0;
              }),
              i(document, "mousemove", function (t) {
                if (r) {
                  var n = Ht(e, t),
                    o = n.second,
                    i = n.percentage;
                  g(s, "art-show-indicator"), p("played", i), (a.seek = o);
                }
              }),
              i(document, "mouseup", function () {
                r && ((r = !1), m(s, "art-show-indicator"));
              });
          },
        }
      );
    };
  }
  function It(t, e) {
    var r = Object.keys(t);
    if (Object.getOwnPropertySymbols) {
      var n = Object.getOwnPropertySymbols(t);
      e &&
        (n = n.filter(function (e) {
          return Object.getOwnPropertyDescriptor(t, e).enumerable;
        })),
        r.push.apply(r, n);
    }
    return r;
  }
  function Vt(t) {
    for (var e = 1; e < arguments.length; e++) {
      var r = null != arguments[e] ? arguments[e] : {};
      e % 2
        ? It(Object(r), !0).forEach(function (e) {
            it(t, e, r[e]);
          })
        : Object.getOwnPropertyDescriptors
        ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(r))
        : It(Object(r)).forEach(function (e) {
            Object.defineProperty(t, e, Object.getOwnPropertyDescriptor(r, e));
          });
    }
    return t;
  }
  function Bt(t, e) {
    var r = Object.keys(t);
    if (Object.getOwnPropertySymbols) {
      var n = Object.getOwnPropertySymbols(t);
      e &&
        (n = n.filter(function (e) {
          return Object.getOwnPropertyDescriptor(t, e).enumerable;
        })),
        r.push.apply(r, n);
    }
    return r;
  }
  function Nt(t) {
    for (var e = 1; e < arguments.length; e++) {
      var r = null != arguments[e] ? arguments[e] : {};
      e % 2
        ? Bt(Object(r), !0).forEach(function (e) {
            it(t, e, r[e]);
          })
        : Object.getOwnPropertyDescriptors
        ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(r))
        : Bt(Object(r)).forEach(function (e) {
            Object.defineProperty(t, e, Object.getOwnPropertyDescriptor(r, e));
          });
    }
    return t;
  }
  function Ut(t, e) {
    var r = Object.keys(t);
    if (Object.getOwnPropertySymbols) {
      var n = Object.getOwnPropertySymbols(t);
      e &&
        (n = n.filter(function (e) {
          return Object.getOwnPropertyDescriptor(t, e).enumerable;
        })),
        r.push.apply(r, n);
    }
    return r;
  }
  function _t(t) {
    for (var e = 1; e < arguments.length; e++) {
      var r = null != arguments[e] ? arguments[e] : {};
      e % 2
        ? Ut(Object(r), !0).forEach(function (e) {
            it(t, e, r[e]);
          })
        : Object.getOwnPropertyDescriptors
        ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(r))
        : Ut(Object(r)).forEach(function (e) {
            Object.defineProperty(t, e, Object.getOwnPropertyDescriptor(r, e));
          });
    }
    return t;
  }
  function Xt(t, e) {
    var r = Object.keys(t);
    if (Object.getOwnPropertySymbols) {
      var n = Object.getOwnPropertySymbols(t);
      e &&
        (n = n.filter(function (e) {
          return Object.getOwnPropertyDescriptor(t, e).enumerable;
        })),
        r.push.apply(r, n);
    }
    return r;
  }
  function Yt(t) {
    for (var e = 1; e < arguments.length; e++) {
      var r = null != arguments[e] ? arguments[e] : {};
      e % 2
        ? Xt(Object(r), !0).forEach(function (e) {
            it(t, e, r[e]);
          })
        : Object.getOwnPropertyDescriptors
        ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(r))
        : Xt(Object(r)).forEach(function (e) {
            Object.defineProperty(t, e, Object.getOwnPropertyDescriptor(r, e));
          });
    }
    return t;
  }
  function Zt(t, e) {
    var r = Object.keys(t);
    if (Object.getOwnPropertySymbols) {
      var n = Object.getOwnPropertySymbols(t);
      e &&
        (n = n.filter(function (e) {
          return Object.getOwnPropertyDescriptor(t, e).enumerable;
        })),
        r.push.apply(r, n);
    }
    return r;
  }
  function Jt(t) {
    for (var e = 1; e < arguments.length; e++) {
      var r = null != arguments[e] ? arguments[e] : {};
      e % 2
        ? Zt(Object(r), !0).forEach(function (e) {
            it(t, e, r[e]);
          })
        : Object.getOwnPropertyDescriptors
        ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(r))
        : Zt(Object(r)).forEach(function (e) {
            Object.defineProperty(t, e, Object.getOwnPropertyDescriptor(r, e));
          });
    }
    return t;
  }
  function Qt(t) {
    return function (e) {
      return Jt(
        Jt({}, t),
        {},
        {
          mounted: function (t) {
            var r = e.option.thumbnails,
              n = e.template.$progress,
              o = e.events,
              i = o.proxy,
              a = o.loadImg,
              c = !1,
              l = !1;
            i(n, "mousemove", function (o) {
              c ||
                ((c = !0),
                a(r.url).then(function () {
                  l = !0;
                })),
                l &&
                  (O(t, "display", "block"),
                  (function (o) {
                    var i = Ht(e, o).width,
                      a = r.url,
                      c = r.height,
                      l = r.width,
                      s = r.number,
                      u = r.column,
                      p = n.clientWidth / s,
                      f = Math.floor(i / p),
                      d = Math.ceil(f / u) - 1,
                      h = f % u || u - 1;
                    O(t, "backgroundImage", "url(".concat(a, ")")),
                      O(t, "height", "".concat(c, "px")),
                      O(t, "width", "".concat(l, "px")),
                      O(
                        t,
                        "backgroundPosition",
                        "-".concat(h * l, "px -").concat(d * c, "px")
                      ),
                      i <= l / 2
                        ? O(t, "left", 0)
                        : i > n.clientWidth - l / 2
                        ? O(t, "left", "".concat(n.clientWidth - l, "px"))
                        : O(t, "left", "".concat(i - l / 2, "px"));
                  })(o));
            }),
              i(n, "mouseout", function () {
                O(t, "display", "none");
              });
          },
        }
      );
    };
  }
  function Gt(t, e) {
    var r = Object.keys(t);
    if (Object.getOwnPropertySymbols) {
      var n = Object.getOwnPropertySymbols(t);
      e &&
        (n = n.filter(function (e) {
          return Object.getOwnPropertyDescriptor(t, e).enumerable;
        })),
        r.push.apply(r, n);
    }
    return r;
  }
  function Kt(t) {
    for (var e = 1; e < arguments.length; e++) {
      var r = null != arguments[e] ? arguments[e] : {};
      e % 2
        ? Gt(Object(r), !0).forEach(function (e) {
            it(t, e, r[e]);
          })
        : Object.getOwnPropertyDescriptors
        ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(r))
        : Gt(Object(r)).forEach(function (e) {
            Object.defineProperty(t, e, Object.getOwnPropertyDescriptor(r, e));
          });
    }
    return t;
  }
  function te(t, e) {
    var r = Object.keys(t);
    if (Object.getOwnPropertySymbols) {
      var n = Object.getOwnPropertySymbols(t);
      e &&
        (n = n.filter(function (e) {
          return Object.getOwnPropertyDescriptor(t, e).enumerable;
        })),
        r.push.apply(r, n);
    }
    return r;
  }
  function ee(t) {
    for (var e = 1; e < arguments.length; e++) {
      var r = null != arguments[e] ? arguments[e] : {};
      e % 2
        ? te(Object(r), !0).forEach(function (e) {
            it(t, e, r[e]);
          })
        : Object.getOwnPropertyDescriptors
        ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(r))
        : te(Object(r)).forEach(function (e) {
            Object.defineProperty(t, e, Object.getOwnPropertyDescriptor(r, e));
          });
    }
    return t;
  }
  function re(t, e) {
    var r = Object.keys(t);
    if (Object.getOwnPropertySymbols) {
      var n = Object.getOwnPropertySymbols(t);
      e &&
        (n = n.filter(function (e) {
          return Object.getOwnPropertyDescriptor(t, e).enumerable;
        })),
        r.push.apply(r, n);
    }
    return r;
  }
  function ne(t) {
    for (var e = 1; e < arguments.length; e++) {
      var r = null != arguments[e] ? arguments[e] : {};
      e % 2
        ? re(Object(r), !0).forEach(function (e) {
            it(t, e, r[e]);
          })
        : Object.getOwnPropertyDescriptors
        ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(r))
        : re(Object(r)).forEach(function (e) {
            Object.defineProperty(t, e, Object.getOwnPropertyDescriptor(r, e));
          });
    }
    return t;
  }
  function oe(t) {
    var e = (function () {
      if ("undefined" == typeof Reflect || !Reflect.construct) return !1;
      if (Reflect.construct.sham) return !1;
      if ("function" == typeof Proxy) return !0;
      try {
        return (
          Date.prototype.toString.call(
            Reflect.construct(Date, [], function () {})
          ),
          !0
        );
      } catch (t) {
        return !1;
      }
    })();
    return function () {
      var r,
        n = s(t);
      if (e) {
        var o = s(this).constructor;
        r = Reflect.construct(n, arguments, o);
      } else r = n.apply(this, arguments);
      return l(this, r);
    };
  }
  var ie = (function (e) {
    a(o, e);
    var n = oe(o);
    function o(e) {
      var r;
      t(this, o), ((r = n.call(this, e)).name = "control");
      var i = e.option,
        a = e.player,
        c = e.template.$player;
      return (
        (r.delayHide = K(function () {
          a.playing &&
            r.show &&
            (g(c, "art-hide-cursor"), m(c, "art-hover"), (r.show = !1));
        }, 3e3)),
        (r.cancelDelayHide = r.delayHide.clearTimeout),
        e.once("ready", function () {
          r.add(
            Wt({
              name: "progress",
              disable: i.isLive,
              position: "top",
              index: 10,
            })
          ),
            r.add(
              Qt({
                name: "thumbnails",
                disable: !i.thumbnails.url || i.isLive,
                position: "top",
                index: 20,
              })
            ),
            r.add(
              (function (t) {
                return function (e) {
                  return ne(
                    ne({}, t),
                    {},
                    {
                      mounted: function (t) {
                        var r = e.player,
                          n = x(t, '<span class="art-loop-point"></span>'),
                          o = x(t, '<span class="art-loop-point"></span>');
                        e.on("loop", function (e) {
                          e
                            ? (O(t, "display", "block"),
                              O(
                                n,
                                "left",
                                "calc("
                                  .concat((e[0] / r.duration) * 100, "% - ")
                                  .concat(n.clientWidth, "px)")
                              ),
                              O(
                                o,
                                "left",
                                "".concat((e[1] / r.duration) * 100, "%")
                              ))
                            : O(t, "display", "none");
                        });
                      },
                    }
                  );
                };
              })({ name: "loop", disable: !1, position: "top", index: 30 })
            ),
            r.add(
              (function (t) {
                return function (e) {
                  return Mt(
                    Mt({}, t),
                    {},
                    {
                      mounted: function (t) {
                        var r = e.events.proxy,
                          n = e.icons,
                          o = e.i18n,
                          i = e.player,
                          a = x(t, n.play),
                          c = x(t, n.pause);
                        function l() {
                          O(a, "display", "flex"), O(c, "display", "none");
                        }
                        function s() {
                          O(a, "display", "none"), O(c, "display", "flex");
                        }
                        R(a, o.get("Play")),
                          R(c, o.get("Pause")),
                          r(a, "click", function () {
                            i.play = !0;
                          }),
                          r(c, "click", function () {
                            i.pause = !0;
                          }),
                          i.playing ? s() : l(),
                          e.on("video:playing", function () {
                            s();
                          }),
                          e.on("video:pause", function () {
                            l();
                          });
                      },
                    }
                  );
                };
              })({
                name: "playAndPause",
                disable: !1,
                position: "left",
                index: 10,
              })
            ),
            r.add(
              (function (t) {
                return function (e) {
                  return _t(
                    _t({}, t),
                    {},
                    {
                      mounted: function (t) {
                        var r = e.events.proxy,
                          n = e.icons,
                          o = e.player,
                          i = e.i18n,
                          a = !1,
                          c = x(t, n.volume),
                          l = x(t, n.volumeClose),
                          s = x(t, '<div class="art-volume-panel"></div>'),
                          u = x(
                            s,
                            '<div class="art-volume-slider-handle"></div>'
                          );
                        function p(t) {
                          var e = s.getBoundingClientRect().left;
                          return et(t.pageX - e - 6, 0, 54) / 48;
                        }
                        function f() {
                          var t =
                            arguments.length > 0 && void 0 !== arguments[0]
                              ? arguments[0]
                              : 0.7;
                          if (o.muted || 0 === t)
                            O(c, "display", "none"),
                              O(l, "display", "flex"),
                              O(u, "left", "0");
                          else {
                            var e = 48 * t;
                            O(c, "display", "flex"),
                              O(l, "display", "none"),
                              O(u, "left", "".concat(e, "px"));
                          }
                        }
                        R(c, i.get("Mute")),
                          O(l, "display", "none"),
                          e.isMobile && O(s, "display", "none"),
                          f(o.volume),
                          e.on("video:volumechange", function () {
                            f(o.volume);
                          }),
                          r(c, "click", function () {
                            o.muted = !0;
                          }),
                          r(l, "click", function () {
                            o.muted = !1;
                          }),
                          r(s, "click", function (t) {
                            (o.muted = !1), (o.volume = p(t));
                          }),
                          r(u, "mousedown", function () {
                            a = !0;
                          }),
                          r(t, "mousemove", function (t) {
                            a && ((o.muted = !1), (o.volume = p(t)));
                          }),
                          r(document, "mouseup", function () {
                            a && (a = !1);
                          });
                      },
                    }
                  );
                };
              })({ name: "volume", disable: !1, position: "left", index: 20 })
            ),
            r.add(
              (function (t) {
                return function (e) {
                  return Nt(
                    Nt({}, t),
                    {},
                    {
                      mounted: function (t) {
                        function r() {
                          var r = ""
                            .concat(rt(e.player.currentTime), " / ")
                            .concat(rt(e.player.duration));
                          r !== t.innerText && (t.innerText = r);
                        }
                        r(),
                          [
                            "video:loadedmetadata",
                            "video:timeupdate",
                            "video:progress",
                          ].forEach(function (t) {
                            e.on(t, r);
                          });
                      },
                    }
                  );
                };
              })({
                name: "time",
                disable: i.isLive,
                position: "left",
                index: 30,
              })
            ),
            r.add(
              (function (t) {
                return function (e) {
                  var r = e.option.quality,
                    n =
                      r.find(function (t) {
                        return t.default;
                      }) || r[0];
                  return ee(
                    ee({}, t),
                    {},
                    {
                      html: n ? n.name : "",
                      selector: r,
                      onSelect: function (t) {
                        e.player.switchQuality(t.url, t.name);
                      },
                    }
                  );
                };
              })({
                name: "quality",
                disable: 0 === i.quality.length,
                position: "right",
                index: 10,
              })
            ),
            r.add(
              (function (t) {
                return function (e) {
                  return Kt(
                    Kt({}, t),
                    {},
                    {
                      tooltip: e.i18n.get("Screenshot"),
                      mounted: function (t) {
                        var r = e.events.proxy,
                          n = e.icons,
                          o = e.player;
                        x(t, n.screenshot),
                          r(t, "click", function () {
                            o.screenshot();
                          });
                      },
                    }
                  );
                };
              })({
                name: "screenshot",
                disable: !i.screenshot,
                position: "right",
                index: 20,
              })
            ),
            r.add(
              (function (t) {
                return function (e) {
                  return Vt(
                    Vt({}, t),
                    {},
                    {
                      tooltip: e.i18n.get("Hide subtitle"),
                      mounted: function (t) {
                        var r = e.events.proxy,
                          n = e.icons,
                          o = e.i18n,
                          i = e.subtitle;
                        x(t, n.subtitle),
                          r(t, "click", function () {
                            i.toggle = !0;
                          }),
                          e.on("subtitle", function (e) {
                            R(t, o.get(e ? "Hide subtitle" : "Show subtitle"));
                          });
                      },
                    }
                  );
                };
              })({
                name: "subtitle",
                disable: !i.subtitle.url,
                position: "right",
                index: 30,
              })
            ),
            r.add(
              (function (t) {
                return function (e) {
                  return Yt(
                    Yt({}, t),
                    {},
                    {
                      tooltip: e.i18n.get("Show setting"),
                      mounted: function (t) {
                        var r = e.events.proxy,
                          n = e.icons,
                          o = e.i18n,
                          i = e.setting;
                        x(t, n.setting),
                          r(t, "click", function () {
                            i.toggle = !0;
                          }),
                          e.on("setting", function (e) {
                            R(t, o.get(e ? "Hide setting" : "Show setting"));
                          });
                      },
                    }
                  );
                };
              })({
                name: "setting",
                disable: !i.setting,
                position: "right",
                index: 40,
              })
            ),
            r.add(
              (function (t) {
                return function (e) {
                  return Ct(
                    Ct({}, t),
                    {},
                    {
                      tooltip: e.i18n.get("PIP mode"),
                      mounted: function (t) {
                        var r = e.events.proxy,
                          n = e.icons,
                          o = e.i18n,
                          i = e.player;
                        x(t, n.pip),
                          r(t, "click", function () {
                            i.pipToggle = !0;
                          }),
                          e.on("pip", function (e) {
                            R(t, o.get(e ? "Exit PIP mode" : "PIP mode"));
                          });
                      },
                    }
                  );
                };
              })({ name: "pip", disable: !i.pip, position: "right", index: 50 })
            ),
            r.add(
              (function (t) {
                return function (e) {
                  return zt(
                    zt({}, t),
                    {},
                    {
                      tooltip: e.i18n.get("Web fullscreen"),
                      mounted: function (t) {
                        var r = e.events.proxy,
                          n = e.icons,
                          o = e.i18n,
                          i = e.player;
                        x(t, n.fullscreenWeb),
                          r(t, "click", function () {
                            i.fullscreenWebToggle = !0;
                          }),
                          e.on("fullscreenWeb", function (e) {
                            R(
                              t,
                              o.get(
                                e ? "Exit web fullscreen" : "Web fullscreen"
                              )
                            );
                          });
                      },
                    }
                  );
                };
              })({
                name: "fullscreenWeb",
                disable: !i.fullscreenWeb,
                position: "right",
                index: 60,
              })
            ),
            r.add(
              (function (t) {
                return function (e) {
                  return $t(
                    $t({}, t),
                    {},
                    {
                      tooltip: e.i18n.get("Fullscreen"),
                      mounted: function (t) {
                        var r = e.events.proxy,
                          n = e.icons,
                          o = e.i18n,
                          i = e.player;
                        x(t, n.fullscreen),
                          r(t, "click", function () {
                            i.fullscreenToggle = !0;
                          }),
                          e.on("fullscreen", function (e) {
                            R(t, o.get(e ? "Exit fullscreen" : "Fullscreen"));
                          });
                      },
                    }
                  );
                };
              })({
                name: "fullscreen",
                disable: !i.fullscreen,
                position: "right",
                index: 70,
              })
            ),
            i.controls.forEach(function (t) {
              r.add(t);
            });
        }),
        r
      );
    }
    return (
      r(o, [
        {
          key: "add",
          value: function (t) {
            var e = "function" == typeof t ? t(this.art) : t,
              r = this.art.template,
              n = r.$progress,
              i = r.$controlsLeft,
              a = r.$controlsRight;
            switch (e.position) {
              case "top":
                this.$parent = n;
                break;
              case "left":
                this.$parent = i;
                break;
              case "right":
                this.$parent = a;
                break;
              default:
                L(
                  !1,
                  "Control option.position must one of 'top', 'left', 'right'"
                );
            }
            Rt(s(o.prototype), "add", this).call(this, e);
          },
        },
      ]),
      o
    );
  })(Et);
  function ae(t, e) {
    var r = Object.keys(t);
    if (Object.getOwnPropertySymbols) {
      var n = Object.getOwnPropertySymbols(t);
      e &&
        (n = n.filter(function (e) {
          return Object.getOwnPropertyDescriptor(t, e).enumerable;
        })),
        r.push.apply(r, n);
    }
    return r;
  }
  function ce(t) {
    for (var e = 1; e < arguments.length; e++) {
      var r = null != arguments[e] ? arguments[e] : {};
      e % 2
        ? ae(Object(r), !0).forEach(function (e) {
            it(t, e, r[e]);
          })
        : Object.getOwnPropertyDescriptors
        ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(r))
        : ae(Object(r)).forEach(function (e) {
            Object.defineProperty(t, e, Object.getOwnPropertyDescriptor(r, e));
          });
    }
    return t;
  }
  function le(t, e) {
    var r = Object.keys(t);
    if (Object.getOwnPropertySymbols) {
      var n = Object.getOwnPropertySymbols(t);
      e &&
        (n = n.filter(function (e) {
          return Object.getOwnPropertyDescriptor(t, e).enumerable;
        })),
        r.push.apply(r, n);
    }
    return r;
  }
  function se(t) {
    for (var e = 1; e < arguments.length; e++) {
      var r = null != arguments[e] ? arguments[e] : {};
      e % 2
        ? le(Object(r), !0).forEach(function (e) {
            it(t, e, r[e]);
          })
        : Object.getOwnPropertyDescriptors
        ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(r))
        : le(Object(r)).forEach(function (e) {
            Object.defineProperty(t, e, Object.getOwnPropertyDescriptor(r, e));
          });
    }
    return t;
  }
  function ue(t, e) {
    var r = Object.keys(t);
    if (Object.getOwnPropertySymbols) {
      var n = Object.getOwnPropertySymbols(t);
      e &&
        (n = n.filter(function (e) {
          return Object.getOwnPropertyDescriptor(t, e).enumerable;
        })),
        r.push.apply(r, n);
    }
    return r;
  }
  function pe(t) {
    for (var e = 1; e < arguments.length; e++) {
      var r = null != arguments[e] ? arguments[e] : {};
      e % 2
        ? ue(Object(r), !0).forEach(function (e) {
            it(t, e, r[e]);
          })
        : Object.getOwnPropertyDescriptors
        ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(r))
        : ue(Object(r)).forEach(function (e) {
            Object.defineProperty(t, e, Object.getOwnPropertyDescriptor(r, e));
          });
    }
    return t;
  }
  function fe(t, e) {
    var r = Object.keys(t);
    if (Object.getOwnPropertySymbols) {
      var n = Object.getOwnPropertySymbols(t);
      e &&
        (n = n.filter(function (e) {
          return Object.getOwnPropertyDescriptor(t, e).enumerable;
        })),
        r.push.apply(r, n);
    }
    return r;
  }
  function de(t) {
    for (var e = 1; e < arguments.length; e++) {
      var r = null != arguments[e] ? arguments[e] : {};
      e % 2
        ? fe(Object(r), !0).forEach(function (e) {
            it(t, e, r[e]);
          })
        : Object.getOwnPropertyDescriptors
        ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(r))
        : fe(Object(r)).forEach(function (e) {
            Object.defineProperty(t, e, Object.getOwnPropertyDescriptor(r, e));
          });
    }
    return t;
  }
  function he(t, e) {
    var r = Object.keys(t);
    if (Object.getOwnPropertySymbols) {
      var n = Object.getOwnPropertySymbols(t);
      e &&
        (n = n.filter(function (e) {
          return Object.getOwnPropertyDescriptor(t, e).enumerable;
        })),
        r.push.apply(r, n);
    }
    return r;
  }
  function ye(t) {
    for (var e = 1; e < arguments.length; e++) {
      var r = null != arguments[e] ? arguments[e] : {};
      e % 2
        ? he(Object(r), !0).forEach(function (e) {
            it(t, e, r[e]);
          })
        : Object.getOwnPropertyDescriptors
        ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(r))
        : he(Object(r)).forEach(function (e) {
            Object.defineProperty(t, e, Object.getOwnPropertyDescriptor(r, e));
          });
    }
    return t;
  }
  function be(t, e) {
    var r = Object.keys(t);
    if (Object.getOwnPropertySymbols) {
      var n = Object.getOwnPropertySymbols(t);
      e &&
        (n = n.filter(function (e) {
          return Object.getOwnPropertyDescriptor(t, e).enumerable;
        })),
        r.push.apply(r, n);
    }
    return r;
  }
  function ve(t) {
    for (var e = 1; e < arguments.length; e++) {
      var r = null != arguments[e] ? arguments[e] : {};
      e % 2
        ? be(Object(r), !0).forEach(function (e) {
            it(t, e, r[e]);
          })
        : Object.getOwnPropertyDescriptors
        ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(r))
        : be(Object(r)).forEach(function (e) {
            Object.defineProperty(t, e, Object.getOwnPropertyDescriptor(r, e));
          });
    }
    return t;
  }
  function ge(t) {
    var e = (function () {
      if ("undefined" == typeof Reflect || !Reflect.construct) return !1;
      if (Reflect.construct.sham) return !1;
      if ("function" == typeof Proxy) return !0;
      try {
        return (
          Date.prototype.toString.call(
            Reflect.construct(Date, [], function () {})
          ),
          !0
        );
      } catch (t) {
        return !1;
      }
    })();
    return function () {
      var r,
        n = s(t);
      if (e) {
        var o = s(this).constructor;
        r = Reflect.construct(n, arguments, o);
      } else r = n.apply(this, arguments);
      return l(this, r);
    };
  }
  var me = (function (e) {
    a(n, e);
    var r = ge(n);
    function n(e) {
      var o;
      t(this, n), ((o = r.call(this, e)).name = "contextmenu");
      var i = e.option,
        a = e.template,
        c = a.$player,
        l = a.$contextmenu,
        s = e.events.proxy;
      return (
        (o.$parent = l),
        e.once("ready", function () {
          o.add(
            (function (t) {
              return function (e) {
                var r = e.i18n,
                  n = e.player;
                return ce(
                  ce({}, t),
                  {},
                  {
                    html: ""
                      .concat(
                        r.get("Play speed"),
                        ':<span data-rate="0.5">0.5</span><span data-rate="0.75">0.75</span><span data-rate="1.0" class="art-current">'
                      )
                      .concat(
                        r.get("Normal"),
                        '</span><span data-rate="1.25">1.25</span><span data-rate="1.5">1.5</span><span data-rate="2.0">2.0</span>'
                      ),
                    click: function (t, e) {
                      var r = e.target.dataset.rate;
                      r && ((n.playbackRate = Number(r)), (t.show = !1));
                    },
                    mounted: function (t) {
                      e.on("playbackRate", function (e) {
                        var r = v("span", t).find(function (t) {
                          return Number(t.dataset.rate) === e;
                        });
                        r && S(r, "art-current");
                      });
                    },
                  }
                );
              };
            })({ disable: !i.playbackRate, name: "playbackRate", index: 10 })
          ),
            o.add(
              (function (t) {
                return function (e) {
                  var r = e.i18n,
                    n = e.player;
                  return se(
                    se({}, t),
                    {},
                    {
                      html: ""
                        .concat(
                          r.get("Aspect ratio"),
                          ':<span data-ratio="default" class="art-current">'
                        )
                        .concat(
                          r.get("Default"),
                          '</span><span data-ratio="4:3">4:3</span><span data-ratio="16:9">16:9</span>'
                        ),
                      click: function (t, e) {
                        var r = e.target.dataset.ratio;
                        r && ((n.aspectRatio = r), (t.show = !1));
                      },
                      mounted: function (t) {
                        e.on("aspectRatio", function (e) {
                          var r = v("span", t).find(function (t) {
                            return t.dataset.ratio === e;
                          });
                          r && S(r, "art-current");
                        });
                      },
                    }
                  );
                };
              })({ disable: !i.aspectRatio, name: "aspectRatio", index: 20 })
            ),
            o.add(
              (function (t) {
                return function (e) {
                  return pe(
                    pe({}, t),
                    {},
                    {
                      html: e.i18n.get("Video info"),
                      click: function (t) {
                        (e.info.show = !0), (t.show = !1);
                      },
                    }
                  );
                };
              })({ disable: !1, name: "info", index: 30 })
            ),
            o.add(
              (function (t) {
                return de(
                  de({}, t),
                  {},
                  {
                    html:
                      '<a href="https://artplayer.org" target="_blank">ArtPlayer 3.5.26</a>',
                  }
                );
              })({ disable: !1, name: "version", index: 40 })
            ),
            o.add(
              (function (t) {
                return function (e) {
                  var r = e.i18n,
                    n = e.player;
                  return ye(
                    ye({}, t),
                    {},
                    {
                      html: r.get("Light Off"),
                      click: function (t) {
                        (n.light = !n.light), (t.show = !1);
                      },
                      mounted: function (t) {
                        e.on("light", function (e) {
                          t.innerText = r.get(e ? "Light On" : "Light Off");
                        });
                      },
                    }
                  );
                };
              })({ disable: !i.light, name: "light", index: 50 })
            ),
            o.add(
              (function (t) {
                return function (e) {
                  return ve(
                    ve({}, t),
                    {},
                    {
                      html: e.i18n.get("Close"),
                      click: function (t) {
                        t.show = !1;
                      },
                    }
                  );
                };
              })({ disable: !1, name: "close", index: 60 })
            ),
            i.contextmenu.forEach(function (t) {
              o.add(t);
            }),
            s(c, "contextmenu", function (t) {
              t.preventDefault(), (o.show = !0);
              var e = t.clientX,
                r = t.clientY,
                n = c.getBoundingClientRect(),
                i = n.height,
                a = n.width,
                s = n.left,
                u = n.top,
                p = l.getBoundingClientRect(),
                f = p.height,
                d = p.width,
                h = e - s,
                y = r - u;
              e + d > s + a && (h = a - d),
                r + f > u + i && (y = i - f),
                k(l, { top: "".concat(y, "px"), left: "".concat(h, "px") });
            }),
            s(c, "click", function (t) {
              D(t, l) || (o.show = !1);
            }),
            e.on("blur", function () {
              o.show = !1;
            });
        }),
        o
      );
    }
    return n;
  })(Et);
  function we(t) {
    var e = (function () {
      if ("undefined" == typeof Reflect || !Reflect.construct) return !1;
      if (Reflect.construct.sham) return !1;
      if ("function" == typeof Proxy) return !0;
      try {
        return (
          Date.prototype.toString.call(
            Reflect.construct(Date, [], function () {})
          ),
          !0
        );
      } catch (t) {
        return !1;
      }
    })();
    return function () {
      var r,
        n = s(t);
      if (e) {
        var o = s(this).constructor;
        r = Reflect.construct(n, arguments, o);
      } else r = n.apply(this, arguments);
      return l(this, r);
    };
  }
  var xe = (function (e) {
    a(n, e);
    var r = we(n);
    function n(e) {
      var o;
      t(this, n), ((o = r.call(this, e)).name = "info");
      var i = e.template,
        a = i.$infoPanel,
        c = i.$infoClose,
        l = i.$video;
      (0, e.events.proxy)(c, "click", function () {
        o.show = !1;
      });
      var s = null,
        u = v("[data-video]", a);
      function p() {
        u.forEach(function (t) {
          var e = l[t.dataset.video];
          t.innerText = "number" == typeof e ? e.toFixed(2) : e;
        }),
          (s = setTimeout(function () {
            p();
          }, 1e3));
      }
      return (
        e.on("destroy", function () {
          clearTimeout(s);
        }),
        e.on("info", function (t) {
          clearTimeout(s), t && p();
        }),
        o
      );
    }
    return n;
  })(Et);
  function Oe(t) {
    var e = (function () {
      if ("undefined" == typeof Reflect || !Reflect.construct) return !1;
      if (Reflect.construct.sham) return !1;
      if ("function" == typeof Proxy) return !0;
      try {
        return (
          Date.prototype.toString.call(
            Reflect.construct(Date, [], function () {})
          ),
          !0
        );
      } catch (t) {
        return !1;
      }
    })();
    return function () {
      var r,
        n = s(t);
      if (e) {
        var o = s(this).constructor;
        r = Reflect.construct(n, arguments, o);
      } else r = n.apply(this, arguments);
      return l(this, r);
    };
  }
  var ke = (function (e) {
    a(o, e);
    var n = Oe(o);
    function o(e) {
      var r;
      t(this, o), ((r = n.call(this, e)).name = "subtitle");
      var i = e.option.subtitle,
        a = e.template.$subtitle;
      return (
        k(a, i.style),
        i.url && r.init(i.url),
        i.bilingual && g(a, "art-bilingual"),
        r
      );
    }
    return (
      r(o, [
        {
          key: "style",
          value: function (t, e) {
            var r = this.art.template.$subtitle;
            return "object" === c(t) ? k(r, t) : O(r, t, e);
          },
        },
        {
          key: "update",
          value: function () {
            var t = this.art.template.$subtitle;
            (t.innerHTML = ""),
              this.activeCue &&
                ((t.innerHTML = this.activeCue.text
                  .split(/\r?\n/)
                  .map(function (t) {
                    return "<p>".concat(nt(t), "</p>");
                  })
                  .join("")),
                this.art.emit("subtitleUpdate", this.activeCue.text));
          },
        },
        {
          key: "switch",
          value: function (t) {
            var e = this,
              r =
                arguments.length > 1 && void 0 !== arguments[1]
                  ? arguments[1]
                  : {},
              n = this.art,
              o = n.i18n,
              i = n.notice;
            return this.init(t, r).then(function (t) {
              return (
                r.name &&
                  (i.show = ""
                    .concat(o.get("Switch subtitle"), ": ")
                    .concat(r.name)),
                e.art.emit("subtitleSwitch", t),
                t
              );
            });
          },
        },
        {
          key: "init",
          value: function (t) {
            var e = this,
              r =
                arguments.length > 1 && void 0 !== arguments[1]
                  ? arguments[1]
                  : {},
              n = this.art,
              o = n.notice,
              i = n.events.proxy,
              a = n.option.subtitle,
              c = n.template,
              l = c.$subtitle,
              s = c.$video,
              u = c.$track;
            if (!u) {
              var p = document.createElement("track");
              (p.default = !0),
                (p.kind = "metadata"),
                s.appendChild(p),
                (this.art.template.$track = p),
                i(this.textTrack, "cuechange", this.update.bind(this));
            }
            return fetch(t)
              .then(function (t) {
                return t.arrayBuffer();
              })
              .then(function (n) {
                var o = new TextDecoder(r.encoding || a.encoding).decode(n);
                switch ((e.art.emit("subtitleLoad", t), r.ext || H(t))) {
                  case "srt":
                    return q(M(o));
                  case "ass":
                    return q(F(o));
                  case "vtt":
                    return q(o);
                  default:
                    return t;
                }
              })
              .then(function (t) {
                return (
                  (l.innerHTML = ""),
                  e.url === t ||
                    (URL.revokeObjectURL(e.url),
                    (e.art.template.$track.src = t)),
                  t
                );
              })
              .catch(function (t) {
                throw ((o.show = t), t);
              });
          },
        },
        {
          key: "url",
          get: function () {
            return this.art.template.$track.src;
          },
        },
        {
          key: "textTrack",
          get: function () {
            return this.art.template.$video.textTracks[0];
          },
        },
        {
          key: "activeCue",
          get: function () {
            return this.textTrack.activeCues[0];
          },
        },
        {
          key: "bilingual",
          get: function () {
            return w(this.art.template.$subtitle, "art-bilingual");
          },
          set: function (t) {
            var e = this.art.template.$subtitle;
            t ? g(e, "art-bilingual") : m(e, "art-bilingual");
          },
        },
      ]),
      o
    );
  })(Et);
  var je = (function () {
      function e(r) {
        var n = this;
        t(this, e),
          (this.destroyEvents = []),
          (this.proxy = this.proxy.bind(this)),
          (this.hover = this.hover.bind(this)),
          (this.loadImg = this.loadImg.bind(this)),
          r.whitelist.state &&
            r.once("ready", function () {
              !(function (t, e) {
                var r = t.controls,
                  n = t.template.$player;
                e.proxy(document, ["click", "contextmenu"], function (e) {
                  D(e, n)
                    ? ((t.isFocus = !0), t.emit("focus"))
                    : ((t.isFocus = !1), t.emit("blur"));
                }),
                  t.on("blur", function () {
                    r.delayHide();
                  });
              })(r, n),
                (function (t, e) {
                  var r = t.controls,
                    n = t.template.$player;
                  e.hover(
                    n,
                    function () {
                      g(n, "art-hover"), t.emit("hover", !0);
                    },
                    function () {
                      m(n, "art-hover"), t.emit("hover");
                    }
                  ),
                    t.on("hover", function (t) {
                      t || r.delayHide();
                    });
                })(r, n),
                (function (t, e) {
                  var r = t.template,
                    n = r.$player,
                    o = r.$video,
                    i = t.player,
                    a = t.controls;
                  e.proxy(n, "mousemove", function (e) {
                    t.emit("mousemove", e);
                  }),
                    t.on("mousemove", function (t) {
                      a.cancelDelayHide(),
                        m(n, "art-hide-cursor"),
                        (a.show = !0),
                        i.pip || t.target !== o || a.delayHide();
                    });
                })(r, n),
                (function (t, e) {
                  var r = t.option,
                    n = t.player,
                    o = tt(function () {
                      n.normalSize && (n.autoSize = r.autoSize),
                        (n.aspectRatioReset = !0),
                        t.emit("resize");
                    }, 500);
                  e.proxy(window, ["orientationchange", "resize"], function () {
                    o();
                  });
                })(r, n),
                (function (t, e) {
                  if (t.isMobile && !t.option.isLive) {
                    var r = t.player,
                      n = t.notice,
                      o = t.template.$video,
                      i = !1,
                      a = 0,
                      c = 0;
                    e.proxy(o, "touchstart", function (t) {
                      1 === t.touches.length &&
                        ((i = !0), (a = t.touches[0].clientX));
                    }),
                      e.proxy(document, "touchmove", function (t) {
                        if (1 === t.touches.length && i) {
                          var e = et(
                            (t.touches[0].clientX - a) / o.clientWidth,
                            -1,
                            1
                          );
                          (c = et(r.currentTime + 60 * e, 0, r.duration)),
                            (n.show = ""
                              .concat(rt(c), " / ")
                              .concat(rt(r.duration)));
                        }
                      }),
                      e.proxy(document, "touchend", function () {
                        i && c && (r.seek = c), (i = !1), (a = 0), (c = 0);
                      });
                  }
                })(r, n),
                (function (t, e) {
                  var r = t.player,
                    n = t.option.autoMini,
                    o = t.template.$container,
                    i = K(function () {
                      t.emit("view", E(o));
                    }, 200);
                  e.proxy(window, "scroll", function () {
                    i();
                  }),
                    t.on("view", function (t) {
                      n && (r.mini = !t);
                    });
                })(r, n);
            });
      }
      return (
        r(e, [
          {
            key: "proxy",
            value: function (t, e, r) {
              var n = this,
                o =
                  arguments.length > 3 && void 0 !== arguments[3]
                    ? arguments[3]
                    : {};
              if (Array.isArray(e))
                return e.map(function (e) {
                  return n.proxy(t, e, r, o);
                });
              t.addEventListener(e, r, o);
              var i = function () {
                return t.removeEventListener(e, r, o);
              };
              return this.destroyEvents.push(i), i;
            },
          },
          {
            key: "hover",
            value: function (t, e, r) {
              e && this.proxy(t, "mouseenter", e),
                r && this.proxy(t, "mouseleave", r);
            },
          },
          {
            key: "loadImg",
            value: function (t) {
              var e = this;
              return new Promise(function (r, n) {
                var o;
                if (t instanceof HTMLImageElement) o = t;
                else {
                  if ("string" != typeof t)
                    return n(new C("Unable to get Image"));
                  (o = new Image()).src = t;
                }
                return (
                  o.complete ||
                    (e.proxy(o, "load", function () {
                      return r(o);
                    }),
                    e.proxy(o, "error", function () {
                      return n(new C("Failed to load Image: ".concat(o.src)));
                    })),
                  r(o)
                );
              });
            },
          },
          {
            key: "destroy",
            value: function () {
              this.destroyEvents.forEach(function (t) {
                return t();
              });
            },
          },
        ]),
        e
      );
    })(),
    Pe = (function () {
      function e(r) {
        var n = this;
        t(this, e), (this.keys = {});
        var o = r.option,
          i = r.player,
          a = r.events.proxy;
        o.hotkey &&
          r.once("ready", function () {
            n.add(27, function () {
              i.fullscreenWeb && (i.fullscreenWeb = !1);
            }),
              n.add(32, function () {
                i.toggle = !0;
              }),
              n.add(37, function () {
                i.backward = 5;
              }),
              n.add(38, function () {
                i.volume += 0.1;
              }),
              n.add(39, function () {
                i.forward = 5;
              }),
              n.add(40, function () {
                i.volume -= 0.1;
              }),
              a(window, "keydown", function (t) {
                if (r.isFocus) {
                  var e = document.activeElement.tagName.toUpperCase(),
                    o = document.activeElement.getAttribute("contenteditable");
                  if (
                    "INPUT" !== e &&
                    "TEXTAREA" !== e &&
                    "" !== o &&
                    "true" !== o
                  ) {
                    var i = n.keys[t.keyCode];
                    i &&
                      (t.preventDefault(),
                      i.forEach(function (t) {
                        return t.call(r);
                      }),
                      r.emit("hotkey", t));
                  }
                }
              });
          });
      }
      return (
        r(e, [
          {
            key: "add",
            value: function (t, e) {
              this.keys[t] ? this.keys[t].push(e) : (this.keys[t] = [e]);
            },
          },
        ]),
        e
      );
    })();
  function Se(t) {
    var e = (function () {
      if ("undefined" == typeof Reflect || !Reflect.construct) return !1;
      if (Reflect.construct.sham) return !1;
      if ("function" == typeof Proxy) return !0;
      try {
        return (
          Date.prototype.toString.call(
            Reflect.construct(Date, [], function () {})
          ),
          !0
        );
      } catch (t) {
        return !1;
      }
    })();
    return function () {
      var r,
        n = s(t);
      if (e) {
        var o = s(this).constructor;
        r = Reflect.construct(n, arguments, o);
      } else r = n.apply(this, arguments);
      return l(this, r);
    };
  }
  var Re = (function (e) {
    a(n, e);
    var r = Se(n);
    function n(e) {
      var o;
      return (
        t(this, n),
        ((o = r.call(this, e)).name = "layer"),
        (o.$parent = e.template.$layer),
        e.once("ready", function () {
          e.option.layers.forEach(function (t) {
            o.add(t);
          });
        }),
        o
      );
    }
    return n;
  })(Et);
  function Ee(t) {
    var e = (function () {
      if ("undefined" == typeof Reflect || !Reflect.construct) return !1;
      if (Reflect.construct.sham) return !1;
      if ("function" == typeof Proxy) return !0;
      try {
        return (
          Date.prototype.toString.call(
            Reflect.construct(Date, [], function () {})
          ),
          !0
        );
      } catch (t) {
        return !1;
      }
    })();
    return function () {
      var r,
        n = s(t);
      if (e) {
        var o = s(this).constructor;
        r = Reflect.construct(n, arguments, o);
      } else r = n.apply(this, arguments);
      return l(this, r);
    };
  }
  var De = (function (e) {
      a(n, e);
      var r = Ee(n);
      function n(e) {
        var o;
        return (
          t(this, n),
          ((o = r.call(this, e)).name = "loading"),
          x(e.template.$loading, e.icons.loading),
          o
        );
      }
      return n;
    })(Et),
    $e = (function () {
      function e(r) {
        t(this, e), (this.art = r), (this.time = 2e3), (this.timer = null);
      }
      return (
        r(e, [
          {
            key: "show",
            set: function (t) {
              var e = this.art.template,
                r = e.$player,
                n = e.$noticeInner;
              (n.innerText = t instanceof Error ? t.message.trim() : t),
                g(r, "art-notice-show"),
                clearTimeout(this.timer),
                (this.timer = setTimeout(function () {
                  (n.innerText = ""), m(r, "art-notice-show");
                }, this.time));
            },
          },
        ]),
        e
      );
    })();
  function Te(t) {
    var e = (function () {
      if ("undefined" == typeof Reflect || !Reflect.construct) return !1;
      if (Reflect.construct.sham) return !1;
      if ("function" == typeof Proxy) return !0;
      try {
        return (
          Date.prototype.toString.call(
            Reflect.construct(Date, [], function () {})
          ),
          !0
        );
      } catch (t) {
        return !1;
      }
    })();
    return function () {
      var r,
        n = s(t);
      if (e) {
        var o = s(this).constructor;
        r = Reflect.construct(n, arguments, o);
      } else r = n.apply(this, arguments);
      return l(this, r);
    };
  }
  var ze = (function (e) {
    a(n, e);
    var r = Te(n);
    function n(e) {
      var o;
      return (
        t(this, n),
        ((o = r.call(this, e)).name = "mask"),
        x(e.template.$state, e.icons.state),
        o
      );
    }
    return n;
  })(Et);
  function Ae(t, e) {
    var r = Object.keys(t);
    if (Object.getOwnPropertySymbols) {
      var n = Object.getOwnPropertySymbols(t);
      e &&
        (n = n.filter(function (e) {
          return Object.getOwnPropertyDescriptor(t, e).enumerable;
        })),
        r.push.apply(r, n);
    }
    return r;
  }
  var Ce = function e(r) {
    var n = this;
    t(this, e);
    var o = (function (t) {
      for (var e = 1; e < arguments.length; e++) {
        var r = null != arguments[e] ? arguments[e] : {};
        e % 2
          ? Ae(Object(r), !0).forEach(function (e) {
              it(t, e, r[e]);
            })
          : Object.getOwnPropertyDescriptors
          ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(r))
          : Ae(Object(r)).forEach(function (e) {
              Object.defineProperty(
                t,
                e,
                Object.getOwnPropertyDescriptor(r, e)
              );
            });
      }
      return t;
    })(
      {
        loading:
          '<svg xmlns="http://www.w3.org/2000/svg" width="50px" height="50px" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid" class="uil-default"><rect x="0" y="0" width="100" height="100" fill="none" class="bk"/><rect x="47" y="40" width="6" height="20" rx="5" ry="5" fill="#ffffff" transform="rotate(0 50 50) translate(0 -30)"><animate attributeName="opacity" from="1" to="0" dur="1s" begin="-1s" repeatCount="indefinite"/></rect><rect x="47" y="40" width="6" height="20" rx="5" ry="5" fill="#ffffff" transform="rotate(30 50 50) translate(0 -30)"><animate attributeName="opacity" from="1" to="0" dur="1s" begin="-0.9166666666666666s" repeatCount="indefinite"/></rect><rect x="47" y="40" width="6" height="20" rx="5" ry="5" fill="#ffffff" transform="rotate(60 50 50) translate(0 -30)"><animate attributeName="opacity" from="1" to="0" dur="1s" begin="-0.8333333333333334s" repeatCount="indefinite"/></rect><rect x="47" y="40" width="6" height="20" rx="5" ry="5" fill="#ffffff" transform="rotate(90 50 50) translate(0 -30)"><animate attributeName="opacity" from="1" to="0" dur="1s" begin="-0.75s" repeatCount="indefinite"/></rect><rect x="47" y="40" width="6" height="20" rx="5" ry="5" fill="#ffffff" transform="rotate(120 50 50) translate(0 -30)"><animate attributeName="opacity" from="1" to="0" dur="1s" begin="-0.6666666666666666s" repeatCount="indefinite"/></rect><rect x="47" y="40" width="6" height="20" rx="5" ry="5" fill="#ffffff" transform="rotate(150 50 50) translate(0 -30)"><animate attributeName="opacity" from="1" to="0" dur="1s" begin="-0.5833333333333334s" repeatCount="indefinite"/></rect><rect x="47" y="40" width="6" height="20" rx="5" ry="5" fill="#ffffff" transform="rotate(180 50 50) translate(0 -30)"><animate attributeName="opacity" from="1" to="0" dur="1s" begin="-0.5s" repeatCount="indefinite"/></rect><rect x="47" y="40" width="6" height="20" rx="5" ry="5" fill="#ffffff" transform="rotate(210 50 50) translate(0 -30)"><animate attributeName="opacity" from="1" to="0" dur="1s" begin="-0.4166666666666667s" repeatCount="indefinite"/></rect><rect x="47" y="40" width="6" height="20" rx="5" ry="5" fill="#ffffff" transform="rotate(240 50 50) translate(0 -30)"><animate attributeName="opacity" from="1" to="0" dur="1s" begin="-0.3333333333333333s" repeatCount="indefinite"/></rect><rect x="47" y="40" width="6" height="20" rx="5" ry="5" fill="#ffffff" transform="rotate(270 50 50) translate(0 -30)"><animate attributeName="opacity" from="1" to="0" dur="1s" begin="-0.25s" repeatCount="indefinite"/></rect><rect x="47" y="40" width="6" height="20" rx="5" ry="5" fill="#ffffff" transform="rotate(300 50 50) translate(0 -30)"><animate attributeName="opacity" from="1" to="0" dur="1s" begin="-0.16666666666666666s" repeatCount="indefinite"/></rect><rect x="47" y="40" width="6" height="20" rx="5" ry="5" fill="#ffffff" transform="rotate(330 50 50) translate(0 -30)"><animate attributeName="opacity" from="1" to="0" dur="1s" begin="-0.08333333333333333s" repeatCount="indefinite"/></rect></svg>',
        state:
          '<svg xmlns="http://www.w3.org/2000/svg" height="60" width="60" style="filter: drop-shadow(0px 1px 1px black);" viewBox="0 0 24 24"><path d="M20,2H4C1.8,2,0,3.8,0,6v12c0,2.2,1.8,4,4,4h16c2.2,0,4-1.8,4-4V6C24,3.8,22.2,2,20,2z M15.6,12.8L10.5,16 C9.9,16.5,9,16,9,15.2V8.8C9,8,9.9,7.5,10.5,8l5.1,3.2C16.3,11.5,16.3,12.5,15.6,12.8z"/></svg>',
        play:
          '<svg xmlns="http://www.w3.org/2000/svg" height="22" width="22" viewBox="0 0 22 22"><path d="M17.982 9.275L8.06 3.27A2.013 2.013 0 0 0 5 4.994v12.011a2.017 2.017 0 0 0 3.06 1.725l9.922-6.005a2.017 2.017 0 0 0 0-3.45z"></path></svg>',
        pause:
          '<svg xmlns="http://www.w3.org/2000/svg" height="22" width="22" viewBox="0 0 22 22"><path d="M7 3a2 2 0 0 0-2 2v12a2 2 0 1 0 4 0V5a2 2 0 0 0-2-2zM15 3a2 2 0 0 0-2 2v12a2 2 0 1 0 4 0V5a2 2 0 0 0-2-2z"></path></svg>',
        volume:
          '<svg xmlns="http://www.w3.org/2000/svg" height="22" width="22" viewBox="0 0 22 22"><path d="M10.188 4.65L6 8H5a2 2 0 0 0-2 2v2a2 2 0 0 0 2 2h1l4.188 3.35a.5.5 0 0 0 .812-.39V5.04a.498.498 0 0 0-.812-.39zM14.446 3.778a1 1 0 0 0-.862 1.804 6.002 6.002 0 0 1-.007 10.838 1 1 0 0 0 .86 1.806A8.001 8.001 0 0 0 19 11a8.001 8.001 0 0 0-4.554-7.222z"></path><path d="M15 11a3.998 3.998 0 0 0-2-3.465v6.93A3.998 3.998 0 0 0 15 11z"></path></svg>',
        volumeClose:
          '<svg xmlns="http://www.w3.org/2000/svg" height="22" width="22" viewBox="0 0 22 22"><path d="M15 11a3.998 3.998 0 0 0-2-3.465v2.636l1.865 1.865A4.02 4.02 0 0 0 15 11z"></path><path d="M13.583 5.583A5.998 5.998 0 0 1 17 11a6 6 0 0 1-.585 2.587l1.477 1.477a8.001 8.001 0 0 0-3.446-11.286 1 1 0 0 0-.863 1.805zM18.778 18.778l-2.121-2.121-1.414-1.414-1.415-1.415L13 13l-2-2-3.889-3.889-3.889-3.889a.999.999 0 1 0-1.414 1.414L5.172 8H5a2 2 0 0 0-2 2v2a2 2 0 0 0 2 2h1l4.188 3.35a.5.5 0 0 0 .812-.39v-3.131l2.587 2.587-.01.005a1 1 0 0 0 .86 1.806c.215-.102.424-.214.627-.333l2.3 2.3a1.001 1.001 0 0 0 1.414-1.416zM11 5.04a.5.5 0 0 0-.813-.39L8.682 5.854 11 8.172V5.04z"></path></svg>',
        subtitle:
          '<svg xmlns="http://www.w3.org/2000/svg" height="22" width="22" viewBox="0 0 48 48"><path d="M0 0h48v48H0z" fill="none"/><path d="M40 8H8c-2.21 0-4 1.79-4 4v24c0 2.21 1.79 4 4 4h32c2.21 0 4-1.79 4-4V12c0-2.21-1.79-4-4-4zM8 24h8v4H8v-4zm20 12H8v-4h20v4zm12 0h-8v-4h8v4zm0-8H20v-4h20v4z"/></svg>',
        screenshot:
          '<svg xmlns="http://www.w3.org/2000/svg" height="22" width="22" viewBox="0 0 50 50">\t<path d="M 19.402344 6 C 17.019531 6 14.96875 7.679688 14.5 10.011719 L 14.097656 12 L 9 12 C 6.238281 12 4 14.238281 4 17 L 4 38 C 4 40.761719 6.238281 43 9 43 L 41 43 C 43.761719 43 46 40.761719 46 38 L 46 17 C 46 14.238281 43.761719 12 41 12 L 35.902344 12 L 35.5 10.011719 C 35.03125 7.679688 32.980469 6 30.597656 6 Z M 25 17 C 30.519531 17 35 21.480469 35 27 C 35 32.519531 30.519531 37 25 37 C 19.480469 37 15 32.519531 15 27 C 15 21.480469 19.480469 17 25 17 Z M 25 19 C 20.589844 19 17 22.589844 17 27 C 17 31.410156 20.589844 35 25 35 C 29.410156 35 33 31.410156 33 27 C 33 22.589844 29.410156 19 25 19 Z "/></svg>',
        setting:
          '<svg xmlns="http://www.w3.org/2000/svg" height="22" width="22" viewBox="0 0 22 22"><circle cx="11" cy="11" r="2"></circle><path d="M19.164 8.861L17.6 8.6a6.978 6.978 0 0 0-1.186-2.099l.574-1.533a1 1 0 0 0-.436-1.217l-1.997-1.153a1.001 1.001 0 0 0-1.272.23l-1.008 1.225a7.04 7.04 0 0 0-2.55.001L8.716 2.829a1 1 0 0 0-1.272-.23L5.447 3.751a1 1 0 0 0-.436 1.217l.574 1.533A6.997 6.997 0 0 0 4.4 8.6l-1.564.261A.999.999 0 0 0 2 9.847v2.306c0 .489.353.906.836.986l1.613.269a7 7 0 0 0 1.228 2.075l-.558 1.487a1 1 0 0 0 .436 1.217l1.997 1.153c.423.244.961.147 1.272-.23l1.04-1.263a7.089 7.089 0 0 0 2.272 0l1.04 1.263a1 1 0 0 0 1.272.23l1.997-1.153a1 1 0 0 0 .436-1.217l-.557-1.487c.521-.61.94-1.31 1.228-2.075l1.613-.269a.999.999 0 0 0 .835-.986V9.847a.999.999 0 0 0-.836-.986zM11 15a4 4 0 1 1 0-8 4 4 0 0 1 0 8z"></path></svg>',
        fullscreen:
          '<svg xmlns="http://www.w3.org/2000/svg" height="36" width="36" viewBox="0 0 36 36">\t<path d="m 10,16 2,0 0,-4 4,0 0,-2 L 10,10 l 0,6 0,0 z"></path>\t<path d="m 20,10 0,2 4,0 0,4 2,0 L 26,10 l -6,0 0,0 z"></path>\t<path d="m 24,24 -4,0 0,2 L 26,26 l 0,-6 -2,0 0,4 0,0 z"></path>\t<path d="M 12,20 10,20 10,26 l 6,0 0,-2 -4,0 0,-4 0,0 z"></path></svg>',
        fullscreenWeb:
          '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 36 36" height="36" width="36">\t<path d="m 28,11 0,14 -20,0 0,-14 z m -18,2 16,0 0,10 -16,0 0,-10 z" fill-rule="evenodd"></path></svg>',
        pip:
          '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 36 36" height="32" width="32"><path d="M25,17 L17,17 L17,23 L25,23 L25,17 L25,17 Z M29,25 L29,10.98 C29,9.88 28.1,9 27,9 L9,9 C7.9,9 7,9.88 7,10.98 L7,25 C7,26.1 7.9,27 9,27 L27,27 C28.1,27 29,26.1 29,25 L29,25 Z M27,25.02 L9,25.02 L9,10.97 L27,10.97 L27,25.02 L27,25.02 Z"></path></svg>',
      },
      r.option.icons
    );
    Object.keys(o).forEach(function (t) {
      X(n, t, {
        get: function () {
          var e = document.createElement("i");
          return g(e, "art-icon"), g(e, "art-icon-".concat(t)), x(e, o[t]), e;
        },
      });
    });
  };
  function Le(t, e) {
    var r = Object.keys(t);
    if (Object.getOwnPropertySymbols) {
      var n = Object.getOwnPropertySymbols(t);
      e &&
        (n = n.filter(function (e) {
          return Object.getOwnPropertyDescriptor(t, e).enumerable;
        })),
        r.push.apply(r, n);
    }
    return r;
  }
  function Me(t) {
    for (var e = 1; e < arguments.length; e++) {
      var r = null != arguments[e] ? arguments[e] : {};
      e % 2
        ? Le(Object(r), !0).forEach(function (e) {
            it(t, e, r[e]);
          })
        : Object.getOwnPropertyDescriptors
        ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(r))
        : Le(Object(r)).forEach(function (e) {
            Object.defineProperty(t, e, Object.getOwnPropertyDescriptor(r, e));
          });
    }
    return t;
  }
  function qe(t, e) {
    var r = Object.keys(t);
    if (Object.getOwnPropertySymbols) {
      var n = Object.getOwnPropertySymbols(t);
      e &&
        (n = n.filter(function (e) {
          return Object.getOwnPropertyDescriptor(t, e).enumerable;
        })),
        r.push.apply(r, n);
    }
    return r;
  }
  function Fe(t) {
    for (var e = 1; e < arguments.length; e++) {
      var r = null != arguments[e] ? arguments[e] : {};
      e % 2
        ? qe(Object(r), !0).forEach(function (e) {
            it(t, e, r[e]);
          })
        : Object.getOwnPropertyDescriptors
        ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(r))
        : qe(Object(r)).forEach(function (e) {
            Object.defineProperty(t, e, Object.getOwnPropertyDescriptor(r, e));
          });
    }
    return t;
  }
  function He(t, e) {
    var r = Object.keys(t);
    if (Object.getOwnPropertySymbols) {
      var n = Object.getOwnPropertySymbols(t);
      e &&
        (n = n.filter(function (e) {
          return Object.getOwnPropertyDescriptor(t, e).enumerable;
        })),
        r.push.apply(r, n);
    }
    return r;
  }
  function We(t) {
    for (var e = 1; e < arguments.length; e++) {
      var r = null != arguments[e] ? arguments[e] : {};
      e % 2
        ? He(Object(r), !0).forEach(function (e) {
            it(t, e, r[e]);
          })
        : Object.getOwnPropertyDescriptors
        ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(r))
        : He(Object(r)).forEach(function (e) {
            Object.defineProperty(t, e, Object.getOwnPropertyDescriptor(r, e));
          });
    }
    return t;
  }
  function Ie(t, e) {
    var r = Object.keys(t);
    if (Object.getOwnPropertySymbols) {
      var n = Object.getOwnPropertySymbols(t);
      e &&
        (n = n.filter(function (e) {
          return Object.getOwnPropertyDescriptor(t, e).enumerable;
        })),
        r.push.apply(r, n);
    }
    return r;
  }
  function Ve(t) {
    for (var e = 1; e < arguments.length; e++) {
      var r = null != arguments[e] ? arguments[e] : {};
      e % 2
        ? Ie(Object(r), !0).forEach(function (e) {
            it(t, e, r[e]);
          })
        : Object.getOwnPropertyDescriptors
        ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(r))
        : Ie(Object(r)).forEach(function (e) {
            Object.defineProperty(t, e, Object.getOwnPropertyDescriptor(r, e));
          });
    }
    return t;
  }
  function Be(t) {
    var e = (function () {
      if ("undefined" == typeof Reflect || !Reflect.construct) return !1;
      if (Reflect.construct.sham) return !1;
      if ("function" == typeof Proxy) return !0;
      try {
        return (
          Date.prototype.toString.call(
            Reflect.construct(Date, [], function () {})
          ),
          !0
        );
      } catch (t) {
        return !1;
      }
    })();
    return function () {
      var r,
        n = s(t);
      if (e) {
        var o = s(this).constructor;
        r = Reflect.construct(n, arguments, o);
      } else r = n.apply(this, arguments);
      return l(this, r);
    };
  }
  var Ne = (function (e) {
      a(n, e);
      var r = Be(n);
      function n(e) {
        var o;
        t(this, n), ((o = r.call(this, e)).name = "setting");
        var i = e.option,
          a = e.template,
          c = a.$setting,
          l = a.$settingBody,
          s = e.events.proxy;
        return (
          (o.$parent = l),
          i.setting &&
            (e.once("ready", function () {
              s(c, "click", function (t) {
                t.target === c && (o.show = !1);
              }),
                o.add(
                  (function (t) {
                    return function (e) {
                      var r = e.i18n,
                        n = e.player;
                      return Me(
                        Me({}, t),
                        {},
                        {
                          html: '<div class="art-setting-header">'
                            .concat(
                              r.get("Flip"),
                              '</div><div class="art-setting-radio"><div class="art-radio-item current"><button type="button" data-value="normal">'
                            )
                            .concat(
                              r.get("Normal"),
                              '</button></div><div class="art-radio-item"><button type="button" data-value="horizontal">'
                            )
                            .concat(
                              r.get("Horizontal"),
                              '</button></div><div class="art-radio-item"><button type="button" data-value="vertical">'
                            )
                            .concat(r.get("Vertical"), "</button></div></div>"),
                          click: function (t, e) {
                            var r = e.target.dataset.value;
                            r && (n.flip = r);
                          },
                          mounted: function (t) {
                            e.on("flip", function (e) {
                              var r = v("button", t).find(function (t) {
                                return t.dataset.value === e;
                              });
                              r && S(r.parentElement, "current");
                            });
                          },
                        }
                      );
                    };
                  })({ disable: !i.flip, name: "flip" })
                ),
                o.add(
                  (function (t) {
                    return function (e) {
                      var r = e.i18n,
                        n = e.player;
                      return Fe(
                        Fe({}, t),
                        {},
                        {
                          html: '<div class="art-setting-header">'.concat(
                            r.get("Rotate"),
                            ': <span class="art-rotate-value">0°</span></div><div class="art-setting-radio"><div class="art-radio-item"><button type="button" data-value="90">+90°</button></div><div class="art-radio-item"><button type="button" data-value="-90">-90°</button></div></div>'
                          ),
                          click: function (t, e) {
                            var r = e.target.dataset.value;
                            if (r) {
                              var o = n.rotate + Number(r);
                              n.rotate = 360 === o || -360 === o ? 0 : o;
                            } else n.rotate = 0;
                          },
                          mounted: function (t) {
                            var r = b(".art-rotate-value", t);
                            e.on("rotate", function (t) {
                              r.innerText = "".concat(t || 0, "°");
                            });
                          },
                        }
                      );
                    };
                  })({ disable: !i.rotate, name: "rotate" })
                ),
                o.add(
                  (function (t) {
                    return function (e) {
                      var r = e.i18n,
                        n = e.player;
                      return We(
                        We({}, t),
                        {},
                        {
                          html: '<div class="art-setting-header">'
                            .concat(
                              r.get("Aspect ratio"),
                              '</div><div class="art-setting-radio"><div class="art-radio-item current"><button type="button" data-value="default">'
                            )
                            .concat(
                              r.get("Default"),
                              '</button></div><div class="art-radio-item"><button type="button" data-value="4:3">4:3</button></div><div class="art-radio-item"><button type="button" data-value="16:9">16:9</button></div></div>'
                            ),
                          click: function (t, e) {
                            var r = e.target.dataset.value;
                            r && (n.aspectRatio = r);
                          },
                          mounted: function (t) {
                            e.on("aspectRatio", function (e) {
                              var r = v("button", t).find(function (t) {
                                return t.dataset.value === e;
                              });
                              r && S(r.parentElement, "current");
                            });
                          },
                        }
                      );
                    };
                  })({ disable: !i.aspectRatio, name: "aspectRatio" })
                ),
                o.add(
                  (function (t) {
                    return function (e) {
                      var r = e.i18n,
                        n = e.player,
                        o = e.events.proxy;
                      return Ve(
                        Ve({}, t),
                        {},
                        {
                          html: '<div class="art-setting-header">'.concat(
                            r.get("Play speed"),
                            ': <span class="art-subtitle-value">1.0</span>x</div><div class="art-setting-range"><input class="art-subtitle-range" value="1" type="range" min="0.5" max="2" step="0.25"></div>'
                          ),
                          mounted: function (t) {
                            var r = b(".art-setting-range input", t),
                              i = b(".art-subtitle-value", t);
                            o(r, "change", function () {
                              var t = r.value;
                              (i.innerText = t), (n.playbackRate = Number(t));
                            }),
                              e.on("playbackRate", function (t) {
                                t &&
                                  r.value !== t &&
                                  ((r.value = t), (i.innerText = t));
                              });
                          },
                        }
                      );
                    };
                  })({ disable: !i.playbackRate, name: "playbackRate" })
                );
            }),
            e.on("blur", function () {
              o.show = !1;
            })),
          o
        );
      }
      return n;
    })(Et),
    Ue = (function () {
      function e() {
        t(this, e), (this.name = "artplayer_settings");
      }
      return (
        r(e, [
          {
            key: "get",
            value: function (t) {
              var e = JSON.parse(localStorage.getItem(this.name)) || {};
              return t ? e[t] : e;
            },
          },
          {
            key: "set",
            value: function (t, e) {
              var r = Object.assign({}, this.get(), it({}, t, e));
              localStorage.setItem(this.name, JSON.stringify(r));
            },
          },
          {
            key: "del",
            value: function (t) {
              var e = this.get();
              delete e[t], localStorage.setItem(this.name, JSON.stringify(e));
            },
          },
          {
            key: "clean",
            value: function () {
              localStorage.removeItem(this.name);
            },
          },
        ]),
        e
      );
    })();
  function _e(t) {
    var e = t.i18n,
      r = t.subtitle,
      n = t.events.proxy;
    return {
      title: "Subtitle",
      name: "subtitleOffset",
      index: 20,
      html: '<div class="art-setting-header">'.concat(
        e.get("Subtitle offset time"),
        ': <span class="art-subtitle-value">0</span>s</div><div class="art-setting-range"><input class="art-subtitle-range" value="0" type="range" min="-5" max="5" step="0.5"></div>'
      ),
      mounted: function (e) {
        var o = b(".art-setting-range input", e),
          i = b(".art-subtitle-value", e);
        n(o, "change", function () {
          var e = o.value;
          (i.innerText = e), t.plugins.subtitleOffset.offset(Number(e));
        }),
          t.on("subtitle:switch", function () {
            (o.value = 0), (i.innerText = 0);
          }),
          t.on("subtitleOffset", function (t) {
            r.update(), o.value !== t && ((o.value = t), (i.innerText = t));
          });
      },
    };
  }
  function Xe(t) {
    var e = t.constructor.utils.clamp,
      r = t.setting,
      n = t.notice,
      o = t.template,
      i = t.i18n,
      a = t.player;
    r.add(_e);
    var c = [];
    return (
      t.on("subtitle:switch", function () {
        c = [];
      }),
      {
        name: "subtitleOffset",
        offset: function (r) {
          if (o.$track && o.$track.track) {
            var l = Array.from(o.$track.track.cues),
              s = e(r, -5, 5);
            l.forEach(function (t, r) {
              c[r] || (c[r] = { startTime: t.startTime, endTime: t.endTime }),
                (t.startTime = e(c[r].startTime + s, 0, a.duration)),
                (t.endTime = e(c[r].endTime + s, 0, a.duration));
            }),
              (n.show = ""
                .concat(i.get("Subtitle offset time"), ": ")
                .concat(r, "s")),
              t.emit("subtitleOffset", r);
          } else
            (n.show = "".concat(i.get("No subtitles found"))),
              t.emit("subtitleOffset", 0);
        },
      }
    );
  }
  function Ye(t) {
    var e = t.events.proxy,
      r = t.template,
      n = t.player,
      o = t.option,
      i = t.setting,
      a = t.i18n;
    function c(e) {
      if (e) {
        var i = r.$video.canPlayType(e.type);
        if ("maybe" === i || "probably" === i) {
          var a = URL.createObjectURL(e);
          (o.title = e.name), n.switchUrl(a, e.name), t.emit("localVideo", e);
        } else L(!1, "Playback of this file format is not supported");
      }
    }
    function l(t) {
      var r = x(t, '<input type="file">');
      O(t, "position", "relative"),
        k(r, {
          position: "absolute",
          width: "100%",
          height: "100%",
          left: "0",
          top: "0",
          opacity: "0",
        }),
        e(r, "change", function () {
          c(r.files[0]);
        });
    }
    return (
      e(r.$player, "dragover", function (t) {
        t.preventDefault();
      }),
      e(r.$player, "drop", function (t) {
        t.preventDefault(), c(t.dataTransfer.files[0]);
      }),
      t.once("ready", function () {
        i.add({
          title: "Local Video",
          name: "localVideo",
          index: 30,
          html: '<div class="art-setting-header">'
            .concat(
              a.get("Local Video"),
              '</div><div class="art-setting-upload"><div class="art-upload-btn">'
            )
            .concat(
              a.get("Open"),
              '</div><div class="art-upload-value"></div></div>'
            ),
          mounted: function (e) {
            var r = b(".art-upload-btn", e),
              n = b(".art-upload-value", e);
            t.on("localVideo", function (t) {
              (n.textContent = t.name), (n.title = t.name);
            }),
              l(r);
          },
        });
      }),
      { name: "localVideo", attach: l }
    );
  }
  function Ze(t) {
    var e = t.events.proxy,
      r = t.subtitle,
      n = t.setting,
      o = t.i18n;
    function i(n) {
      var o = x(n, '<input type="file">');
      O(n, "position", "relative"),
        k(o, {
          position: "absolute",
          width: "100%",
          height: "100%",
          left: "0",
          top: "0",
          opacity: "0",
        }),
        e(o, "change", function () {
          !(function (e) {
            if (e) {
              var n = H(e.name);
              ["ass", "vtt", "srt"].includes(n)
                ? (r.switch(URL.createObjectURL(e), { name: e.name, ext: n }),
                  t.emit("localSubtitle", e))
                : L(
                    !1,
                    "Only supports subtitle files in .ass, .vtt and .srt format"
                  );
            }
          })(o.files[0]);
        });
    }
    return (
      t.once("ready", function () {
        n.add({
          title: "Local Subtitle",
          name: "localSubtitle",
          index: 40,
          html: '<div class="art-setting-header">'
            .concat(
              o.get("Local Subtitle"),
              '</div><div class="art-setting-upload"><div class="art-upload-btn">'
            )
            .concat(
              o.get("Open"),
              '</div><div class="art-upload-value"></div></div>'
            ),
          mounted: function (e) {
            var r = b(".art-upload-btn", e),
              n = b(".art-upload-value", e);
            t.on("localSubtitle", function (t) {
              (n.textContent = t.name), (n.title = t.name);
            }),
              i(r);
          },
        });
      }),
      { name: "localSubtitle", attach: i }
    );
  }
  function Je(t) {
    var e = t.layers,
      r = t.player,
      n = t.option.theme;
    return (
      e.add({
        name: "miniProgressBar",
        style: {
          display: "none",
          position: "absolute",
          left: 0,
          right: 0,
          bottom: 0,
          height: "2px",
          background: n,
        },
        mounted: function (e) {
          t.on("control", function (t) {
            e.style.display = t ? "none" : "block";
          }),
            t.on("destroy", function () {
              e.style.display = "none";
            }),
            t.on("video:timeupdate", function () {
              e.style.width = "".concat(100 * r.played, "%");
            });
        },
      }),
      { name: "miniProgressBar" }
    );
  }
  function Qe(t) {
    var e = 1e4,
      r = 0,
      n = 0,
      o = 0,
      i = null;
    function a() {
      (r = 0), (n = 0), (o = 0), cancelAnimationFrame(i), (i = null);
    }
    function c() {
      i ||
        (function a() {
          t.isDestroy ||
            (i = requestAnimationFrame(function () {
              var i = Date.now();
              if (o) {
                var c = i - o;
                (n += c), t.player.playing || (r += c);
              }
              (o = i),
                t.emit("networkMonitor", r / n),
                n >= e && ((r = 0), (n = 0)),
                a();
            }));
        })();
    }
    return (
      t.on("play", c),
      t.on("pause", a),
      {
        name: "networkMonitor",
        reset: a,
        start: c,
        sample: function (t) {
          e = t;
        },
      }
    );
  }
  var Ge = (function () {
      function e(r) {
        var n = this;
        t(this, e), (this.art = r), (this.id = 0);
        var o = r.option;
        o.subtitle.url && o.subtitleOffset && this.add(Xe),
          !o.isLive && o.miniProgressBar && this.add(Je),
          o.localVideo && this.add(Ye),
          o.localSubtitle && this.add(Ze),
          o.networkMonitor && this.add(Qe),
          r.option.plugins.forEach(function (t) {
            n.add(t);
          });
      }
      return (
        r(e, [
          {
            key: "add",
            value: function (t) {
              this.id += 1;
              var e = t.call(this, this.art),
                r = (e && e.name) || t.name || "plugin".concat(this.id);
              return (
                L(
                  !Z(this, r),
                  "Cannot add a plugin that already has the same name: ".concat(
                    r
                  )
                ),
                X(this, r, { value: e }),
                this
              );
            },
          },
        ]),
        e
      );
    })(),
    Ke = function e(r) {
      t(this, e);
      var n = r.option,
        o = r.events.proxy,
        i = r.template.$video;
      bt.events.forEach(function (t) {
        o(i, t, function (t) {
          r.emit("video:".concat(t.type), t);
        });
      }),
        Object.keys(n.moreVideoAttr).forEach(function (t) {
          i[t] = n.moreVideoAttr[t];
        }),
        n.muted && (i.muted = n.muted),
        n.volume && (i.volume = et(n.volume, 0, 1)),
        n.poster && (i.poster = n.poster),
        n.autoplay && (i.autoplay = n.autoplay),
        (i.controls = !0);
      var a = n.type || H(n.url),
        c = n.customType[a];
      a && c
        ? (c(i, n.url, r), r.emit("customType", a))
        : ((i.src = n.url), r.emit("url", i.src));
    };
  function tr(t) {
    var e = (function () {
      if ("undefined" == typeof Reflect || !Reflect.construct) return !1;
      if (Reflect.construct.sham) return !1;
      if ("function" == typeof Proxy) return !0;
      try {
        return (
          Date.prototype.toString.call(
            Reflect.construct(Date, [], function () {})
          ),
          !0
        );
      } catch (t) {
        return !1;
      }
    })();
    return function () {
      var r,
        n = s(t);
      if (e) {
        var o = s(this).constructor;
        r = Reflect.construct(n, arguments, o);
      } else r = n.apply(this, arguments);
      return l(this, r);
    };
  }
  var er = 0,
    rr = [],
    nr = (function (e) {
      a(i, e);
      var o = tr(i);
      function i(e) {
        var r;
        return (
          t(this, i),
          ((r = o.call(this)).option = u(Q(i.option, e), yt)),
          (r.isFocus = !1),
          (r.isDestroy = !1),
          (r.userAgent = f),
          (r.isMobile = d),
          (r.isWechat = y),
          (r.whitelist = new vt(n(r))),
          (r.template = new gt(n(r))),
          (r.events = new je(n(r))),
          r.whitelist.state
            ? ((r.storage = new Ue(n(r))),
              (r.icons = new Ce(n(r))),
              (r.i18n = new xt(n(r))),
              (r.notice = new $e(n(r))),
              (r.player = new Pt(n(r))),
              (r.layers = new Re(n(r))),
              (r.controls = new ie(n(r))),
              (r.contextmenu = new me(n(r))),
              (r.subtitle = new ke(n(r))),
              (r.info = new xe(n(r))),
              (r.loading = new De(n(r))),
              (r.hotkey = new Pe(n(r))),
              (r.mask = new ze(n(r))),
              (r.setting = new Ne(n(r))),
              (r.plugins = new Ge(n(r))))
            : (r.mobile = new Ke(n(r))),
          (er += 1),
          (r.id = er),
          rr.push(n(r)),
          r
        );
      }
      return (
        r(
          i,
          [
            {
              key: "destroy",
              value: function () {
                var t =
                  !(arguments.length > 0 && void 0 !== arguments[0]) ||
                  arguments[0];
                this.events.destroy(),
                  this.template.destroy(t),
                  rr.splice(rr.indexOf(this), 1),
                  (this.isDestroy = !0),
                  this.emit("destroy");
              },
            },
          ],
          [
            {
              key: "instances",
              get: function () {
                return rr;
              },
            },
            {
              key: "version",
              get: function () {
                return "3.5.26";
              },
            },
            {
              key: "env",
              get: function () {
                return '"production"';
              },
            },
            {
              key: "config",
              get: function () {
                return bt;
              },
            },
            {
              key: "utils",
              get: function () {
                return ot;
              },
            },
            {
              key: "scheme",
              get: function () {
                return yt;
              },
            },
            {
              key: "Emitter",
              get: function () {
                return p;
              },
            },
            {
              key: "validator",
              get: function () {
                return u;
              },
            },
            {
              key: "kindOf",
              get: function () {
                return u.kindOf;
              },
            },
            {
              key: "option",
              get: function () {
                return {
                  container: "#artplayer",
                  url: "",
                  poster: "",
                  title: "",
                  theme: "#f00",
                  volume: 0.7,
                  isLive: !1,
                  muted: !1,
                  autoplay: !1,
                  autoSize: !1,
                  autoMini: !1,
                  loop: !1,
                  flip: !1,
                  rotate: !1,
                  playbackRate: !1,
                  aspectRatio: !1,
                  screenshot: !1,
                  setting: !1,
                  hotkey: !0,
                  pip: !1,
                  mutex: !0,
                  light: !1,
                  backdrop: !0,
                  fullscreen: !1,
                  fullscreenWeb: !1,
                  subtitleOffset: !1,
                  miniProgressBar: !1,
                  localVideo: !1,
                  localSubtitle: !1,
                  networkMonitor: !1,
                  layers: [],
                  contextmenu: [],
                  controls: [],
                  quality: [],
                  highlight: [],
                  plugins: [],
                  whitelist: [],
                  switcher: [],
                  thumbnails: {
                    url: "",
                    number: 60,
                    width: 160,
                    height: 90,
                    column: 10,
                  },
                  subtitle: {
                    url: "",
                    style: {},
                    encoding: "utf-8",
                    bilingual: !1,
                  },
                  moreVideoAttr: {
                    controls: !1,
                    preload: h ? "auto" : "metadata",
                  },
                  icons: {},
                  customType: {},
                  lang: navigator.language.toLowerCase(),
                };
              },
            },
          ]
        ),
        i
      );
    })(p);
  return (
    console.log(
      "%c ArtPlayer %c 3.5.26 %c https://artplayer.org",
      "color: #fff; background: #5f5f5f",
      "color: #fff; background: #4bc729",
      ""
    ),
    nr
  );
});
