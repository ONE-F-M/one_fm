function ownKeys(object, enumerableOnly) { var keys = Object.keys(object); if (Object.getOwnPropertySymbols) { var symbols = Object.getOwnPropertySymbols(object); enumerableOnly && (symbols = symbols.filter(function (sym) { return Object.getOwnPropertyDescriptor(object, sym).enumerable; })), keys.push.apply(keys, symbols); } return keys; }

function _objectSpread(target) { for (var i = 1; i < arguments.length; i++) { var source = null != arguments[i] ? arguments[i] : {}; i % 2 ? ownKeys(Object(source), !0).forEach(function (key) { _defineProperty(target, key, source[key]); }) : Object.getOwnPropertyDescriptors ? Object.defineProperties(target, Object.getOwnPropertyDescriptors(source)) : ownKeys(Object(source)).forEach(function (key) { Object.defineProperty(target, key, Object.getOwnPropertyDescriptor(source, key)); }); } return target; }

function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

import { extend, mergeData } from '../../vue';
import { NAME_SKELETON_ICON } from '../../constants/components';
import { PROP_TYPE_OBJECT, PROP_TYPE_STRING } from '../../constants/props';
import { makeProp, makePropsConfigurable } from '../../utils/props';
import { BIcon } from '../../icons'; // --- Props ---

export var props = makePropsConfigurable({
  animation: makeProp(PROP_TYPE_STRING, 'wave'),
  icon: makeProp(PROP_TYPE_STRING),
  iconProps: makeProp(PROP_TYPE_OBJECT, {})
}, NAME_SKELETON_ICON); // --- Main component ---
// @vue/component

export var BSkeletonIcon = /*#__PURE__*/extend({
  name: NAME_SKELETON_ICON,
  functional: true,
  props: props,
  render: function render(h, _ref) {
    var data = _ref.data,
        props = _ref.props;
    var icon = props.icon,
        animation = props.animation;
    var $icon = h(BIcon, {
      staticClass: 'b-skeleton-icon',
      props: _objectSpread(_objectSpread({}, props.iconProps), {}, {
        icon: icon
      })
    });
    return h('div', mergeData(data, {
      staticClass: 'b-skeleton-icon-wrapper position-relative d-inline-block overflow-hidden',
      class: _defineProperty({}, "b-skeleton-animate-".concat(animation), animation)
    }), [$icon]);
  }
});