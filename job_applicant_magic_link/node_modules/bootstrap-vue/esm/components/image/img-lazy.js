var _watch;

function ownKeys(object, enumerableOnly) { var keys = Object.keys(object); if (Object.getOwnPropertySymbols) { var symbols = Object.getOwnPropertySymbols(object); enumerableOnly && (symbols = symbols.filter(function (sym) { return Object.getOwnPropertyDescriptor(object, sym).enumerable; })), keys.push.apply(keys, symbols); } return keys; }

function _objectSpread(target) { for (var i = 1; i < arguments.length; i++) { var source = null != arguments[i] ? arguments[i] : {}; i % 2 ? ownKeys(Object(source), !0).forEach(function (key) { _defineProperty(target, key, source[key]); }) : Object.getOwnPropertyDescriptors ? Object.defineProperties(target, Object.getOwnPropertyDescriptors(source)) : ownKeys(Object(source)).forEach(function (key) { Object.defineProperty(target, key, Object.getOwnPropertyDescriptor(source, key)); }); } return target; }

function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

import { extend } from '../../vue';
import { NAME_IMG_LAZY } from '../../constants/components';
import { HAS_INTERACTION_OBSERVER_SUPPORT } from '../../constants/env';
import { MODEL_EVENT_NAME_PREFIX } from '../../constants/events';
import { PROP_TYPE_BOOLEAN, PROP_TYPE_NUMBER_STRING, PROP_TYPE_STRING } from '../../constants/props';
import { concat } from '../../utils/array';
import { requestAF } from '../../utils/dom';
import { identity } from '../../utils/identity';
import { toInteger } from '../../utils/number';
import { omit } from '../../utils/object';
import { makeProp, makePropsConfigurable, pluckProps } from '../../utils/props';
import { VBVisible } from '../../directives/visible/visible';
import { BImg, props as BImgProps } from './img'; // --- Constants ---

var MODEL_PROP_NAME_SHOW = 'show';
var MODEL_EVENT_NAME_SHOW = MODEL_EVENT_NAME_PREFIX + MODEL_PROP_NAME_SHOW; // --- Props ---

var imgProps = omit(BImgProps, ['blank']);
export var props = makePropsConfigurable(_objectSpread(_objectSpread({}, imgProps), {}, _defineProperty({
  blankHeight: makeProp(PROP_TYPE_NUMBER_STRING),
  // If `null`, a blank image is generated
  blankSrc: makeProp(PROP_TYPE_STRING, null),
  blankWidth: makeProp(PROP_TYPE_NUMBER_STRING),
  // Distance away from viewport (in pixels)
  // before being considered "visible"
  offset: makeProp(PROP_TYPE_NUMBER_STRING, 360)
}, MODEL_PROP_NAME_SHOW, makeProp(PROP_TYPE_BOOLEAN, false))), NAME_IMG_LAZY); // --- Main component ---
// @vue/component

export var BImgLazy = /*#__PURE__*/extend({
  name: NAME_IMG_LAZY,
  directives: {
    'b-visible': VBVisible
  },
  props: props,
  data: function data() {
    return {
      isShown: this[MODEL_PROP_NAME_SHOW]
    };
  },
  computed: {
    computedSrc: function computedSrc() {
      var blankSrc = this.blankSrc;
      return !blankSrc || this.isShown ? this.src : blankSrc;
    },
    computedBlank: function computedBlank() {
      return !(this.isShown || this.blankSrc);
    },
    computedWidth: function computedWidth() {
      var width = this.width;
      return this.isShown ? width : this.blankWidth || width;
    },
    computedHeight: function computedHeight() {
      var height = this.height;
      return this.isShown ? height : this.blankHeight || height;
    },
    computedSrcset: function computedSrcset() {
      var srcset = concat(this.srcset).filter(identity).join(',');
      return srcset && (!this.blankSrc || this.isShown) ? srcset : null;
    },
    computedSizes: function computedSizes() {
      var sizes = concat(this.sizes).filter(identity).join(',');
      return sizes && (!this.blankSrc || this.isShown) ? sizes : null;
    }
  },
  watch: (_watch = {}, _defineProperty(_watch, MODEL_PROP_NAME_SHOW, function (newValue, oldValue) {
    if (newValue !== oldValue) {
      // If `IntersectionObserver` support is not available, image is always shown
      var visible = HAS_INTERACTION_OBSERVER_SUPPORT ? newValue : true;
      this.isShown = visible; // Ensure the show prop is synced (when no `IntersectionObserver`)

      if (newValue !== visible) {
        this.$nextTick(this.updateShowProp);
      }
    }
  }), _defineProperty(_watch, "isShown", function isShown(newValue, oldValue) {
    // Update synched show prop
    if (newValue !== oldValue) {
      this.updateShowProp();
    }
  }), _watch),
  mounted: function mounted() {
    var _this = this;

    // If `IntersectionObserver` is not available, image is always shown
    this.$nextTick(function () {
      _this.isShown = HAS_INTERACTION_OBSERVER_SUPPORT ? _this[MODEL_PROP_NAME_SHOW] : true;
    });
  },
  methods: {
    updateShowProp: function updateShowProp() {
      this.$emit(MODEL_EVENT_NAME_SHOW, this.isShown);
    },
    doShow: function doShow(visible) {
      var _this2 = this;

      // If IntersectionObserver is not supported, the callback
      // will be called with `null` rather than `true` or `false`
      if ((visible || visible === null) && !this.isShown) {
        // In a `requestAF()` to render the `blank` placeholder properly
        // for fast loading images in some browsers (i.e. Firefox)
        requestAF(function () {
          _this2.isShown = true;
        });
      }
    }
  },
  render: function render(h) {
    var directives = [];

    if (!this.isShown) {
      var _modifiers;

      // We only add the visible directive if we are not shown
      directives.push({
        // Visible directive will silently do nothing if
        // `IntersectionObserver` is not supported
        name: 'b-visible',
        // Value expects a callback (passed one arg of `visible` = `true` or `false`)
        value: this.doShow,
        modifiers: (_modifiers = {}, _defineProperty(_modifiers, "".concat(toInteger(this.offset, 0)), true), _defineProperty(_modifiers, "once", true), _modifiers)
      });
    }

    return h(BImg, {
      directives: directives,
      props: _objectSpread(_objectSpread({}, pluckProps(imgProps, this.$props)), {}, {
        // Computed value props
        src: this.computedSrc,
        blank: this.computedBlank,
        width: this.computedWidth,
        height: this.computedHeight,
        srcset: this.computedSrcset,
        sizes: this.computedSizes
      })
    });
  }
});