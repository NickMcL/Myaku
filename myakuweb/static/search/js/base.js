$('.search-clear').click(function () {
    $(this).closest('.search-form').find('#query').val('');
})

$('.extra-sample-instances').on('show.bs.collapse', function () {
    var trigger_button = $(this)
        .closest('.result-tile')
        .find('.show-more-button');
    trigger_button.text(trigger_button.text().replace('more', 'less'));
})

$('.extra-sample-instances').on('hide.bs.collapse', function () {
    var trigger_button = $(this)
        .closest('.result-tile')
        .find('.show-more-button');
    trigger_button.text(trigger_button.text().replace('less', 'more'));
})
