/**
 * @file Myaku search javascript.
 */
'use strict';

document.addEventListener('DOMContentLoaded', function() {

// Search box placeholder text adjust based on viewport size
const FULL_SEARCH_PLACEHOLDER = 'Japanese word, set phrase, idiom, etc.';
const SHORT_SEARCH_PLACEHOLDER = 'Japanese word, phrase, etc.';
const MEDIUM_VIEWPORT_MIN_WIDTH = getCssVarInt('--md-min-width');

setupMyakuSearchPage();


/**
 * Do all setup for the Myaku search page.
 */
function setupMyakuSearchPage() {
    // Search input placeholder text updater based on viewport size
    updateSearchPlaceholder();
    window.addEventListener('resize', updateSearchPlaceholder);

    // Search input clear button
    var searchClearButton = document.querySelector('.search-clear');
    searchClearButton.addEventListener('click', function() {
        document.getElementById('search-input').value = '';
    });

    // Collapse button setup
    setupCollapseButtons('.search-options-toggle');
    setupCollapseButtons('.show-more-button');
}

/**
 * Gets an integer CSS variable defined for the :root element.
 */
function getCssVarInt(cssVarName) {
    var rootStyle = getComputedStyle(document.documentElement);
    return parseInt(rootStyle.getPropertyValue(cssVarName));
}

/**
 * Updates the placeholder text of the search input based on the current
 * viewport size.
 */
function updateSearchPlaceholder() {
    var searchInput = document.querySelector('#search-input');
    if (window.innerWidth >= MEDIUM_VIEWPORT_MIN_WIDTH) {
        searchInput.placeholder = FULL_SEARCH_PLACEHOLDER;
    } else {
        searchInput.placeholder = SHORT_SEARCH_PLACEHOLDER;
    }
}

/*
 * Toggles the collapse animation for the given element.
 *
 * @return {bool} - Whether the element will be visible after the collapse
 *      toggle or not. If null, it means the element is in the middle of a
 *      transition, so no collapse toggle was attempted.
 */
function toggleCollapse(collapseElementSelector) {
    var element = document.querySelector(collapseElementSelector);
    if (element.classList.contains('collapsing')) {
        return null;
    }

    if (element.classList.contains('show')) {
        collapse(element);
        return false;
    } else {
        uncollapse(element);
        return true;
    }
}

/**
 * Forces a redraw of the element by the browser.
 */
function reflow(element) {
    return element.offsetHeight;
}

/**
 * Collapses an element with a CSS animation.
 */
function collapse(element) {
    element.addEventListener('transitionend', function removeCollapsing() {
        element.classList.remove('collapsing');
        element.classList.add('collapse');

        element.removeEventListener('transitionend', removeCollapsing);
    });

    element.style.height = element.getBoundingClientRect()['height'] + 'px';
    reflow(element);

    element.classList.remove('collapse');
    element.classList.remove('show');
    element.classList.add('collapsing');
    element.style.removeProperty('height');
}

/**
 * Uncollapses a collapsed element with a CSS animation.
 */
function uncollapse(element) {
    element.addEventListener('transitionend', function removeCollapsing() {
        element.classList.remove('collapsing');
        element.style.removeProperty('height');
        element.classList.add('collapse');
        element.classList.add('show');

        element.removeEventListener('transitionend', removeCollapsing);
    });

    element.classList.remove('collapse');
    element.classList.add('collapsing');
    element.style.height = 0;
    element.style.height = element.scrollHeight + 'px';
}

/**
 * Sets the buttons matching the given selector to toggle the collapse of the
 * elements matched by their data-target selector.
 *
 * @param {string} buttonSelector - Selector to find the buttons to set up.
 * @param {string} hiddenText - String to swap with showingText when the
 *      data-target for a button is collapsed.
 * @param {string} showingText - String to swap with hiddenText when the
 *      data-target for a button is uncollapsed.
 */
function setupCollapseButtons(buttonQuery, hiddenText, showingText) {
    var buttons = document.querySelectorAll(buttonQuery);
    buttons.forEach(function(button) {
        button.addEventListener('click', function() {
            var isShowing = toggleCollapse(this.getAttribute('data-target'));
            if (isShowing === null) {
                return;
            }

            if (isShowing) {
                this.innerHTML = this.innerHTML.replace(
                    hiddenText, showingText
                );
            } else {
                this.innerHTML = this.innerHTML.replace(
                    showingText, hiddenText
                );
            }
        });
    });
}

});
