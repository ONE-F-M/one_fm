function ownKeys(object, enumerableOnly) { var keys = Object.keys(object); if (Object.getOwnPropertySymbols) { var symbols = Object.getOwnPropertySymbols(object); enumerableOnly && (symbols = symbols.filter(function (sym) { return Object.getOwnPropertyDescriptor(object, sym).enumerable; })), keys.push.apply(keys, symbols); } return keys; }

function _objectSpread(target) { for (var i = 1; i < arguments.length; i++) { var source = null != arguments[i] ? arguments[i] : {}; i % 2 ? ownKeys(Object(source), !0).forEach(function (key) { _defineProperty(target, key, source[key]); }) : Object.getOwnPropertyDescriptors ? Object.defineProperties(target, Object.getOwnPropertyDescriptors(source)) : ownKeys(Object(source)).forEach(function (key) { Object.defineProperty(target, key, Object.getOwnPropertyDescriptor(source, key)); }); } return target; }

function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

import { extend, mergeData } from '../../vue';
import { NAME_NAVBAR_BRAND } from '../../constants/components';
import { PROP_TYPE_STRING } from '../../constants/props';
import { omit, sortKeys } from '../../utils/object';
import { makeProp, makePropsConfigurable, pluckProps } from '../../utils/props';
import { BLink, props as BLinkProps } from '../link/link'; // --- Props ---

var linkProps = omit(BLinkProps, ['event', 'routerTag']);
linkProps.href.default = undefined;
linkProps.to.default = undefined;
export var props = makePropsConfigurable(sortKeys(_objectSpread(_objectSpread({}, linkProps), {}, {
  tag: makeProp(PROP_TYPE_STRING, 'div')
})), NAME_NAVBAR_BRAND); // --- Main component ---
// @vue/component

export var BNavbarBrand = /*#__PURE__*/extend({
  name: NAME_NAVBAR_BRAND,
  functional: true,
  props: props,
  render: function render(h, _ref) {
    var props = _ref.props,
        data = _ref.data,
        children = _ref.children;
    var isLink = props.to || props.href;
    var tag = isLink ? BLink : props.tag;
    return h(tag, mergeData(data, {
      staticClass: 'navbar-brand',
      props: isLink ? pluckProps(linkProps, props) : {}
    }), children);
  }
});