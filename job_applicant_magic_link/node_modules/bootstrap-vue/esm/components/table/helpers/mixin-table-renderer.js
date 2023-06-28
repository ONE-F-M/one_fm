function ownKeys(object, enumerableOnly) { var keys = Object.keys(object); if (Object.getOwnPropertySymbols) { var symbols = Object.getOwnPropertySymbols(object); enumerableOnly && (symbols = symbols.filter(function (sym) { return Object.getOwnPropertyDescriptor(object, sym).enumerable; })), keys.push.apply(keys, symbols); } return keys; }

function _objectSpread(target) { for (var i = 1; i < arguments.length; i++) { var source = null != arguments[i] ? arguments[i] : {}; i % 2 ? ownKeys(Object(source), !0).forEach(function (key) { _defineProperty(target, key, source[key]); }) : Object.getOwnPropertyDescriptors ? Object.defineProperties(target, Object.getOwnPropertyDescriptors(source)) : ownKeys(Object(source)).forEach(function (key) { Object.defineProperty(target, key, Object.getOwnPropertyDescriptor(source, key)); }); } return target; }

function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

import { extend } from '../../../vue';
import { PROP_TYPE_ARRAY_OBJECT_STRING, PROP_TYPE_BOOLEAN, PROP_TYPE_BOOLEAN_STRING, PROP_TYPE_STRING } from '../../../constants/props';
import { identity } from '../../../utils/identity';
import { isBoolean } from '../../../utils/inspect';
import { makeProp } from '../../../utils/props';
import { safeVueInstance } from '../../../utils/safe-vue-instance';
import { toString } from '../../../utils/string';
import { attrsMixin } from '../../../mixins/attrs'; // Main `<table>` render mixin
// Includes all main table styling options
// --- Props ---

export var props = {
  bordered: makeProp(PROP_TYPE_BOOLEAN, false),
  borderless: makeProp(PROP_TYPE_BOOLEAN, false),
  captionTop: makeProp(PROP_TYPE_BOOLEAN, false),
  dark: makeProp(PROP_TYPE_BOOLEAN, false),
  fixed: makeProp(PROP_TYPE_BOOLEAN, false),
  hover: makeProp(PROP_TYPE_BOOLEAN, false),
  noBorderCollapse: makeProp(PROP_TYPE_BOOLEAN, false),
  outlined: makeProp(PROP_TYPE_BOOLEAN, false),
  responsive: makeProp(PROP_TYPE_BOOLEAN_STRING, false),
  small: makeProp(PROP_TYPE_BOOLEAN, false),
  // If a string, it is assumed to be the table `max-height` value
  stickyHeader: makeProp(PROP_TYPE_BOOLEAN_STRING, false),
  striped: makeProp(PROP_TYPE_BOOLEAN, false),
  tableClass: makeProp(PROP_TYPE_ARRAY_OBJECT_STRING),
  tableVariant: makeProp(PROP_TYPE_STRING)
}; // --- Mixin ---
// @vue/component

