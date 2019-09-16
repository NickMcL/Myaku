// Myaku javascript

// Search box placeholder text adjust based on viewport size
const FULL_SEARCH_PLACEHOLDER = "Japanese word, set phrase, idiom, etc.";
const SHORT_SEARCH_PLACEHOLDER = "Japanese word, phrase, etc.";
const MOBILE_VIEWPORT_WIDTH_MAX = 767;  // in pixels.

function updateSearchPlaceholder() {
    if (window.innerWidth <= MOBILE_VIEWPORT_WIDTH_MAX) {
        $("#search-input").attr("placeholder", SHORT_SEARCH_PLACEHOLDER);
    } else {
        $("#search-input").attr("placeholder", FULL_SEARCH_PLACEHOLDER);
    }
}

updateSearchPlaceholder();
$(window).resize(updateSearchPlaceholder);


// Search clear button
$(".search-clear").click(function() {
    $(this).closest(".search-form").find("#search-input").val("");
});


// Search options collapse button text changes
$("#search-options").on("show.bs.collapse", function() {
    var trigger_button = $(".search-options-toggle");
    trigger_button.text(trigger_button.text().replace("Show", "Hide"));
});
$("#search-options").on("hide.bs.collapse", function() {
    var trigger_button = $(".search-options-toggle");
    trigger_button.text(trigger_button.text().replace("Hide", "Show"));
});


// More instances collapse button text changes
$(".extra-sample-instances").on("show.bs.collapse", function() {
    var trigger_button = $(this)
        .closest(".result-tile")
        .find(".show-more-button");
    trigger_button.text(trigger_button.text().replace("more", "less"));
});
$(".extra-sample-instances").on("hide.bs.collapse", function() {
    var trigger_button = $(this)
        .closest(".result-tile")
        .find(".show-more-button");
    trigger_button.text(trigger_button.text().replace("less", "more"));
});
