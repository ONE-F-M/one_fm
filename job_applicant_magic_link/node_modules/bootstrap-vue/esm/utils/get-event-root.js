export var getEventRoot = function getEventRoot(vm) {
  return vm.$root.$options.bvEventRoot || vm.$root;
};