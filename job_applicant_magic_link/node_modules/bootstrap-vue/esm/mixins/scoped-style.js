function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

import { extend } from '../vue';
import { useParentMixin } from '../mixins/use-parent';
import { getScopeId } from '../utils/get-scope-id'; // @vue/component

export var scopedStyleMixin = extend({
  mixins: [useParentMixin],
  computed: {
    scopedStyleAttrs: function scopedStyleAttrs() {
      var scopeId = getScopeId(this.bvParent);
      return scopeId ? _defineProperty({}, scopeId, '') : {};
    }
  }
});