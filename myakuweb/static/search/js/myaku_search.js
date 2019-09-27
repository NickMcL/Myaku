/**
 * @file Myaku search javascript
 */
'use strict';

jQuery(document).ready(function($) {

// Search box placeholder text adjust based on viewport size
const FULL_SEARCH_PLACEHOLDER = 'Japanese word, set phrase, idiom, etc.';
const SHORT_SEARCH_PLACEHOLDER = 'Japanese word, phrase, etc.';
const MOBILE_VIEWPORT_WIDTH_MAX = 767;  // in pixels.


/**
 * Updates the placeholder text of the search input based on the current
 * viewport size.
 */
function updateSearchPlaceholder() {
    var $searchInput = $('#search-input');
    if (window.innerWidth <= MOBILE_VIEWPORT_WIDTH_MAX) {
        $searchInput.attr('placeholder', SHORT_SEARCH_PLACEHOLDER);
    } else {
        $searchInput.attr('placeholder', FULL_SEARCH_PLACEHOLDER);
    }
}

updateSearchPlaceholder();
$(window).resize(updateSearchPlaceholder);


// Search clear button
$('.search-clear').click(function() {
    $('#search-input').val('');
});


// Search options collapse button text changes
var $searchOptionsButton = $('#search-options');
$searchOptionsButton.on('show.bs.collapse', function() {
    var $trigger_button = $('.search-options-toggle');
    $trigger_button.text($trigger_button.text().replace('Show', 'Hide'));
});
$searchOptionsButton.on('hide.bs.collapse', function() {
    var $trigger_button = $('.search-options-toggle');
    $trigger_button.text($trigger_button.text().replace('Hide', 'Show'));
});


// More instances collapse button text changes
var $extraSampleInstancesDivs = $('.extra-sample-instances');
$extraSampleInstancesDivs.on('show.bs.collapse', function() {
    var $trigger_button = $(this)
        .closest('.result-tile')
        .find('.show-more-button');
    $trigger_button.text($trigger_button.text().replace('more', 'less'));
});
$extraSampleInstancesDivs.on('hide.bs.collapse', function() {
    var $trigger_button = $(this)
        .closest('.result-tile')
        .find('.show-more-button');
    $trigger_button.text($trigger_button.text().replace('less', 'more'));
});

});
