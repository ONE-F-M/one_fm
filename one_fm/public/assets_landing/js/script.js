$(document).ready(function(){

	var rtl = false;
    if($("html").attr("lang") == 'ar'){
         rtl = true;
    }
    /*header-fixed*/
    $(window).scroll(function(){
            
        if ($(window).scrollTop() >= 100) {
            $('#header').addClass('fixed-header');
        }
        else {
            $('#header').removeClass('fixed-header');
        }
              
    });
    $('.scroll, .mmenu a').on('click', function () {
        
        $('html, body').animate({
           
            scrollTop: $('#' + $(this).data('value')).offset().top
           
        }, 1000);
        
        $("body,html").removeClass('menu-toggle');
        
        $(".hamburger").removeClass('active');
        
    });
    /*open menu*/
    $(".hamburger").click(function(){
        $("body,html").addClass('menu-toggle');
        $(".hamburger").addClass('active');
    });
    $(".m-overlay").click(function(){
        $("body,html").removeClass('menu-toggle');
        $(".hamburger").removeClass('active');
    });
 

    $("#clientSlider").owlCarousel({
        items: 1,
        loop: true,
        margin: 0,
        responsiveClass: true,
        nav: true,
        dots: false,
        rtl:rtl,
        smartSpeed: 500,
        autoplay: true,
        navText:['<i class="zmdi zmdi-arrow-left"></i>','<i class="zmdi zmdi-arrow-right"></i>'],
    });
    
    $("#slider-about").owlCarousel({
        items: 1,
        loop: true,
        margin: 0,
        responsiveClass: true,
        nav: false,
        dots: false,
        rtl:rtl,
        smartSpeed: 500,
        autoplay: true,
        autoplayTimeout: 2000,
        animateOut: 'fadeOut',
        animateIn: 'fadeIn'
    });

    
    // counter
    $('.counter-count').each(function () {
        $(this).prop('counter',0).animate({
            counter: $(this).text()
        }, {
            duration: 5000,
            easing: 'swing',
            step: function (now) {
                $(this).text(Math.ceil(now));
            }
        });
    });

    $('.timer').each(function () {
        $(this).prop('counter',0).animate({
            counter: $(this).text()
        }, {
            duration: 5000,
            easing: 'swing',
            step: function (now) {
                $(this).text(Math.ceil(now));
            }
        });
    });


})