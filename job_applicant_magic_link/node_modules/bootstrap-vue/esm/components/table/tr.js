function ownKeys(object, enumerableOnly) { var keys = Object.keys(object); if (Object.getOwnPropertySymbols) { var symbols = Object.getOwnPropertySymbols(object); enumerableOnly && (symbols = symbols.filter(function (sym) { return Object.getOwnPropertyDescriptor(object, sym).enumerable; })), keys.push.apply(keys, symbols); } return keys; }

function _objectSpread(target) { for (var i = 1; i < arguments.length; i++) { var source = null != arguments[i] ? arguments[i] : {}; i % 2 ? ownKeys(Object(source), !0).forEach(function (key) { _defineProperty(target, key, source[key]); }) : Object.getOwnPropertyDescriptors ? Object.defineProperties(target, Object.getOwnPropertyDescriptors(source)) : ownKeys(Object(source)).forEach(function (key) { Object.defineProperty(target, key, Object.getOwnPropertyDescriptor(source, key)); }); } return target; }

function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

import { extend } from '../../vue';
import { NAME_TR } from '../../constants/components';
import { PROP_TYPE_STRING } from '../../constants/props';
import { makeProp, makePropsConfigurable } from '../../utils/props';
import { attrsMixin } from '../../mixins/attrs';
import { listenersMixin } from '../../mixins/listeners';
import { normalizeSlotMixin } from '../../mixins/normalize-slot'; // --- Constants ---

var LIGHT = 'light';
var DARK = 'dark'; // --- Props ---

export var props = makePropsConfigurable({
  variant: makeProp(PROP_TYPE_STRING)
}, NAME_TR); // --- Main component ---
// TODO:
//   In Bootstrap v5, we won't need "sniffing" as table element variants properly inherit
//   to the child elements, so this can be converted to a functional component
// @vue/component

export var BTr = /*#__PURE__*/extend({
  name: NAME_TR,
  mixins: [attrsMixin, listenersMixin, normalizeSlotMixin],
  provide: function provide() {
    var _this = this;

    return {
      getBvTableTr: function getBvTableTr() {
        return _this;
      }
    };
  },
  inject: {
    getBvTableRowGroup: {
      default:
      /* istanbul ignore next */
      function _default() {
        return function () {
          return {};
        };
      }
    }
  },
  inheritAttrs: false,
  props: props,
  computed: {
    bvTableRowGroup: function bvTableRowGroup() {
      return this.getBvTableRowGroup();
    },
    // Sniffed by `<b-td>` / `<b-th>`
    inTbody: function inTbody() {
      return this.bvTableRowGroup.isTbody;
    },
    // Sniffed by `<b-td>` / `<b-th>`
    inThead: function inThead() {
      return this.bvTableRowGroup.isThead;
    },
    // Sniffed by `<b-td>` / `<b-th>`
    inTfoot: function inTfoot() {
      return this.bvTableRowGroup.isTfoot;
    },
    // Sniffed by `<b-td>` / `<b-th>`
    isDark: function isDark() {
      return this.bvTableRowGroup.isDark;
    },
    // Sniffed by `<b-td>` / `<b-th>`
    isStacked: function isStacked() {
      return this.bvTableRowGroup.isStacked;
    },
    // Sniffed by `<b-td>` / `<b-th>`
    isResponsive: function isResponsive() {
      return this.bvTableRowGroup.isResponsive;
    },
    // Sniffed by `<b-td>` / `<b-th>`
    // Sticky headers are only supported in thead
    isStickyHeader: function isStickyHeader() {
      return this.bvTableRowGroup.isStickyHeader;
    },
    // Sniffed by <b-tr> / `<b-td>` / `<b-th>`
    // Needed to handle header background classes, due to lack of
    // background color inheritance with Bootstrap v4 table CSS
    hasStickyHeader: function hasStickyHeader() {
      return !this.isStacked && this.bvTableRowGroup.hasStickyHeader;
    },
    // Sniffed by `<b-td>` / `<b-th>`
    tableVariant: function tableVariant() {
      return this.bvTableRowGroup.tableVariant;
    },
    // Sniffed by `<b-td>` / `<b-th>`
    headVariant: function headVariant() {
      return this.inThead ? this.bvTableRowGroup.headVariant : null;
    },
    // Sniffed by `<b-td>` / `<b-th>`
    footVariant: function footVariant() {
      return this.inTfoot ? this.bvTableRowGroup.footVariant : null;
    },
    isRowDark: function isRowDark() {
      return this.headVariant === LIGHT || this.footVariant === LIGHT ?
      /* istanbul ignore next */
      false : this.headVariant === DARK || this.footVariant === DARK ?
      /* istanbul ignore next */
      true : this.isDark;
    },
    trClasses: function trClasses() {
      var variant = this.variant;
      return [variant ? "".concat(this.isRowDark ? 'bg' : 'table', "-").concat(variant) : null];
    },
    trAttrs: function trAttrs() {
      return _objectSpread({
        role: 'row'
      }, this.bvAttrs);
    }
  },
  render: function render(h) {
    return h('tr', {
      class: this.trClasses,
      attrs: this.trAttrs,
      // Pass native listeners to child
      on: this.bvListeners
    }, this.normalizeSlot());
  }
});