import { extend } from '../vue'; // --- Mixin ---
// @vue/component

export var useParentMixin = extend({
  computed: {
    bvParent: function bvParent() {
      return this.$parent || this.$root === this && this.$options.bvParent;
    }
  }
});