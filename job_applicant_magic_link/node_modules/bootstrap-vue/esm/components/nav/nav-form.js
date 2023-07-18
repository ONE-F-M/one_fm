function ownKeys(object, enumerableOnly) { var keys = Object.keys(object); if (Object.getOwnPropertySymbols) { var symbols = Object.getOwnPropertySymbols(object); enumerableOnly && (symbols = symbols.filter(function (sym) { return Object.getOwnPropertyDescriptor(object, sym).enumerable; })), keys.push.apply(keys, symbols); } return keys; }

function _objectSpread(target) { for (var i = 1; i < arguments.length; i++) { var source = null != arguments[i] ? arguments[i] : {}; i % 2 ? ownKeys(Object(source), !0).forEach(function (key) { _defineProperty(target, key, source[key]); }) : Object.getOwnPropertyDescriptors ? Object.defineProperties(target, Object.getOwnPropertyDescriptors(source)) : ownKeys(Object(source)).forEach(function (key) { Object.defineProperty(target, key, Object.getOwnPropertyDescriptor(source, key)); }); } return target; }

function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

import { extend, mergeData } from '../../vue';
import { NAME_NAV_FORM } from '../../constants/components';
import { PROP_TYPE_ARRAY_OBJECT_STRING } from '../../constants/props';
import { omit, sortKeys } from '../../utils/object';
import { makeProp, makePropsConfigurable, pluckProps } from '../../utils/props';
import { BForm, props as BFormProps } from '../form/form'; // --- Props ---

var formProps = omit(BFormProps, ['inline']);
export var props = makePropsConfigurable(sortKeys(_objectSpread(_objectSpread({}, formProps), {}, {
  formClass: makeProp(PROP_TYPE_ARRAY_OBJECT_STRING)
})), NAME_NAV_FORM); // --- Main component ---
// @vue/component

export var BNavForm = /*#__PURE__*/extend({
  name: NAME_NAV_FORM,
  functional: true,
  props: props,
  render: function render(h, _ref) {
    var props = _ref.props,
        data = _ref.data,
        children = _ref.children,
        listeners = _ref.listeners;
    var $form = h(BForm, {
      class: props.formClass,
      props: _objectSpread(_objectSpread({}, pluckProps(formProps, props)), {}, {
        inline: true
      }),
      attrs: data.attrs,
      on: listeners
    }, children);
    return h('li', mergeData(omit(data, ['attrs', 'on']), {
      staticClass: 'form-inline'
    }), [$form]);
  }
});