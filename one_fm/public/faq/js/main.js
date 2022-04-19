(function ($) {
  "use strict";

  //*=============menu sticky js =============*//
  var $window = $(window);
  var didScroll,
    lastScrollTop = 0,
    delta = 5,
    $mainNav = $(".sticky-nav"),
    $body = $("body"),
    $mainNavHeight = $mainNav.outerHeight() + 15,
    scrollTop;

  $window.on("scroll", function () {
    didScroll = true;
    scrollTop = $(this).scrollTop();
  });

  setInterval(function () {
    if (didScroll) {
      if (Math.abs(lastScrollTop - scrollTop) <= delta) {
        return;
      }
      if (scrollTop > lastScrollTop && scrollTop > $mainNavHeight) {
        $mainNav
          .removeClass("fadeInDown")
          .addClass("fadeInUp")
          .css("top", -$mainNavHeight);
        $body.removeClass("remove").addClass("add");
      } else {
        if (scrollTop + $(window).height() < $(document).height()) {
          $mainNav
            .removeClass("fadeInUp")
            .addClass("fadeInDown")
            .css("top", 0)
            .addClass("gap");
          $body.removeClass("add").addClass("remove");
        }
      }
      lastScrollTop = scrollTop;
      didScroll = false;
    }
  }, 200);

  if ($(".sticky-nav").length) {
    $(window).scroll(function () {
      var scroll = $(window).scrollTop();
      if (scroll) {
        $(".sticky-nav").addClass("navbar_fixed");
        $(".sticky-nav-doc .body_fixed").addClass("body_navbar_fixed");
      } else {
        $(".sticky-nav").removeClass("navbar_fixed");
        $(".sticky-nav-doc .body_fixed").removeClass("body_navbar_fixed");
      }
    });
  }

  $(document).ready(function () {
    $(window).scroll(function () {
      if ($(document).scrollTop() > 500) {
        $("body").addClass("test");
      } else {
        $("body").removeClass("test");
      }
    });
  });

  function navbarFixedTwo() {
    if ($("#stickyTwo").length) {
      $(window).scroll(function () {
        var scroll = $(window).scrollTop();
        if (scroll) {
          $("#stickyTwo").addClass("navbar_fixed");
        } else {
          $("#stickyTwo").removeClass("navbar_fixed");
        }
      });
    }
  }
  navbarFixedTwo();

  /*-------------------------------------------------------------------------------
    Navbar Fixed
  -------------------------------------------------------------------------------*/

  function tabFixed() {
    var windowWidth = $(window).width();
    if ($(".header_tabs_area").length) {
      if (windowWidth > 576) {
        var tops = $(".header_tabs_area");
        var tabs = $(".header_tab_items").height() + 100;
        var leftOffset = tops.offset().top + tabs;

        $(window).on("scroll", function () {
          var scroll = $(window).scrollTop();
          if (scroll >= leftOffset) {
            tops.addClass("tab_fixed");
          } else {
            tops.removeClass("tab_fixed");
          }
        });
      }
    }
  }

  tabFixed();

  $(".count_div").on("click", function () {
    $(".count").html(function (i, val) {
      return val * 1 + 1;
    });
    $(this).addClass("active");
    return false;
  });


  /*  Menu Click js  */
  function Menu_js() {
    if ($(".submenu").length) {
      $(".submenu > .dropdown-toggle").click(function () {
        var location = $(this).attr("href");
        window.location.href = location;
        return false;
      });
    }
  }

  Menu_js();

  $('.doc_menu a[href^="#"]:not([href="#"]').on("click", function (event) {
    var $anchor = $(this);
    $("html, body")
      .stop()
      .animate(
        {
          scrollTop: $($anchor.attr("href")).offset().top,
        },
        900
      );
    // event.preventDefault();
  });

  $(window).on("load", function () {
    if ($(".scroll").length) {
      $(".scroll").mCustomScrollbar({
        mouseWheelPixels: 50,
        scrollInertia: 0,
      });
    }
  });

  /*--------------- doc_documentation_area Switcher js--------*/
  if ($(".doc_documentation_area").length > 0) {
    //switcher
    var switchs = true;
    $("#right").on("click", function (e) {
      // e.preventDefault();
      if (switchs) {
        $(".doc_documentation_area,#right").addClass("overlay");
        $(".doc_right_mobile_menu").animate(
          {
            right: "0px",
          },
          100
        );
        switchs = false;
      } else {
        $(".doc_documentation_area,#right").removeClass("overlay");
        $(".doc_right_mobile_menu").animate(
          {
            right: "-250px",
          },
          100
        );
        switchs = true;
      }
    });

    $("#left").on("click", function (e) {
      // e.preventDefault();
      if (switchs) {
        $(".doc_documentation_area,#left").addClass("overlay");
        $(".doc_mobile_menu").animate(
          {
            left: "0px",
          },
          300
        );
        switchs = false;
      } else {
        $(".doc_documentation_area,#left").removeClass("overlay");
        $(".doc_mobile_menu").animate(
          {
            left: "-245px",
          },
          300
        );
        switchs = true;
      }
    });
  }

  if ($(".mobile_menu").length > 0) {
    var switchs = true;
    $(".mobile_btn").on("click", function (e) {
      if (switchs) {
        $(".mobile_menu").addClass("open");
      }
    });
  }

  /*--------------- slick js--------*/
  if ($(".doc_feedback_slider").length) {
    $(".doc_feedback_slider").slick({
      autoplay: true,
      slidesToShow: 1,
      slidesToScroll: 1,
      autoplaySpeed: 2000,
      speed: 1000,
      dots: false,
      arrows: true,
      prevArrow: ".prev",
      nextArrow: ".next",
    });
  }

  /*--------------- parallaxie js--------*/
  function parallax() {
    if ($(".parallaxie").length) {
      $(".parallaxie").parallaxie({
        speed: 0.5,
      });
    }
  }

  parallax();

  /*--------------- tooltip js--------*/
  function tooltip() {
    if ($(".tooltips").length) {
      $(".tooltips").tooltipster({
        interactive: true,
        arrow: true,
        animation: "grow",
        delay: 200,
      });
    }
  }

  tooltip();
  $(".tooltips_one").data("tooltip-custom-class", "tooltip_blue").tooltip();
  $(".tooltips_two").data("tooltip-custom-class", "tooltip_danger").tooltip();

  $(document).on("inserted.bs.tooltip", function (e) {
    var tooltip = $(e.target).data("bs.tooltip");
    $(tooltip.tip).addClass($(e.target).data("tooltip-custom-class"));
  });

  /*--------------- wavify js--------*/
  if ($(".animated-waves").length) {
    $("#animated-wave-three").wavify({
      height: 40,
      bones: 4,
      amplitude: 70,
      color: "rgba(188, 214, 234, 0.14)",
      speed: 0.3,
    });

    $("#animated-wave-four").wavify({
      height: 60,
      bones: 5,
      amplitude: 90,
      color: "rgba(188, 214, 234, 0.14)",
      speed: 0.2,
    });
  }

  /*--------------- nav-sidebar js--------*/
  if ($(".nav-sidebar > li").hasClass("active")) {
    $(".nav-sidebar > li.active").find("ul").slideDown(700);
  }

  function active_dropdown() {
    $(".nav-sidebar > li .icon").on("click", function (e) {
      $(this).parent().find("ul").first().toggle(300);
      $(this).parent().siblings().find("ul").hide(300);
    });
  }

  active_dropdown();

  $(".nav-sidebar > li .icon").each(function () {
    var $this = $(this);
    $this.on("click", function (e) {
      var has = $this.parent().hasClass("active");
      $(".nav-sidebar li").removeClass("active");
      if (has) {
        $this.parent().removeClass("active");
      } else {
        $this.parent().addClass("active");
      }
    });
  });


  /*--------------- mobile dropdown js--------*/
  function active_dropdown2() {
    $(".menu > li .mobile_dropdown_icon").on("click", function (e) {
      $(this).parent().find("ul").first().slideToggle(300);
      $(this).parent().siblings().find("ul").hide(300);
    });
  }

  active_dropdown2();

  /*--------------- search js--------*/
  $(".search a").on("click", function () {
    if ($(this).parent().hasClass("open")) {
      $(this).parent().removeClass("open");
    } else {
      $(this).parent().addClass("open");
    }
    return false;
  });

  /*--------------- counterUp js--------*/
  function counterUp() {
    if ($(".counter").length) {
      $(".counter").counterUp({
        delay: 1,
        time: 250,
      });
    }
  }

  counterUp();

  /*--------------- popup-js--------*/
  function popupGallery() {
    if ($(".img_popup").length) {
      $(".img_popup").each(function () {
        $(".img_popup").magnificPopup({
          type: "image",
          closeOnContentClick: true,
          closeBtnInside: false,
          fixedContentPos: true,
          removalDelay: 300,
          mainClass: "mfp-no-margins mfp-with-zoom",
          image: {
            enabled: true,
            navigateByImgClick: true,
            preload: [0, 1], // Will preload 0 - before current, and 1 after the current image,
          },
        });
      });
    }
  }

  popupGallery();

  if ( $('.pointing_img_container').length ) {
    $(".pointing_img_container").magnificPopup({
      type: "inline",
      delegate: "a",
      fixedContentPos: false,
      fixedBgPos: true,

      overflowY: "auto",
      closeBtnInside: true,
      preloader: false,
      gallery: {
        enabled: true,
        preload: [0, 1],
        navigateByImgClick: true,
        arrowMarkup:
            '<button title="%title%" type="button" class="mfp-arrow mfp-arrow-%dir% zoom-anim-dialog"></button>',
      },
      midClick: true,

      removalDelay: 300,
      mainClass: "my-mfp-zoom-in gallery_content",
    })
  }

  const multipleSwiperSlides = function () {
    let sliderMain = document.querySelectorAll(
      ".swiper-container.js-slider--main"
    );
    let sliderNav = document.querySelectorAll(
      ".swiper-container.js-slider--nav"
    );

    // Arrays to hold swiper instances
    let mainArray = [];
    let navArray = [];

    // Slider Main
    sliderMain.forEach(function (element, i) {
      // Push swiper instance to array
      mainArray.push(
        new Swiper(element, {
          loopedSlides: 3,
          paginationClickable: true,
          effect: "coverflow",
          loop: true,
          centeredSlides: true,
          slidesPerView: "auto",
          coverflow: {
            rotate: 0,
            stretch: 100,
            depth: 150,
            modifier: 1.5,
            slideShadows: false,
          },
        })
      );
    });

    // Slider Nav
    sliderNav.forEach(function (element, i) {
      var self = sliderNav;
      // Push swiper instance to array
      navArray.push(
        new Swiper(element, {
          slidesPerView: 3,
          loop: true,
          loopedSlides: 3,
          slideToClickedSlide: true,
          spaceBetween: 5,
          navigation: {
            nextEl: self[i].querySelector(".swiper-button-next"),
            prevEl: self[i].querySelector(".swiper-button-prev"),
          },
        })
      );
    });

    const checkOnPage = function () {
      if (sliderMain.length > 0 && sliderNav.length > 0) {
        let numberOfSlides = mainArray.length || navArray.length || 0;

        if (mainArray.length !== navArray.length) {
          console.warn(
            "multipleSwiperSlides: Number of main slides and nav slides is different. Expect incorrect behaviour."
          );
        }

        for (let i = 0; i < numberOfSlides; i++) {
          mainArray[i].controller.control = navArray[i];
          navArray[i].controller.control = mainArray[i];
        }

        console.log("multipleSwiperSlides: Things should be working fine. B)");
      }
    };

    checkOnPage();
  };

  multipleSwiperSlides();

  function customPlayer(count) {
    // console.log(count);
    var player = videojs("player_" + count);
    player.nuevo({
      theaterButton: true,
    });
    player.on("mode", function (event, mode) {
      var width;
      if (mode == "large") width = "100%";
      else width = "100%";
      document.querySelector(".video_slider_area").style.width = width;
      $(".video_slider_area").toggleClass("theatermode");
      $(".gallery-thumbs").slick("refresh");
    });
  }

  /*=========== Font size switcher/controller ===========*/
  if ($("#post").length > 0) {
    $.rvFontsize({
      targetSection: "#post",
      store: true, // store.min.js required!
      controllers: {
        appendTo: "#rvfs-controllers",
        showResetButton: true,
      },
    });
  }

  /*=========== anchors js ===========*/
  if ($(".shortcode_info h4").length) {
    var Anchor1 = new AnchorJS();
    document.addEventListener("DOMContentLoaded", function (event) {
      Anchor1 = new AnchorJS();
      Anchor1.add(".shortcode_info h4");
    });
  }

  /*--------- WOW js-----------*/
  function bodyScrollAnimation() {
    var scrollAnimate = $("body").data("scroll-animation");
    if (scrollAnimate === true) {
      new WOW({
        mobile: false,
      }).init();
    }
  }
  bodyScrollAnimation();

  /*------------ Cookie functions and color js ------------*/
  function createCookie(name, value, days) {
    var expires = "";
    if (days) {
      var date = new Date();
      date.setTime(date.getTime() + days * 24 * 60 * 60 * 1000);
      expires = "; expires=" + date.toUTCString();
    }
    document.cookie = name + "=" + value + expires + "; path=/";
  }

  function readCookie(name) {
    var nameEQ = name + "=";
    var ca = document.cookie.split(";");
    for (var i = 0; i < ca.length; i++) {
      var c = ca[i];
      while (c.charAt(0) == " ") c = c.substring(1, c.length);
      if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length, c.length);
    }
    return null;
  }

  function eraseCookie(name) {
    createCookie(name, "", -1);
  }

  var prefersDark =
    window.matchMedia &&
    window.matchMedia("(prefers-color-scheme: dark)").matches;
  var selectedNightTheme = readCookie("body_dark");

  if (
    selectedNightTheme == "true" ||
    (selectedNightTheme === null && prefersDark)
  ) {
    applyNight();
    $(".dark_mode_switcher").prop("checked", true);
  } else {
    applyDay();
    $(".dark_mode_switcher").prop("checked", false);
  }

  function applyNight() {
    $("body").addClass("body_dark");
  }

  function applyDay() {
    $("body").removeClass("body_dark");
  }

  $(".dark_mode_switcher").change(function () {
    if ($(this).is(":checked")) {
      applyNight();
      $(".tab-btns").css("color", "#6B707F");
      createCookie("body_dark", true, 999);
    } else {
      applyDay();
      $(".tab-btns").css("color", "#007CBA");
      createCookie("body_dark", false, 999);
    }
  });

  $(".mobile_menu_btn").on("click", function () {
    $("body").removeClass("menu-is-closed").addClass("menu-is-opened");
  });
  $(".close_nav").on("click", function (e) {
    if ($(".side_menu").hasClass("menu-opened")) {
      $(".side_menu").removeClass("menu-opened");
      $("body").removeClass("menu-is-opened");
    } else {
      $(".side_menu").addClass("menu-opened");
    }
  });

  $(".click_capture").on("click", function () {
    $("body").removeClass("menu-is-opened").addClass("menu-is-closed");
    $(".side_menu").removeClass("menu-opened");
  });

  /*--------------- Tab button js--------*/
  $(".next").on("click", function () {
    $(".v_menu .nav-item > .active")
      .parent()
      .next("li")
      .find("a")
      .trigger("click");
  });

  $(".previous").on("click", function () {
    $(".v_menu .nav-item > .active")
      .parent()
      .prev("li")
      .find("a")
      .trigger("click");
  });
  /*------------ MAILCHIMP js ------------*/
  if ($(".mailchimp").length > 0) {
    $(".mailchimp").ajaxChimp({
      callback: mailchimpCallback,
      url:
        "http://droitlab.us15.list-manage.com/subscribe/post?u=0fa954b1e090d4269d21abef5&id=a80b5aedb0", //Replace this with your own mailchimp post URL. Don't remove the "". Just paste the url inside "".
    });
  }
  if ($(".mailchimp_two").length > 0) {
    $(".mailchimp_two").ajaxChimp({
      callback: mailchimpCallback,
      url:
        "https://droitthemes.us19.list-manage.com/subscribe/post?u=5d334217e146b083fe74171bf&amp;id=0e45662e8c", //Replace this with your own mailchimp post URL. Don't remove the "". Just paste the url inside "".
    });
  }
  $(".memail").on("focus", function () {
    $(".mchimp-errmessage").fadeOut();
    $(".mchimp-sucmessage").fadeOut();
  });
  $(".memail").on("keydown", function () {
    $(".mchimp-errmessage").fadeOut();
    $(".mchimp-sucmessage").fadeOut();
  });
  $(".memail").on("click", function () {
    $(".memail").val("");
  });

  function mailchimpCallback(resp) {
    if (resp.result === "success") {
      $(".mchimp-errmessage").html(resp.msg).fadeIn(1000);
      $(".mchimp-sucmessage").fadeOut(500);
    } else if (resp.result === "error") {
      $(".mchimp-errmessage").html(resp.msg).fadeIn(1000);
    }
  }

  function Click_menu_hover() {
    if ($(".tab-demo").length) {
      $.fn.tab = function (options) {
        var opts = $.extend({}, $.fn.tab.defaults, options);
        return this.each(function () {
          var obj = $(this);

          $(obj)
            .find(".tabHeader li")
            .on(opts.trigger_event_type, function () {
              $(obj).find(".tabHeader li").removeClass("active");
              $(this).addClass("active");

              $(obj).find(".tabContent .tab-pane").removeClass("active show");
              $(obj)
                .find(".tabContent .tab-pane")
                .eq($(this).index())
                .addClass("active show");
            });
        });
      };
      $.fn.tab.defaults = {
        trigger_event_type: "click", //mouseover | click é»˜è®¤æ˜¯click
      };
    }
  }

  Click_menu_hover();

  function Tab_menu_activator() {
    if ($(".tab-demo").length) {
      $(".tab-demo").tab({
        trigger_event_type: "mouseover",
      });
    }
  }

  Tab_menu_activator();

  function fAqactive() {
    $(".doc_faq_info .card").on("click", function () {
      $(".doc_faq_info .card").removeClass("active");
      $(this).addClass("active");
    });
  }

  fAqactive();

  function chartJs() {
    var windowSize = $(window).width();

    if (windowSize <= 767) {
      var leg = true,
        ratio = false;
    } else {
      var leg = false,
        ratio = true;
    }

    var data = [
      {
        name: "35 out of 205 issues unanswered",
        value: 36,
      },
      {
        name: "We are working on 42 out of 205 issues",
        value: 40,
      },
      {
        name: "20 Out of 205 issues haven't got a reply",
        value: 44,
      },
      {
        name: "90 Out of 205 issues resolved in last tow monthsSent",
        value: 50,
      },
    ];

    var labels = [];
    var datasets = [];
    var sent = data[0];
    var opened = data[1];
    var response = data[2];
    var secured = data[3];

    data.forEach(function (items) {
      labels.push(items.name);
    });

    datasets.push({
      data: [sent.value, opened.value, response.value, secured.value],
      backgroundColor: ["#f9327a", "#ecb939", "#35bae9", "#42dabf"],
      borderWidth: 0,
      label: [sent.name, opened.name, response.name, secured.name],
    });

    $("#Docy-chart").each(function () {
      var canvas = $("#Docy-chart");
      canvas.attr("height", 125);
      // chart.canvas.parentNode.style.height = '128px';
      // chart.canvas.parentNode.style.width = '128px';

      var chart = new Chart(canvas, {
        type: "polarArea",
        borderWidth: 0,
        hover: false,
        data: {
          datasets: datasets,
          labels: labels,
        },

        options: {
          responsive: true,
          maintainAspectRatio: ratio,
          legend: {
            position: "top",
            display: leg,
            fullWidth: false,
            padding: 10,
            align: "start",
          },
          scale: {
            display: false,
          },
          tooltips: {
            enabled: false,
            backgroundColor: "white",
            borderColor: "#868e96",
            borderWidth: 0.5,
            bodyFontColor: "#868e96",
            bodyFontSize: 14,
            bodySpacing: 5,
            caretSize: 0,
            cornerRadius: 0,
            displayColors: true,
            xPadding: 10,
            yPadding: 15,
          },
        },
      });
    });
  }

  $(window).on("load", function () {
    chartJs();
  });

  function general() {
    $(".collapse-btn").on("click", function (e) {
      // e.preventDefault();
      $(this).toggleClass("active");
      $(".collapse-wrap").slideToggle(500);
    });

    $(".short-by a").click(function () {
      $(this)
        .toggleClass("active-short")
        .siblings()
        .removeClass("active-short");
    });
  }
  general();

  $(".share_gropu .eye, .share_icon").click(function () {
    $(".share_gropu, .modal_social").addClass("active");
    return false;
  });
  $(".close_btn").click(function () {
    $(".share_gropu, .modal_social").removeClass("active");
    return false;
  });

  /*-------------------------------------
	Intersection Observer
	-------------------------------------*/
  if (!!window.IntersectionObserver) {
    let observer = new IntersectionObserver(
      (entries, observer) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("active-animation");
            //entry.target.src = entry.target.dataset.src;
            observer.unobserve(entry.target);
          }
        });
      },
      {
        rootMargin: "0px 0px -100px 0px",
      }
    );
    document.querySelectorAll(".has-animation").forEach((block) => {
      observer.observe(block);
    });
  } else {
    document.querySelectorAll(".has-animation").forEach((block) => {
      block.classList.remove("has-animation");
    });
  }

  // === Image Magnify
  if ($(".zoom").length) {
    $(".zoom").magnify({
      afterLoad: function () {
        //console.log("Magnification powers activated!");
      },
    });
  }

  // === Focus Search Form
  $(document).on("keydown", function (e) {
    if (e.keyCode === 191) {
      // e.preventDefault();
      $("input[type=search]").focus();
      return;
    }
  });

  let doc_banner_area = $(".doc_banner_area input[type=search]");
  doc_banner_area.on('focus', function () {
    $("body").addClass("search-focused");
    $(".doc_banner_content").css({"position": "relative", "z-index": "999"});
  });

  doc_banner_area.on('focusout', function () {
    $("body").removeClass("search-focused");
    $(".doc_banner_content").removeAttr('style');
  });

  // === YouTube Channel Videos Playlist
  if ($("#ycp").length) {
    $("#ycp").ycp({
      apikey: "AIzaSyBS5J1A7o-M8X78JuiqF5h103XLmSQiReE",
      playlist: 6,
      autoplay: true,
      related: true,
    });
  }

  // === Back to Top Button
  var back_top_btn = $("#back-to-top");

  $(window).scroll(function () {
    if ($(window).scrollTop() > 300) {
      back_top_btn.addClass("show");
    } else {
      back_top_btn.removeClass("show");
    }
  });

  back_top_btn.on("click", function (e) {
    // e.preventDefault();
    $("html, body").animate({ scrollTop: 0 }, "300");
  });

  /**
   * OS select dropdown
   */
  /*--------------- niceSelect js--------*/
  function select() {
    if ($(".custom-select, .nice_select").length) {
      $(".custom-select, .nice_select").niceSelect();
    }
    if ($("#mySelect").length) {
      $("#mySelect").selectpicker();
    }
  }
  select();

  if ($("#mySelect").val() == "windows") {
    $(".windows").show();
  } else {
    $(".windows").hide();
  }

  if ($("#mySelect").val() == "ios") {
    $(".ios").show();
  } else {
    $(".ios").hide();
  }

  $("#mySelect").change(function () {
    if ($("#mySelect").val() == "windows") {
      $(".windows").show();
    } else {
      $(".windows").hide();
    }
    if ($("#mySelect").val() == "ios") {
      $(".ios").show();
    } else {
      $(".ios").hide();
    }
  });

  if ($(".doc_testimonial_area").length) {
    $(".doc_testimonial_slider").slick({
      autoplay: true,
      slidesToShow: 1,
      slidesToScroll: 1,
      autoplaySpeed: 2000,
      speed: 1000,
      dots: true,
      arrows: false,
      asNavFor: ".doc_img_slider",
    });
    $(".doc_img_slider").slick({
      slidesToShow: 1,
      slidesToScroll: 1,
      asNavFor: ".doc_testimonial_slider",
      arrows: false,
      fade: true,
      focusOnSelect: true,
    });
  }

  $(".header_search_keyword ul li a").on("click", function (e) {
    // e.preventDefault();
    var content = $(this).text();
    $("#searchbox").val(content).focus();
    $(".input-wrapper input")
      .parent()
      .find(".header_search_form_panel")
      .first()
      .slideDown(300);
  });
  $(".input-wrapper input").focusout(function () {
    $(this).parent().find(".header_search_form_panel").first().slideUp(300);
  });

  /*-------------------------------------------------------------------------------
	  MAILCHIMP js
	-------------------------------------------------------------------------------*/
  if ($(".mailchimp").length > 0) {
    $(".mailchimp").ajaxChimp({
      callback: mailchimpCallback,
      url:
        "http://droitlab.us15.list-manage.com/subscribe/post?u=0fa954b1e090d4269d21abef5&id=a80b5aedb0", //Replace this with your own mailchimp post URL. Don't remove the "". Just paste the url inside "".
    });
  }
  if ($(".mailchimp_two").length > 0) {
    $(".mailchimp_two").ajaxChimp({
      callback: mailchimpCallback,
      url:
        "https://droitthemes.us19.list-manage.com/subscribe/post?u=5d334217e146b083fe74171bf&amp;id=0e45662e8c", //Replace this with your own mailchimp post URL. Don't remove the "". Just paste the url inside "".
    });
  }
  $(".memail").on("focus", function () {
    $(".mchimp-errmessage").fadeOut();
    $(".mchimp-sucmessage").fadeOut();
  });
  $(".memail").on("keydown", function () {
    $(".mchimp-errmessage").fadeOut();
    $(".mchimp-sucmessage").fadeOut();
  });
  $(".memail").on("click", function () {
    $(".memail").val("");
  });

  function mailchimpCallback(resp) {
    if (resp.result === "success") {
      $(".mchimp-errmessage").html(resp.msg).fadeIn(1000);
      $(".mchimp-sucmessage").fadeOut(500);
    } else if (resp.result === "error") {
      $(".mchimp-errmessage").html(resp.msg).fadeIn(1000);
    }
  }

  /**
   * Doc : On this page
   * @param str
   * @returns {string}
   */
  var slug = function(str) {
    str = str.replace(/^\s+|\s+$/g, ''); // trim
    str = str.toLowerCase();

    // remove accents, swap ñ for n, etc
    var from = "ãàáäâẽèéëêìíïîõòóöôùúüûñç·/_,:;";
    var to   = "aaaaaeeeeeiiiiooooouuuunc------";
    for (var i=0, l=from.length ; i<l ; i++) {
      str = str.replace(new RegExp(from.charAt(i), 'g'), to.charAt(i));
    }

    str = str.replace(/[^a-z0-9 -]/g, '') // remove invalid chars
        .replace(/\s+/g, '-') // collapse whitespace and replace by -
        .replace(/-+/g, '-'); // collapse dashes

    return str;
  }

  function capitalizeFirstLetter(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
  }

  function convertToTitle(Text)
  {
    let title = Text.replaceAll('-', ' ');
    return capitalizeFirstLetter(title)
  }

  function onThisPageTitles( divs ) {
    var titles = [];
    jQuery(divs).each(function () {
      titles.push( jQuery(this).attr("id") );
    });
    titles.forEach(onThisPage)

    function onThisPage(item, index) {
      if ( $('#navbar-example3').length ) {
        document.getElementById("navbar-example3").innerHTML += "<a class='nav-link' href='#" + item + "'>" + convertToTitle(item) + "</a>";
      }
    }
  }

  $(document).ready(function () {
    onThisPageTitles($(".shortcode_info h4").toArray());
  })

  $( ".shadow-sm" ).hover(
    function() {
      $(this).addClass('shadow-lg');
    }, function() {
      $(this).removeClass('shadow-lg');
  })

// blog_single2_sidebar js
function bodyFixed2() {
  var windowWidth = $(window).width();
  
  if ($("#sticky_doc2").length) {
    if (windowWidth > 576) {
      var tops = $("#sticky_doc2");
      var topOffset = tops.offset().top;
      var blogForm = $('.blog_comment_box');
      var blogFormTop = blogForm.offset().top -300;

      $(window).on("scroll", function () {
        var scrolls = $(window).scrollTop();
        if (scrolls >= topOffset && scrolls <= blogFormTop ) {
          tops.addClass("stick");
         } else {
          tops.removeClass("stick");
        }
      });


      $('a[href="#hackers"]').click(function() {
        $("#hackers").css("padding-top", "100px"); 

        $(window).on("scroll", function () {
          var hackersOffset = $("#hackers").offset().top;
          var scrolls = $(window).scrollTop();
          if (scrolls < hackersOffset) {
            $("#hackers").css("padding-top", "0px");
           }
        })
      });
    }
  }
}

bodyFixed2();


})(jQuery);