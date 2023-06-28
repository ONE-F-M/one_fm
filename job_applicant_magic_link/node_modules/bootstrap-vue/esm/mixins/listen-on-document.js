import { extend } from '../vue';
import { IS_BROWSER } from '../constants/env';
import { EVENT_OPTIONS_NO_CAPTURE } from '../constants/events';
import { arrayIncludes } from '../utils/array';
import { eventOn, eventOff } from '../utils/events';
import { keys } from '../utils/object'; // --- Constants ---

var PROP = '$_documentListeners'; // --- Mixin ---
// @vue/component

export var listenOnDocumentMixin = extend({
  created: function created() {
    // Define non-reactive property
    // Object of arrays, keyed by event name,
    // where value is an array of callbacks
    this[PROP] = {};
  },
  beforeDestroy: function beforeDestroy() {
    var _this = this;

    // Unregister all registered listeners
    keys(this[PROP] || {}).forEach(function (event) {
      _this[PROP][event].forEach(function (callback) {
        _this.listenOffDocument(event, callback);
      });
    });
    this[PROP] = null;
  },
  methods: {
    registerDocumentListener: function registerDocumentListener(event, callback) {
      if (this[PROP]) {
        this[PROP][event] = this[PROP][event] || [];

        if (!arrayIncludes(this[PROP][event], callback)) {
          this[PROP][event].push(callback);
        }
      }
    },
    unregisterDocumentListener: function unregisterDocumentListener(event, callback) {
      if (this[PROP] && this[PROP][event]) {
        this[PROP][event] = this[PROP][event].filter(function (cb) {
          return cb !== callback;
        });
      }
    },
    listenDocument: function listenDocument(on, event, callback) {
      on ? this.listenOnDocument(event, callback) : this.listenOffDocument(event, callback);
    },
    listenOnDocument: function listenOnDocument(event, callback) {
      if (IS_BROWSER) {
        eventOn(document, event, callback, EVENT_OPTIONS_NO_CAPTURE);
        this.registerDocumentListener(event, callback);
      }
    },
    listenOffDocument: function listenOffDocument(event, callback) {
      if (IS_BROWSER) {
        eventOff(document, event, callback, EVENT_OPTIONS_NO_CAPTURE);
      }

      this.unregisterDocumentListener(event, callback);
    }
  }
});