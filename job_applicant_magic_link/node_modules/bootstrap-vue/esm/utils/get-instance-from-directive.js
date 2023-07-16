import { isVue3 } from '../vue';
export var getInstanceFromDirective = function getInstanceFromDirective(vnode, bindings) {
  return isVue3 ? bindings.instance : vnode.context;
};