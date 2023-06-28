function _toConsumableArray(arr) { return _arrayWithoutHoles(arr) || _iterableToArray(arr) || _unsupportedIterableToArray(arr) || _nonIterableSpread(); }

function _nonIterableSpread() { throw new TypeError("Invalid attempt to spread non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method."); }

function _unsupportedIterableToArray(o, minLen) { if (!o) return; if (typeof o === "string") return _arrayLikeToArray(o, minLen); var n = Object.prototype.toString.call(o).slice(8, -1); if (n === "Object" && o.constructor) n = o.constructor.name; if (n === "Map" || n === "Set") return Array.from(o); if (n === "Arguments" || /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(n)) return _arrayLikeToArray(o, minLen); }

function _iterableToArray(iter) { if (typeof Symbol !== "undefined" && iter[Symbol.iterator] != null || iter["@@iterator"] != null) return Array.from(iter); }

function _arrayWithoutHoles(arr) { if (Array.isArray(arr)) return _arrayLikeToArray(arr); }

function _arrayLikeToArray(arr, len) { if (len == null || len > arr.length) len = arr.length; for (var i = 0, arr2 = new Array(len); i < len; i++) { arr2[i] = arr[i]; } return arr2; }

function ownKeys(object, enumerableOnly) { var keys = Object.keys(object); if (Object.getOwnPropertySymbols) { var symbols = Object.getOwnPropertySymbols(object); enumerableOnly && (symbols = symbols.filter(function (sym) { return Object.getOwnPropertyDescriptor(object, sym).enumerable; })), keys.push.apply(keys, symbols); } return keys; }

function _objectSpread(target) { for (var i = 1; i < arguments.length; i++) { var source = null != arguments[i] ? arguments[i] : {}; i % 2 ? ownKeys(Object(source), !0).forEach(function (key) { _defineProperty(target, key, source[key]); }) : Object.getOwnPropertyDescriptors ? Object.defineProperties(target, Object.getOwnPropertyDescriptors(source)) : ownKeys(Object(source)).forEach(function (key) { Object.defineProperty(target, key, Object.getOwnPropertyDescriptor(source, key)); }); } return target; }

function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

import { extend } from '../../vue';
import { NAME_NAV_ITEM_DROPDOWN } from '../../constants/components';
import { SLOT_NAME_BUTTON_CONTENT, SLOT_NAME_DEFAULT, SLOT_NAME_TEXT } from '../../constants/slots';
import { htmlOrText } from '../../utils/html';
import { keys, pick, sortKeys } from '../../utils/object';
import { makePropsConfigurable } from '../../utils/props';
import { dropdownMixin, props as dropdownProps } from '../../mixins/dropdown';
import { idMixin, props as idProps } from '../../mixins/id';
import { normalizeSlotMixin } from '../../mixins/normalize-slot';
import { props as BDropdownProps } from '../dropdown/dropdown';
import { BLink } from '../link/link'; // --- Props ---

export var props = makePropsConfigurable(sortKeys(_objectSpread(_objectSpread({}, idProps), pick(BDropdownProps, [].concat(_toConsumableArray(keys(dropdownProps)), ['html', 'lazy', 'menuClass', 'noCaret', 'role', 'text', 'toggleClass'])))), NAME_NAV_ITEM_DROPDOWN); // --- Main component ---
// @vue/component

export var BNavItemDropdown = /*#__PURE__*/extend({
  name: NAME_NAV_ITEM_DROPDOWN,
  mixins: [idMixin, dropdownMixin, normalizeSlotMixin],
  props: props,
  computed: {
    toggleId: function toggleId() {
      return this.safeId('_BV_toggle_');
    },
    menuId: function menuId() {
      return this.safeId('_BV_toggle_menu_');
    },
    dropdownClasses: function dropdownClasses() {
      return [this.directionClass, this.boundaryClass, {
        show: this.visible
      }];
    },
    menuClasses: function menuClasses() {
      return [this.menuClass, {
        'dropdown-menu-right': this.right,
        show: this.visible
      }];
    },
    toggleClasses: function toggleClasses() {
      return [this.toggleClass, {
        'dropdown-toggle-no-caret': this.noCaret
      }];
    }
  },
  render: function render(h) {
    var toggleId = this.toggleId,
        menuId = this.menuId,
        visible = this.visible,
        hide = this.hide;
    var $toggle = h(BLink, {
      staticClass: 'nav-link dropdown-toggle',
      class: this.toggleClasses,
      props: {
        href: "#".concat(this.id || ''),
        disabled: this.disabled
      },
      attrs: {
        id: toggleId,
        role: 'button',
        'aria-haspopup': 'true',
        'aria-expanded': visible ? 'true' : 'false',
        'aria-controls': menuId
      },
      on: {
        mousedown: this.onMousedown,
        click: this.toggle,
        keydown: this.toggle // Handle ENTER, SPACE and DOWN

      },
      ref: 'toggle'
    }, [// TODO: The `text` slot is deprecated in favor of the `button-content` slot
    this.normalizeSlot([SLOT_NAME_BUTTON_CONTENT, SLOT_NAME_TEXT]) || h('span', {
      domProps: htmlOrText(this.html, this.text)
    })]);
    var $menu = h('ul', {
      staticClass: 'dropdown-menu',
      class: this.menuClasses,
      attrs: {
        tabindex: '-1',
        'aria-labelledby': toggleId,
        id: menuId
      },
      on: {
        keydown: this.onKeydown // Handle UP, DOWN and ESC

      },
      ref: 'menu'
    }, !this.lazy || visible ? this.normalizeSlot(SLOT_NAME_DEFAULT, {
      hide: hide
    }) : [h()]);
    return h('li', {
      staticClass: 'nav-item b-nav-dropdown dropdown',
      class: this.dropdownClasses,
      attrs: {
        id: this.safeId()
      }
    }, [$toggle, $menu]);
  }
});