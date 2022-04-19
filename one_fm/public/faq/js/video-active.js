(function ($) {
  "use strict";

  function video_active() {
    if ($(".video_list_area").length) {
      const list = [
        {
          className: ".artplayer-app",
          url: "img/home-tow/video-list/mov_bbb.mp4",
          title: "Google",
          poster: "img/home-tow/video-list/video-bg.jpg",
        },
        {
          className: ".artplayer-app2",
          url: "img/home-tow/video-list/mov_bbb.mp4",
          title: "Facebook",
          poster: "img/home-tow/video-list/video-bg-2.jpg",
        },
        {
          className: ".artplayer-app3",
          url: "img/home-tow/video-list/mov_bbb.mp4",
          title: "Facebook",
          poster: "img/home-tow/video-list/video-bg.jpg",
        },
        {
          className: ".artplayer-app4",
          url: "img/home-tow/video-list/mov_bbb.mp4",
          title: "Facebook",
          poster: "img/home-tow/video-list/video-bg-2.jpg",
        },
        {
          className: ".artplayer-app5",
          url: "img/home-tow/video-list/mov_bbb.mp4",
          title: "Facebook",
          poster: "img/home-tow/video-list/video-bg.jpg",
        },
        {
          className: ".artplayer-app6",
          url: "img/home-tow/video-list/mov_bbb.mp4",
          title: "Facebook",
          poster: "img/home-tow/video-list/video-bg-2.jpg",
        },
        {
          className: ".artplayer-app7",
          url: "img/home-tow/video-list/mov_bbb.mp4",
          title: "Facebook",
          poster: "img/home-tow/video-list/video-bg.jpg",
        },
        {
          className: ".artplayer-app8",
          url: "img/home-tow/video-list/mov_bbb.mp4",
          title: "Facebook",
          poster: "img/home-tow/video-list/video-bg-2.jpg",
        },
        {
          className: ".artplayer-app9",
          url: "img/home-tow/video-list/mov_bbb.mp4",
          title: "Facebook",
          poster: "img/home-tow/video-list/video-bg.jpg",
        },
        {
          className: ".artplayer-app10",
          url: "img/home-tow/video-list/mov_bbb.mp4",
          title: "Facebook",
          poster: "img/home-tow/video-list/video-bg-2.jpg",
        },
        {
          className: ".artplayer-app11",
          url: "img/home-tow/video-list/mov_bbb.mp4",
          title: "Facebook",
          poster: "img/home-tow/video-list/video-bg.jpg",
        },
        {
          className: ".artplayer-app12",
          url: "img/home-tow/video-list/mov_bbb.mp4",
          title: "Facebook",
          poster: "img/home-tow/video-list/video-bg.jpg",
        },
        {
          className: ".artplayer-app13",
          url: "img/home-tow/video-list/mov_bbb.mp4",
          title: "Facebook",
          poster: "img/home-tow/video-list/video-bg.jpg",
        },
        {
          className: ".artplayer-app14",
          url: "img/home-tow/video-list/mov_bbb.mp4",
          title: "Facebook",
          poster: "img/home-tow/video-list/video-bg.jpg",
        },
      ];

      list.forEach(function (e) {
        var art = new Artplayer({
          container: e.className,
          url: e.url,
          title: e.title,
          poster: e.poster,
          volume: 0.5,
          muted: false,
          autoplay: false,
          pip: true,
          autoSize: true,
          autoMini: false,
          screenshot: true,
          setting: true,
          loop: true,
          flip: true,
          rotate: true,
          playbackRate: true,
          aspectRatio: false,
          fullscreen: true,
          fullscreenWeb: true,
          subtitleOffset: true,
          miniProgressBar: true,
          localVideo: true,
          localSubtitle: true,
          networkMonitor: false,
          mutex: true,
          light: true,
          backdrop: true,
          isLive: false,
          theme: "#10b3d6",
          lang: navigator.language.toLowerCase(),
          // moreVideoAttr: {
          //   crossOrigin: "anonymous",
          // },
          contextmenu: [
            {
              html: "Custom menu",
              click: function (contextmenu) {
                console.info("You clicked on the custom menu");
                contextmenu.show = false;
              },
            },
          ],
          layers: [
            {
              html: `<img style="width: 100px" src="img/home-tow/video-list/video-bg.jpg">`,
              click: function () {
                console.info("You clicked on the custom layer");
              },
              style: {
                position: "absolute",
                top: "20px",
                right: "20px",
                opacity: ".9",
              },
            },
          ],
          quality: [
            {
              default: true,
              name: "SD 480P",
              url: "img/home-tow/video-list/mov_bbb.mp4",
            },
            {
              name: "HD 720P",
              url: "img/home-tow/video-list/mov_bbb.mp4",
            },
          ],
          thumbnails: {
            url: "img/home-tow/video-list/video-bg.jpg",
            number: 100,
            width: 160,
            height: 90,
            column: 10,
          },
          subtitle: {
            url: "img/home-tow/video-list/subtitle.srt",
            style: {
              color: "#03A9F4",
            },
            encoding: "utf-8",
            bilingual: true,
          },
          highlight: [
            {
              time: 60,
              text: "One more chance",
            },
            {
              time: 120,
              text: "谁でもいいはずなのに",
            },
            {
              time: 180,
              text: "夏の想い出がまわる",
            },
            {
              time: 240,
              text: "こんなとこにあるはずもないのに",
            },
            {
              time: 300,
              text: "终わり",
            },
          ],
          controls: [
            {
              position: "right",
              html: "Control",
              index: 10,
              click: function () {
                console.info("You clicked on the custom control");
              },
            },
          ],
          icons: {
            loading: '<img src="img/home-tow/video-list/ploading.gif">',
            state: '<ion-icon name="play"></ion-icon>',
          },
        });
      });

      $(document).on("click", function (e) {
        var el = e.target.nodeName,
          parent = e.target.parentNode;
        if (
          (el === "path" && videoControlClassCheck(parent.parentNode)) ||
          (el === "svg" && videoControlClassCheck(parent))
        ) {
          $(".video_list_area").toggleClass("theatermode");
        }
      });
      function videoControlClassCheck(parent) {
        return parent.className.indexOf("art-icon-fullscreenWeb") !== -1;
      }
    }
  }
  video_active();
  function Video_slide_player() {
    if ($(".video_slider_area").length) {
      var myPlayers = Array(
        videojs("player_1"),
        videojs("player_2"),
        videojs("player_3"),
        videojs("player_4"),
        videojs("player_5"),
        videojs("player_6")
      );
    }
  }
  Video_slide_player();

  function modal_player() {
    if ($(".video_popup_slider").length) {
      Array(
        videojs("modal_video_1"),
        videojs("modal_video_2"),
        videojs("modal_video_3"),
        videojs("modal_video_4"),
        videojs("modal_video_5"),
        videojs("modal_video_6"),
        videojs("modal_video_7"),
        videojs("modal_video_8"),
        videojs("modal_video_9"),
        {
          controls: true,
          autoplay: false,
          preload: "auto",
        }
      );
    }
  }
  modal_player();
})(jQuery);