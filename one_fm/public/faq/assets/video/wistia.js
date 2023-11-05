(function (root, factory) {
  if(typeof define === 'function' && define.amd) {
    define(['video.js'], function(videojs){
      return (root.WistiaTech = factory(videojs));
    });
  } else if(typeof module === 'object' && module.exports) {
    module.exports = (root.WistiaTech = factory(require('video.js')));
  } else {
    root.WistiaTech = factory(root.videojs);
  }
}(this, function(videojs) {
  'use strict';

  var WistiaState = {
    UNSTARTED: -1,
    ENDED: 0,
    PLAYING: 1,
    PAUSED: 2,
    BUFFERING: 3
  };

  var Tech = videojs.getComponent('Tech');

  var WistiaTech = videojs.extend(Tech, {
    constructor: function(options, ready) {
      Tech.call(this, options, ready);
      this.setSrc(this.options_.source.src, true);
    },

    dispose: function() {
      this.wistiaVideo.remove();
      this.el_.parentNode.removeChild(this.el_);
    },

    createEl: function() {
      var protocol = (document.location.protocol === 'file:') ? 'http:' : document.location.protocol;
      this.wistia = {};
      this.wistiaInfo = {};
      this.baseUrl = protocol + '//fast.wistia.com/embed/iframe/';
      this.videoOptions = WistiaTech.parseUrl(this.options_.source.src);
      this.videoId = this.videoOptions.videoId;
      this.playedId = this.options_.playerId;

      var div = videojs.createEl('div', {
        id: this.videoId,
        className: this.videoOptions.classString,
        width: this.options_.width || "100%",
        height: this.options_ .height || "100%"
      });

      this.wistiaScriptElement = videojs.createEl('script', {
        src: protocol + "//fast.wistia.com/assets/external/E-v1.js"
      });

      var divWrapper = document.createElement('div');
      divWrapper.setAttribute('id', 'wistia-wrapper');
      divWrapper.appendChild(div);

      var divBlocker = document.createElement('div');
      divBlocker.setAttribute('class', 'vjs-iframe-blocker');
      divBlocker.setAttribute('style', 'position:absolute;top:0;left:0;width:100%;height:100%');

      divWrapper.appendChild(divBlocker);
      div.insertBefore(this.wistiaScriptElement, div.firstChild);
      this.initPlayer();

      return divWrapper;
    },

    initPlayer: function() {
      var self = this;
      var wistiaVideoID = WistiaTech.parseUrl(this.options_.source.src).videoId;

      self.wistiaInfo = {
        state: WistiaState.UNSTARTED,
        volume: 1,
        muted: false,
        muteVolume: 1,
        time: 0,
        duration: 0,
        buffered: 0,
        url: self.baseUrl + self.videoId,
        error: null
      };

      this.wistiaScriptElement.onload = function() {
        self.wistiaVideo = Wistia.api(self.videoId);
        window._wq = window._wq || [];

        var videos = {};
        videos[self.videoId] = function(video) {
          self.wistiaVideo = video;
          self.onLoad();
        };

        window._wq.push(videos);
      };
    },

    ended: function() {
      return (this.wistiaInfo.state === WistiaState.ENDED);
    },

    onLoad: function() {
      this.wistiaInfo = {
        state: WistiaState.UNSTARTED,
        volume: 1,
        muted: false,
        muteVolume: 1,
        time: 0,
        duration: this.wistiaVideo.duration(),
        buffered: 0,
        url: this.baseUrl + this.videoId,
        error: null
      };

      var self = this;

      this.wistiaVideo.hasData(function() {
        self.onReady();
      });

      this.wistiaVideo.embedded(function() {
        var players = videojs.getPlayers();
        if (players) {
          var player = players[this.playedId];
          if (player && player.controls()) {
            var videos = this.player_.el_.getElementsByTagName('video');
            if (videos.length) {
              videos[0].style['pointerEvents'] = 'none';
            }
          }
        }
      }.bind(this));

      this.wistiaVideo.bind('pause', function() {
        self.onPause();
      });

      this.wistiaVideo.bind('play', function() {
        self.onPlay();
      });

      this.wistiaVideo.bind('seek', function(currentTime, lastTime) {
        self.onSeek({seconds: currentTime});
      });

      this.wistiaVideo.bind('secondchange', function(s) {
        self.wistiaInfo.time = s;
        self.player_.trigger('timeupdate');
      });

      this.wistiaVideo.bind('end', function(t) {
        self.onFinish();
      });

    },

    onReady: function(){
      this.isReady_ = true;
      this.triggerReady();
      this.trigger('loadedmetadata');

      if (this.startMuted) {
        this.setMuted(true);
        this.startMuted = false;
      }

      this.wistiaInfo.duration = this.wistiaVideo.duration();
    },

    /* TODO: Unused? */
    onLoadProgress: function(data) {
      var durationUpdate = !this.wistiaInfo.duration;
      this.wistiaInfo.duration = data.duration;
      this.wistiaInfo.buffered = data.percent;
      this.trigger('progress');
      if (durationUpdate) this.trigger('durationchange');
    },

    /* TODO: Unused? */
    onPlayProgress: function(data) {
      this.wistiaInfo.time = data.seconds;
      this.wistiaVideo.time(this.wistiaInfo.time);
      this.trigger('timeupdate');
    },

    onPlay: function() {
      this.wistiaInfo.state = WistiaState.PLAYING;
      this.trigger('play');
    },

    onPause: function() {
      this.wistiaInfo.state = WistiaState.PAUSED;
      this.trigger('pause');
    },

    onFinish: function() {
      this.wistiaInfo.state = WistiaState.ENDED;
      this.trigger('ended');
    },

    onSeek: function(data) {
      this.trigger('seeking');
      this.wistiaInfo.time = data.seconds;
      this.wistiaVideo.time(this.wistiaInfo.time);
      this.trigger('timeupdate');
      this.trigger('seeked');
    },

    onError: function(error){
      this.error = error;
      this.trigger('error');
    },

    error: function() {
      switch (this.errorNumber) {
        case 2:
          return { code: 'Unable to find the video' };

        case 5:
          return { code: 'Error while trying to play the video' };

        case 100:
          return { code: 'Unable to find the video' };

        case 101:
        case 150:
          return { code: 'Playback on other Websites has been disabled by the video owner.' };
      }

      return { code: 'Wistia unknown error (' + this.errorNumber + ')' };
    },

    playbackRate: function() {
      return this.suggestedRate ? this.suggestedRate : 1;
    },

    setPlaybackRate: function(suggestedRate) {
      if (!this.wistiaVideo) {
        return;
      }
      var d = this.wistiaVideo.playbackRate(suggestedRate);
      this.suggestedRate = suggestedRate;
      this.trigger('ratechange');
    },

    src: function(src) {
      if(src) {
        this.setSrc({ src: src });
      }
      return this.source;
    },

    setSrc: function(source) {
      if(!source || !source.src) {
        return;
      }

      this.source = source;
      this.videoOptions = WistiaTech.parseUrl(source.src);
      this.wistiaVideo.replaceWith(this.videoOptions.videoId, this.videoOptions.options);
    },

    supportsFullScreen: function() {
      return true;
    },

    load: function() {},

    play: function() {
      this.wistiaVideo.play();
    },

    pause: function() {
      this.wistiaVideo.pause();
    },

    paused: function() {
      return this.wistiaInfo.state !== WistiaState.PLAYING &&
             this.wistiaInfo.state !== WistiaState.BUFFERING;
    },

    currentTime: function() {
      return this.wistiaInfo.time || 0;
    },

    setCurrentTime: function(seconds) {
      this.wistiaVideo.time(seconds);
      this.player_.trigger('timeupdate');
    },

    duration: function() {
      return this.wistiaInfo.duration || 0;
    },

    buffered: function() {
      return videojs.createTimeRange(0, (this.wistiaInfo.buffered * this.wistiaInfo.duration) || 0);
    },

    volume: function() {
      return (this.wistiaInfo.muted) ? this.wistiaInfo.muteVolume : this.wistiaInfo.volume;
    },

    setVolume: function(percentAsDecimal) {
      this.wistiaInfo.volume = percentAsDecimal;
      this.wistiaVideo.volume(percentAsDecimal);
      this.player_.trigger('volumechange');
    },

    currentSrc: function() {
      return this.el_.src;
    },

    muted: function() {
      return this.wistiaInfo.muted || false;
    },

    setMuted: function(muted) {
      if(muted) {
        this.wistiaInfo.muteVolume = this.wistiaInfo.volume;
        this.setVolume(0);
      } else {
        this.setVolume(this.wistiaInfo.muteVolume);
      }

      this.wistiaInfo.muted = muted;
      this.player_.trigger('volumechange');
    }
  });

  WistiaTech.isSupported = function() {
    return true;
  };

  WistiaTech.canPlaySource = function(e) {
    return (e.type === 'video/wistia');
  };

  WistiaTech.parseUrl = function(url) {
    var result = {
      videoId: null,
      classes: [],
      classString: '',
      options: {}
    };

    var videoOptions = {};

    var regex = regex = /^.*(wistia\.com\/)(embed\/iframe\/|medias\/)([A-z0-9]+)/;
    var match = url.match(regex);

    if(match) {
      result.videoId = match[3];
    }

    var classes = [];
    classes.push('vjs-tech');
    classes.push('wistia_embed');
    classes.push('wistia_async_' + result.videoId);

    var options = {};
    options['wmode'] = 'transparent';

    if(url) {
      var playerColorMatch = url.match(/playerColor=([#a-fA-f0-9]+)/);
      if(playerColorMatch) {
        videoOptions.playerColor = playerColorMatch[1];
      }

      var playbarMatch = url.match(/playbar=(true|false)/);
      if (playbarMatch) {
        videoOptions.playbar = playbarMatch[1];
      }

      var playButtonMatch = url.match(/playButton=(true|false)/);
      if (playButtonMatch) {
        videoOptions.playButton = playButtonMatch[1];
      }

      var smallPlayButtonMatch = url.match(/smallPlayButton=(true|false)/);
      if (smallPlayButtonMatch) {
        videoOptions.smallPlayButton = smallPlayButtonMatch[1];
      }

      var volumeControlMatch = url.match(/volumeControl=(true|false)/);
      if (volumeControlMatch) {
        videoOptions.volumeControl = volumeControlMatch[1];
      }

      var fullscreenButtonMatch = url.match(/fullscreenButton=(true|false)/);
      if (fullscreenButtonMatch) {
        videoOptions.fullscreenButton = fullscreenButtonMatch[1];
      }

      var controlsVisibleMatch = url.match(/controlsVisibleOnLoad=(true|false)/);
      if(controlsVisibleMatch) {
        videoOptions.controls = controlsVisibleMatch[1];
      }

      var chromelessMatch = url.match(/chromeless=(true|false)/);
      if (chromelessMatch) {
        videoOptions.chromeless = chromelessMatch[1];
      }

      var autoPlayMatch = url.match(/autoplay=(true|false)/);
      if(autoPlayMatch) {
        videoOptions.autoplay = autoPlayMatch[1];
      }

      var mutedMatch = url.match(/muted=(true|false)/);
      if(mutedMatch) {
        videoOptions.muted = true;
      }

      var volumeMatch = url.match(/volume=([0-9]+)/);
      if(volumeMatch) {
        videoOptions.volume = volumeMatch[1];
      }

      var endVideoBehaviorMatch = url.match(/endVideoBehavior=(loop|default|reset)/);
      if(endVideoBehaviorMatch) {
        videoOptions.endVideoBehavior = endVideoBehaviorMatch[1];
      }
    }

    var color = videoOptions.playerColor;
    if(color && color.substring(0, 1) === '#') {
      videoOptions.playerColor = color.substring(1);
    }

    if (videoOptions.chromeless) {
      options['chromeless'] = videoOptions.chromeless;
    }

    if (videoOptions.playbar) {
      options['playbar'] = videoOptions.playbar;
    }

    if (videoOptions.playButton) {
      options['playButton'] = videoOptions.playButton;
    }

    if (videoOptions.smallPlayButton) {
      options['smallPlayButton'] = videoOptions.smallPlayButton;
    }

    if (videoOptions.volumeControl) {
      options['volumeControl'] = videoOptions.volumeControl;
    }

    if (videoOptions.fullscreenButton) {
      options['fullscreenButton'] = videoOptions.fullscreenButton;
    }

    if(videoOptions.controls) {
      options['controlsVisibleOnLoad'] = videoOptions.controls;
    }

    if(videoOptions.playerColor) {
      options['playerColor'] = videoOptions.playerColor;
    }

    if(videoOptions.autoplay) {
      options['autoPlay'] = videoOptions.autoplay;
    }

    if(videoOptions.volume !== false) {
      options['volume'] = videoOptions.volume || 1;
    }

    if(videoOptions.muted) {
      options['volume'] = 0;
    }

    if(videoOptions.loop) {
      videoOptions.endVideoBehavior = 'loop';
    }

    if(videoOptions.endVideoBehavior) {
      options['endVideoBehavior'] = videoOptions.endVideoBehavior;
    }

    var keys = Object.keys(options);
    var classString = classes.join(' ') + ' ';
    for(var i = 0; i < keys.length; i++) {
      var key = keys[i];
      var value = options[key];
      classString += key + '=' + value + '&';
    }
    classString = classString.replace(/&+$/,'');

    result.classes = classes;
    result.classString = classString;
    result.options = options;

    return result;
  };

  videojs.registerTech('Wistia', WistiaTech);
}));
