import { IS_BROWSER } from '../../constants/env';
import { isNumber, isObject, isString } from '../../utils/inspect';
import { mathRound } from '../../utils/math';
import { toInteger } from '../../utils/number';
import { keys } from '../../utils/object';
import { getEventRoot } from '../../utils/get-event-root';
import { getInstanceFromDirective } from '../../utils/get-instance-from-directive';
import { BVScrollspy } from './helpers/bv-scrollspy.class'; // Key we use to store our instance

var BV_SCROLLSPY = '__BV_Scrollspy__'; // Pre-compiled regular expressions

var onlyDigitsRE = /^\d+$/;
var offsetRE = /^(auto|position|offset)$/; // Build a Scrollspy config based on bindings (if any)
// Arguments and modifiers take precedence over passed value config object

/* istanbul ignore next: not easy to test */

var parseBindings = function parseBindings(bindings)
/* istanbul ignore next: not easy to test */
{
  var config = {}; // If argument, assume element ID

  if (bindings.arg) {
    // Element ID specified as arg
    // We must prepend '#' to become a CSS selector
    config.element = "#".concat(bindings.arg);
  } // Process modifiers


  keys(bindings.modifiers).forEach(function (mod) {
    if (onlyDigitsRE.test(mod)) {
      // Offset value
      config.offset = toInteger(mod, 0);
    } else if (offsetRE.test(mod)) {
      // Offset method
      config.method = mod;
    }
  }); // Process value

  if (isString(bindings.value)) {
    // Value is a CSS ID or selector
    config.element = bindings.value;
  } else if (isNumber(bindings.value)) {
    // Value is offset
    config.offset = mathRound(bindings.value);
  } else if (isObject(bindings.value)) {
    // Value is config object
    // Filter the object based on our supported config options
    keys(bindings.value).filter(function (k) {
      return !!BVScrollspy.DefaultType[k];
    }).forEach(function (k) {
      config[k] = bindings.value[k];
    });
  }

  return config;
}; // Add or update Scrollspy on our element


var applyScrollspy = function applyScrollspy(el, bindings, vnode)
/* istanbul ignore next: not easy to test */
{
  if (!IS_BROWSER) {
    /* istanbul ignore next */
    return;
  }

  var config = parseBindings(bindings);

  if (el[BV_SCROLLSPY]) {
    el[BV_SCROLLSPY].updateConfig(config, getEventRoot(getInstanceFromDirective(vnode, bindings)));
  } else {
    el[BV_SCROLLSPY] = new BVScrollspy(el, config, getEventRoot(getInstanceFromDirective(vnode, bindings)));
  }
}; // Remove Scrollspy on our element

/* istanbul ignore next: not easy to test */


var removeScrollspy = function removeScrollspy(el)
/* istanbul ignore next: not easy to test */
{
  if (el[BV_SCROLLSPY]) {
    el[BV_SCROLLSPY].dispose();
    el[BV_SCROLLSPY] = null;
    delete el[BV_SCROLLSPY];
  }
};
/*
 * Export our directive
 */


export var VBScrollspy = {
  /* istanbul ignore next: not easy to test */
  bind: function bind(el, bindings, vnode) {
    applyScrollspy(el, bindings, vnode);
  },

  /* istanbul ignore next: not easy to test */
  inserted: function inserted(el, bindings, vnode) {
    applyScrollspy(el, bindings, vnode);
  },

  /* istanbul ignore next: not easy to test */
  update: function update(el, bindings, vnode) {
    if (bindings.value !== bindings.oldValue) {
      applyScrollspy(el, bindings, vnode);
    }
  },

  /* istanbul ignore next: not easy to test */
  componentUpdated: function componentUpdated(el, bindings, vnode) {
    if (bindings.value !== bindings.oldValue) {
      applyScrollspy(el, bindings, vnode);
    }
  },

  /* istanbul ignore next: not easy to test */
  unbind: function unbind(el) {
    removeScrollspy(el);
  }
};