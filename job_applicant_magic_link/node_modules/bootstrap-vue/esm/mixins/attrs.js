function ownKeys(object, enumerableOnly) { var keys = Object.keys(object); if (Object.getOwnPropertySymbols) { var symbols = Object.getOwnPropertySymbols(object); enumerableOnly && (symbols = symbols.filter(function (sym) { return Object.getOwnPropertyDescriptor(object, sym).enumerable; })), keys.push.apply(keys, symbols); } return keys; }

function _objectSpread(target) { for (var i = 1; i < arguments.length; i++) { var source = null != arguments[i] ? arguments[i] : {}; i % 2 ? ownKeys(Object(source), !0).forEach(function (key) { _defineProperty(target, key, source[key]); }) : Object.getOwnPropertyDescriptors ? Object.defineProperties(target, Object.getOwnPropertyDescriptors(source)) : ownKeys(Object(source)).forEach(function (key) { Object.defineProperty(target, key, Object.getOwnPropertyDescriptor(source, key)); }); } return target; }

function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

import { makePropCacheMixin } from '../utils/cache';
import { extend, isVue3 } from '../vue';
var attrsMixinVue2 = makePropCacheMixin('$attrs', 'bvAttrs');
var attrsMixinVue3 = extend({
  computed: {
    bvAttrs: function bvAttrs() {
      var bvAttrs = _objectSpread({}, this.$attrs);

      Object.keys(bvAttrs).forEach(function (key) {
        if (bvAttrs[key] === undefined) {
          delete bvAttrs[key];
        }
      });
      return bvAttrs;
    }
  }
});
export var attrsMixin = isVue3 ? attrsMixinVue3 : attrsMixinVue2;