import { isVue3 } from '../vue';
var registry = null;

if (isVue3) {
  registry = new WeakMap();
}

export var registerElementToInstance = function registerElementToInstance(element, instance) {
  if (!isVue3) {
    return;
  }

  registry.set(element, instance);
};
export var removeElementToInstance = function removeElementToInstance(element) {
  if (!isVue3) {
    return;
  }

  registry.delete(element);
};
export var getInstanceFromElement = function getInstanceFromElement(element) {
  if (!isVue3) {
    return element.__vue__;
  }

  var currentElement = element;

  while (currentElement) {
    if (registry.has(currentElement)) {
      /* istanbul ignore next */
      return registry.get(currentElement);
    }

    currentElement = currentElement.parentNode;
  }

  return null;
};