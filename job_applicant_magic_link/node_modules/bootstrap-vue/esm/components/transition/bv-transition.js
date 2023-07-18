function ownKeys(object, enumerableOnly) { var keys = Object.keys(object); if (Object.getOwnPropertySymbols) { var symbols = Object.getOwnPropertySymbols(object); enumerableOnly && (symbols = symbols.filter(function (sym) { return Object.getOwnPropertyDescriptor(object, sym).enumerable; })), keys.push.apply(keys, symbols); } return keys; }

function _objectSpread(target) { for (var i = 1; i < arguments.length; i++) { var source = null != arguments[i] ? arguments[i] : {}; i % 2 ? ownKeys(Object(source), !0).forEach(function (key) { _defineProperty(target, key, source[key]); }) : Object.getOwnPropertyDescriptors ? Object.defineProperties(target, Object.getOwnPropertyDescriptors(source)) : ownKeys(Object(source)).forEach(function (key) { Object.defineProperty(target, key, Object.getOwnPropertyDescriptor(source, key)); }); } return target; }

function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

// Generic Bootstrap v4 fade (no-fade) transition component
//
// Assumes that `show` class is not required when
// the transition has finished the enter transition
// (show and fade classes are only applied during transition)
import { extend, mergeData } from '../../vue';
import { NAME_TRANSITION } from '../../constants/components';
import { PROP_TYPE_BOOLEAN, PROP_TYPE_OBJECT, PROP_TYPE_STRING } from '../../constants/props';
import { isPlainObject } from '../../utils/inspect';
import { makeProp } from '../../utils/props'; // --- Constants ---

var NO_FADE_PROPS = {
  name: '',
  enterClass: '',
  enterActiveClass: '',
  enterToClass: 'show',
  leaveClass: 'show',
  leaveActiveClass: '',
  leaveToClass: ''
};

var FADE_PROPS = _objectSpread(_objectSpread({}, NO_FADE_PROPS), {}, {
  enterActiveClass: 'fade',
  leaveActiveClass: 'fade'
}); // --- Props ---


export var props = {
  // Has no effect if `trans-props` provided
  appear: makeProp(PROP_TYPE_BOOLEAN, false),
  // Can be overridden by user supplied `trans-props`
  mode: makeProp(PROP_TYPE_STRING),
  // Only applicable to the built in transition
  // Has no effect if `trans-props` provided
  noFade: makeProp(PROP_TYPE_BOOLEAN, false),
  // For user supplied transitions (if needed)
  transProps: makeProp(PROP_TYPE_OBJECT)
}; // --- Main component ---
// @vue/component

export var BVTransition = /*#__PURE__*/extend({
  name: NAME_TRANSITION,
  functional: true,
  props: props,
  render: function render(h, _ref) {
    var children = _ref.children,
        data = _ref.data,
        props = _ref.props;
    var transProps = props.transProps;

    if (!isPlainObject(transProps)) {
      transProps = props.noFade ? NO_FADE_PROPS : FADE_PROPS;

      if (props.appear) {
        // Default the appear classes to equal the enter classes
        transProps = _objectSpread(_objectSpread({}, transProps), {}, {
          appear: true,
          appearClass: transProps.enterClass,
          appearActiveClass: transProps.enterActiveClass,
          appearToClass: transProps.enterToClass
        });
      }
    }

    transProps = _objectSpread(_objectSpread({
      mode: props.mode
    }, transProps), {}, {
      // We always need `css` true
      css: true
    });

    var dataCopy = _objectSpread({}, data);

    delete dataCopy.props;
    return h('transition', // Any transition event listeners will get merged here
    mergeData(dataCopy, {
      props: transProps
    }), children);
  }
});