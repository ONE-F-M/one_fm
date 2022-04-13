(function ($) {
  "use strict";

  function DataTable() {
    if ($("#dtMaterialDesignExample").length) {
      $(document).ready(function () {
        $("#dtMaterialDesignExample").DataTable();
        $("#dtMaterialDesignExample_wrapper")
          .find("label")
          .each(function () {
            $(this).parent().append($(this).children());
          });
        $("#dtMaterialDesignExample_wrapper .dataTables_filter")
          .find("input")
          .each(function () {
            const $this = $(this);
            $this.attr("placeholder", "Search");
            $this.removeClass("form-control-sm");
          });
        $("#dtMaterialDesignExample_wrapper .dataTables_length").addClass(
          "d-flex flex-row"
        );
        $("#dtMaterialDesignExample_wrapper .dataTables_filter").addClass(
          "md-form"
        );
        $("#dtMaterialDesignExample_wrapper select").removeClass(
          "custom-select custom-select-sm form-control form-control-sm"
        );
        $("#dtMaterialDesignExample_wrapper select").addClass("mdb-select");
        $("#dtMaterialDesignExample_wrapper .dataTables_filter")
          .find("label")
          .remove();
      });
    }
  }

  DataTable();

  $(document).ready(function () {
    if ( $(".gallery-top").length ) {
    $(".gallery-top")
      .slick({
        slidesToShow: 1,
        slidesToScroll: 1,
        arrows: false,
        fade: true,
        infinite: false,
        asNavFor: ".gallery-thumbs",
      })
      .on("beforeChange", function (event, slick, currentSlide, nextSlide) {
        $(".gallery-top .slick-current video").attr(
          "src",
          $(".gallery-top .slick-current video").attr("src")
        );
        $(".gallery-top .slick-current .video-js").removeClass("vjs-playing");
      });
    $(".gallery-thumbs")
      .slick({
        slidesToShow: 4,
        slidesToScroll: 1,
        vertical: false,
        asNavFor: ".gallery-top",
        dots: false,
        focusOnSelect: true,
        arrows: true,
        infinite: false,
        swipeToSlide: true,
        prevArrow: $(".prev"),
        nextArrow: $(".next"),
        responsive: [
          {
            breakpoint: 992,
            settings: {
              vertical: false,
              slidesToShow: 3,
            },
          },
          {
            breakpoint: 768,
            settings: {
              vertical: false,
              slidesToShow: 3,
            },
          },
          {
            breakpoint: 650,
            settings: {
              vertical: false,
              slidesToShow: 2,
            },
          },
          {
            breakpoint: 480,
            settings: {
              vertical: false,
              slidesToShow: 1,
            },
          },
        ],
      })
      .on("beforeChange", function (event, slick, currentSlide, nextSlide) {
        $(".gallery-thumbs .slick-current video").attr(
          "src",
          $(".gallery-thumbs .slick-current video").attr("src")
        );
        $(".gallery-thumbs .slick-current .video-js").removeClass(
          "vjs-playing"
        );
      });
  }
  });
  $(".slick-track").css("max-width", $(window).width());

  /*--------------- video js--------*/
  function video() {
    if ($("#inline-popups").length) {
      $("#inline-popups").magnificPopup({
        delegate: "a",
        removalDelay: 500, //delay removal by X to allow out-animation
        mainClass: "mfp-no-margins mfp-with-zoom",
        preloader: false,
        midClick: true,
      });
    }
  }

  video();
  if ($("#small-dialog").lenght) {
    $(window).on("load", function () {
      document.getElementById("small-dialog").click();
    });
  }

  if ( $('.popup_slick').length ) {
    $(".popup_slick").slick({
      dots: false,
      infinite: false,
      speed: 300,
      slidesToShow: 4,
      slidesToScroll: 1,
      prevArrow: ".prev1",
      nextArrow: ".next1",
      responsive: [
        {
          breakpoint: 1024,
          settings: {
            slidesToShow: 3,
            slidesToScroll: 3,
            dots: false,
          },
        },
        {
          breakpoint: 600,
          settings: {
            slidesToShow: 2,
            slidesToScroll: 2,
          },
        },
        {
          breakpoint: 480,
          settings: {
            slidesToShow: 1,
            slidesToScroll: 1,
          },
        },
      ],
    });
  }

  $(".modal").on("shown.bs.modal", function (e) {
    $(".modal_slider")
      .not(".slick-initialized")
      .slick({
        slidesToScroll: 1,
        dots: false,
        focusOnSelect: true,
        arrows: true,
        infinite: false,
        swipeToSlide: false,
        centerMode: true,
        asNavFor: ".modal_carousel",
        slidesToShow: 3,
        prevArrow: ".prev_modal",
        nextArrow: ".next_modal",
        responsive: [
          {
            breakpoint: 767,
            settings: {
              vertical: false,
              centerPadding: "0px",
            },
          },
          {
            breakpoint: 575,
            settings: {
              vertical: false,
              centerPadding: "0px",
              slidesToShow: 1,
            },
          },
        ],
      })
      .on("beforeChange", function (event, slick, currentSlide, nextSlide) {
        $(".modal_slider_css .slick-current video").attr(
          "src",
          $(".modal_slider_css .slick-current video").attr("src")
        );
        $(".modal_slider_css .slick-current .video-js").removeClass(
          "vjs-playing"
        );
      });
    $(".close").click(function () {
      $(".modal_slider_css .slick-current video").attr(
        "src",
        $(".modal_slider_css .slick-current video").attr("src")
      );
      $(".modal_slider_css .slick-current .video-js").removeClass(
        "vjs-playing"
      );
    });
    $(".modal_carousel")
      .not(".slick-initialized")
      .slick({
        slidesToShow: 4,
        slidesToScroll: 1,
        vertical: false,
        asNavFor: ".modal_slider",
        dots: false,
        focusOnSelect: true,
        arrows: true,
        infinite: false,
        swipeToSlide: true,
        prevArrow: $(".prev_car"),
        nextArrow: $(".next_car"),
        centerMode: false,
        responsive: [
          {
            breakpoint: 1199,
            settings: {
              vertical: false,
              slidesToShow: 4,
            },
          },
          {
            breakpoint: 991,
            settings: {
              vertical: false,
              slidesToShow: 2,
            },
          },
          {
            breakpoint: 767,
            settings: {
              vertical: false,
              slidesToShow: 2,
              centerMode: false,
            },
          },
          {
            breakpoint: 575,
            settings: {
              vertical: false,
              slidesToShow: 1,
              centerMode: false,
            },
          },
        ],
      })
      .on("beforeChange", function (event, slick, currentSlide, nextSlide) {
        $(".modal_slider_css .slick-current video").attr(
          "src",
          $(".modal_slider_css .slick-current video").attr("src")
        );
        $(".modal_slider_css .slick-current .video-js").removeClass(
          "vjs-playing"
        );
      });
  });

  $('.video_list a[data-toggle="tab"]').on("shown.bs.tab", function (e) {
    $(".tab-pane:not(.active)").each(function (idx, el) {
      $("video")[0].pause();
      $("video")[1].pause();
      $("video")[2].pause();
      $("video")[3].pause();
      $("video")[4].pause();
      $("video")[5].pause();
      $("video")[6].pause();
      $("video")[7].pause();
      $("video")[8].pause();
      $("video")[9].pause();
      $("video")[10].pause();
      $("video")[11].pause();
      $("video")[12].pause();
      $("video")[13].pause();
    });
  });

  $(document).ready(function () {
    $(".item_modal_box video")
      .mouseenter(function () {
        $(this).get(0).play();
      })
      .mouseleave(function () {
        $(this).get(0).pause();
      });
  });

  $(document).ready(function () {
    $(".divs div").each(function (e) {
      if (e != 0) $(this).hide();
    });

    $(".next").click(function () {
      //$(".list li").addClass("active");
      if (($(".divs div:visible").next().length = !0)) {
        $(".divs div:visible").next().show().prev().hide();
        var activeClass = "." + $(".divs div:visible").attr("class");
        $(".list").find("li").removeClass("active show");
        $(".list").find(activeClass).addClass("active show");
      } else {
        $(".divs div:visible").hide();
        $(".divs div:first").show();
        $(".list").find("li").removeClass("active show");
        $(".list li:first").addClass("active show");
      }
      return false;
    });

    $(".prev").click(function () {
      if (($(".divs div:visible").prev().length = !0)) {
        $(".divs div:visible").prev().show().next().hide();
        var activeClass = "." + $(".divs div:visible").attr("class");
        $(".list").find("li").removeClass("active show");
        $(".list").find(activeClass).addClass("active show");
      } else {
        $(".divs div:visible").hide();
        $(".divs div:last").show();
        $(".list").find("li").removeClass("active show");
        $(".list li:last").addClass("active show");
      }
      return false;
    });
    $(".close_btn").on("click", function () {
      $(".nav.list li").removeClass("active show");
      $(".nav.list li .dropdown-menu").removeClass("show");
      $("body").removeClass("blur");
    });
    $(".nav.list li .img_pointing").on("click", function () {
      $("body").toggleClass("blur");
    });
    var selector, elems, makeActive;

    selector = ".nav.list li";

    elems = document.querySelectorAll(selector);

    makeActive = function () {
      for (var i = 0; i < elems.length; i++)
        elems[i].classList.remove("active");

      this.classList.add("active");
    };

    for (var i = 0; i < elems.length; i++)
      elems[i].addEventListener("mousedown", makeActive);

    if ($(".nav.list li").hasClass("active")) {
      $("body").addClass("blur");
    }
  });
})(jQuery);