export var tableRendererMixin = extend({
  mixins: [attrsMixin],
  provide: function provide() {
    var _this = this;

    return {
      getBvTable: function getBvTable() {
        return _this;
      }
    };
  },
  // Don't place attributes on root element automatically,
  // as table could be wrapped in responsive `<div>`
  inheritAttrs: false,
  props: props,
  computed: {
    isTableSimple: function isTableSimple() {
      return false;
    },
    // Layout related computed props
    isResponsive: function isResponsive() {
      var responsive = this.responsive;
      return responsive === '' ? true : responsive;
    },
    isStickyHeader: function isStickyHeader() {
      var stickyHeader = this.stickyHeader;
      stickyHeader = stickyHeader === '' ? true : stickyHeader;
      return this.isStacked ? false : stickyHeader;
    },
    wrapperClasses: function wrapperClasses() {
      var isResponsive = this.isResponsive;
      return [this.isStickyHeader ? 'b-table-sticky-header' : '', isResponsive === true ? 'table-responsive' : isResponsive ? "table-responsive-".concat(this.responsive) : ''].filter(identity);
    },
    wrapperStyles: function wrapperStyles() {
      var isStickyHeader = this.isStickyHeader;
      return isStickyHeader && !isBoolean(isStickyHeader) ? {
        maxHeight: isStickyHeader
      } : {};
    },
    tableClasses: function tableClasses() {
      var _safeVueInstance = safeVueInstance(this),
          hover = _safeVueInstance.hover,
          tableVariant = _safeVueInstance.tableVariant,
          selectableTableClasses = _safeVueInstance.selectableTableClasses,
          stackedTableClasses = _safeVueInstance.stackedTableClasses,
          tableClass = _safeVueInstance.tableClass,
          computedBusy = _safeVueInstance.computedBusy;

      hover = this.isTableSimple ? hover : hover && this.computedItems.length > 0 && !computedBusy;
      return [// User supplied classes
      tableClass, // Styling classes
      {
        'table-striped': this.striped,
        'table-hover': hover,
        'table-dark': this.dark,
        'table-bordered': this.bordered,
        'table-borderless': this.borderless,
        'table-sm': this.small,
        // The following are b-table custom styles
        border: this.outlined,
        'b-table-fixed': this.fixed,
        'b-table-caption-top': this.captionTop,
        'b-table-no-border-collapse': this.noBorderCollapse
      }, tableVariant ? "".concat(this.dark ? 'bg' : 'table', "-").concat(tableVariant) : '', // Stacked table classes
      stackedTableClasses, // Selectable classes
      selectableTableClasses];
    },
    tableAttrs: function tableAttrs() {
      var _safeVueInstance2 = safeVueInstance(this),
          items = _safeVueInstance2.computedItems,
          filteredItems = _safeVueInstance2.filteredItems,
          fields = _safeVueInstance2.computedFields,
          selectableTableAttrs = _safeVueInstance2.selectableTableAttrs,
          computedBusy = _safeVueInstance2.computedBusy;

      var ariaAttrs = this.isTableSimple ? {} : {
        'aria-busy': toString(computedBusy),
        'aria-colcount': toString(fields.length),
        // Preserve user supplied `aria-describedby`, if provided
        'aria-describedby': this.bvAttrs['aria-describedby'] || this.$refs.caption ? this.captionId : null
      };
      var rowCount = items && filteredItems && filteredItems.length > items.length ? toString(filteredItems.length) : null;
      return _objectSpread(_objectSpread(_objectSpread({
        // We set `aria-rowcount` before merging in `$attrs`,
        // in case user has supplied their own
        'aria-rowcount': rowCount
      }, this.bvAttrs), {}, {
        // Now we can override any `$attrs` here
        id: this.safeId(),
        role: this.bvAttrs.role || 'table'
      }, ariaAttrs), selectableTableAttrs);
    }
  },
  render: function render(h) {
    var _safeVueInstance3 = safeVueInstance(this),
        wrapperClasses = _safeVueInstance3.wrapperClasses,
        renderCaption = _safeVueInstance3.renderCaption,
        renderColgroup = _safeVueInstance3.renderColgroup,
        renderThead = _safeVueInstance3.renderThead,
        renderTbody = _safeVueInstance3.renderTbody,
        renderTfoot = _safeVueInstance3.renderTfoot;

    var $content = [];

    if (this.isTableSimple) {
      $content.push(this.normalizeSlot());
    } else {
      // Build the `<caption>` (from caption mixin)
      $content.push(renderCaption ? renderCaption() : null); // Build the `<colgroup>`

      $content.push(renderColgroup ? renderColgroup() : null); // Build the `<thead>`

      $content.push(renderThead ? renderThead() : null); // Build the `<tbody>`

      $content.push(renderTbody ? renderTbody() : null); // Build the `<tfoot>`

      $content.push(renderTfoot ? renderTfoot() : null);
    } // Assemble `<table>`


    var $table = h('table', {
      staticClass: 'table b-table',
      class: this.tableClasses,
      attrs: this.tableAttrs,
      key: 'b-table'
    }, $content.filter(identity)); // Add responsive/sticky wrapper if needed and return table

    return wrapperClasses.length > 0 ? h('div', {
      class: wrapperClasses,
      style: this.wrapperStyles,
      key: 'wrap'
    }, [$table]) : $table;
  }
});