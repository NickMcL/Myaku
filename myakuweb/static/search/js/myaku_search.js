// Myaku javascript

const FULL_SEARCH_PLACEHOLDER = 'Japanese word, set phrase, idiom, etc.';
const SHORT_SEARCH_PLACEHOLDER = 'Japanese word, phrase, etc.';
const MOBILE_VIEWPORT_WIDTH_MAX = 768;  // in pixels.

function updateSearchPlaceholder() {
    if (window.innerWidth <= MOBILE_VIEWPORT_WIDTH_MAX) {
        $('#search-input').attr('placeholder', SHORT_SEARCH_PLACEHOLDER);
    } else {
        $('#search-input').attr('placeholder', FULL_SEARCH_PLACEHOLDER);
    }
}

updateSearchPlaceholder();
$(window).resize(updateSearchPlaceholder);

$('.search-clear').click(function () {
    $(this).closest('.search-form').find('#search-input').val('');
});

$('.extra-sample-instances').on('show.bs.collapse', function () {
    var trigger_button = $(this)
        .closest('.result-tile')
        .find('.show-more-button');
    trigger_button.text(trigger_button.text().replace('more', 'less'));
});

$('.extra-sample-instances').on('hide.bs.collapse', function () {
    var trigger_button = $(this)
        .closest('.result-tile')
        .find('.show-more-button');
    trigger_button.text(trigger_button.text().replace('less', 'more'));
});
