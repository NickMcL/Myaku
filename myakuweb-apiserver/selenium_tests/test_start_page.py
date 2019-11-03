"""Web driver tests for MyakuWeb."""

import os
from typing import Dict, List, Union

import pytest
from selenium import webdriver
from selenium.webdriver import firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

REVERSEPROXY_HOST_ENV_VAR = 'REVERSEPROXY_HOST'

GITHUB_LINK = 'https://github.com/FriedRice/Myaku'

MYAKUWEB_FONT_FAMILY = 'Open Sans, sans-serif'

# Viewport width size breakpoints
SM_MIN_WIDTH = 576
MD_MIN_WIDTH = 768
LG_MIN_WIDTH = 992
XL_MIN_WIDTH = 1200

SHORT_SEARCH_PLACEHOLDER = 'Japanese word, phrase, etc.'
FULL_SEARCH_PLACEHOLDER = 'Japanese word, set phrase, idiom, etc.'


@pytest.fixture
def web_driver():
    """Init a headless Firefox web driver for testing."""
    options = firefox.options.Options()
    options.headless = True
    test_web_driver = webdriver.Firefox(options=options)

    yield test_web_driver
    test_web_driver.close()


@pytest.fixture
def web_driver_xs(web_driver):
    """Set up a web driver with an extram small viewport for testing."""
    web_driver.set_window_size(SM_MIN_WIDTH - 100, 720)
    return web_driver


@pytest.fixture
def web_driver_sm(web_driver):
    """Set up a web driver with a small viewport for testing."""
    web_driver.set_window_size(SM_MIN_WIDTH, 720)
    return web_driver


@pytest.fixture
def web_driver_md(web_driver):
    """Set up a web driver with a medium viewport for testing."""
    web_driver.set_window_size(MD_MIN_WIDTH, 720)
    return web_driver


@pytest.fixture
def web_driver_lg(web_driver):
    """Set up a web driver with a small viewport for testing."""
    web_driver.set_window_size(LG_MIN_WIDTH, 720)
    return web_driver


@pytest.fixture
def web_driver_xl(web_driver):
    """Set up a web driver with an extra large viewport for testing."""
    web_driver.set_window_size(XL_MIN_WIDTH, 720)
    return web_driver


def _go_to_start_page(web_driver) -> None:
    """Go to the MyakuWeb start page with the web driver."""
    host = os.environ[REVERSEPROXY_HOST_ENV_VAR]
    web_driver.get(f'http://{host}/')


def _go_to_search_result_page(web_driver, query: str) -> None:
    """Go to the MyakuWeb start page with the web driver."""
    host = os.environ[REVERSEPROXY_HOST_ENV_VAR]
    web_driver.get(f'http://{host}/?q={query}')


def filter_by_displayed(
    tags: List[WebElement], displayed: bool
) -> List[WebElement]:
    """Filter out tags based on if they are displayed or not."""
    displayed_tags = []
    not_displayed_tags = []
    for tag in tags:
        if not tag.is_displayed():
            not_displayed_tags.append(tag)
            continue

        # An img having a natural width or height of 0 means it failed to load
        # and isn't being displayed.
        if (tag.tag_name == 'img'
                and (tag.get_property('naturalHeight') == 0
                     or tag.get_property('naturalWidth') == 0)):
            not_displayed_tags.append(tag)
            continue

        displayed_tags.append(tag)

    if displayed:
        return displayed_tags
    else:
        return not_displayed_tags


def filter_by_attrs(tags: List[WebElement], attrs: Dict) -> List[WebElement]:
    """Filter out tags that do not have all of the given attributes."""
    if attrs is None:
        return tags

    filtered_tags = []
    for tag in tags:
        for attr, value in attrs.items():
            if tag.get_attribute(attr) != value:
                break
        else:
            filtered_tags.append(tag)

    return filtered_tags


def filter_by_properties(
    tags: List[WebElement], props: Dict
) -> List[WebElement]:
    """Filter out tags that do not have all of the given properties."""
    if props is None:
        return tags

    filtered_tags = []
    for tag in tags:
        for prop, value in props.items():
            if tag.get_property(prop) != value:
                break
        else:
            filtered_tags.append(tag)

    return filtered_tags


def assert_element_text(
    tags: List[WebElement], expected_text: Union[str, bool], is_displayed: bool
) -> None:
    """Assert the text for the given tag elements is as expected.

    Args:
        tags: Elements whose text to check.
        text: If a string, will check that the elements have this text. If
            True, will check that the elements have at least one non-space
            character in their text.
        is_displayed: If True, will only check the displayed text for
            the elements. If False, will also include the undisplayed text or
            the elements.
    """
    for tag in tags:
        if is_displayed:
            text = tag.text
        else:
            # textContent attr will include undisplayed text
            text = tag.get_attribute('textContent')

        if expected_text is True:
            assert len(text) > 0 and not text.isspace()
        else:
            assert text == expected_text


def assert_element(
    we: WebElement, tag_name: str, by_attr: By, attr_value: str,
    expected_text: str = None, is_displayed: bool = True,
    expected_count: int = 1, attrs: Dict = None, properties: Dict = None
) -> None:
    """Assert that the specified element(s) are in the current webdriver page.

    Args:
        we: WebElement containing the desired content to assert.
        tag_name: Name of the tag of the elements to check for.
        by_attr: Attr to use to search for the elements.
        attr_value: Attr value that the by_attr must have for the elements.
        expected_text: Expected text contained by the elements. If None, does
            not check the text of the elements.
        is_displayed: If True, will only consider elements that are
            displayed to the user in the page. If False, will only consider
            elements that are not displayed to the user in the page.
        expected_count: Expected count of the matching elements in the page.
        attrs: Dictionary of attrs that the elements must have.
        properties: Dictionary of properties that the elements must have.
    """
    tags = we.find_elements(by_attr, attr_value)
    tags = filter_by_displayed(tags, is_displayed)
    tags = filter_by_attrs(tags, attrs)
    tags = filter_by_properties(tags, properties)

    assert len(tags) == expected_count
    if expected_text is not None:
        assert_element_text(tags, expected_text, is_displayed)


def assert_element_by_tag(
    we: WebElement, tag_name: str, *args, **kwargs
) -> None:
    """Assert that a single element with tag is in the webdriver page.

    Args:
        we: WebElement containing the desired content to assert.
        tag_name: Name of the tag of the element to check for.
        args: Passed to assert_element.
        kwargs: Passed to assert_element.
    """
    assert_element(we, tag_name, By.TAG_NAME, tag_name, *args, **kwargs)


def assert_element_by_classes(
    we: WebElement, tag_name: str, classes: Union[str, List[str]],
    *args, **kwargs
) -> None:
    """Assert that a single element with classes is in the webdriver page.

    Args:
        we: WebElement containing the desired content to assert.
        tag_name: Name of the tag of the element to check for.
        classes: Class(es) that the element to check for must have.
        args: Passed to assert_element.
        kwargs: Passed to assert_element.
    """
    if not isinstance(classes, list):
        classes = [classes]

    css_selector = '{}.{}'.format(tag_name, '.'.join(classes))
    assert_element(
        we, tag_name, By.CSS_SELECTOR, css_selector, *args, **kwargs
    )


def assert_element_by_id(
    we: WebElement, tag_name: str, id_: str, *args, **kwargs
) -> None:
    """Assert that a single element with id is in the webdriver page.

    Args:
        we: WebElement containing the desired content to assert.
        tag_name: Name of the tag of the element to check for.
        id_: id attr of the element to check for.
    """
    assert_element(we, tag_name, By.ID, id_, *args, **kwargs)


def assert_search_header(we: WebElement, window_width: int) -> None:
    """Assert that the search header part of the page is as expected.

    Args:
        we: WebElement containing the desired content to assert.
        window_width: Width of the viewport in pixels for the web driver used
            to access the page.
    """
    assert_element_by_classes(we, 'img', 'myaku-logo')
    assert_element_by_classes(we, 'button', 'search-clear')
    assert_element_by_classes(we, 'button', 'search-submit')
    assert_element_by_classes(
        we, 'button', 'search-options-toggle', 'Show search options'
    )
    assert_element_by_classes(
        we, 'legend', 'search-options-legend', 'Romaji Conversion', False
    )
    assert_element_by_classes(
        we, 'label', 'check-input-label', True, False, 3
    )
    assert_element_by_classes(
        we, 'input', 'search-options-check-input', None, False, 3
    )

    nav_link_list = we.find_element_by_class_name('nav-link-list')
    assert_element_by_tag(
        nav_link_list, 'a', 'Github', attrs={'href': GITHUB_LINK}
    )

    if window_width < SM_MIN_WIDTH:
        placeholder = SHORT_SEARCH_PLACEHOLDER
    else:
        placeholder = FULL_SEARCH_PLACEHOLDER
    assert_element_by_id(
        we, 'input', 'search-input', attrs={'placeholder': placeholder}
    )


def assert_start_tiles(we: WebElement) -> None:
    """Assert that the start page tiles are as expected.

    Args:
        we: WebElement containing the desired content to assert.
    """
    assert_element_by_classes(
        we, 'section', ['tile', 'start-tile'], None, True, 2
    )
    tiles = we.find_elements_by_class_name('start-tile')

    assert_element_by_classes(
        tiles[0], 'h4', 'main-tile-header', 'What is Myaku?'
    )
    assert_element_by_classes(
        tiles[0], 'span', 'key-word', True, True, 2
    )
    assert_element_by_classes(tiles[0], 'ol', 'myaku-ol')
    assert_element_by_tag(tiles[0], 'li', True, True, 3)

    assert_element_by_classes(
        tiles[1], 'h4', 'main-tile-header', 'Getting Started'
    )
    assert_element_by_classes(we, 'ul', 'myaku-ul')
    assert_element_by_tag(tiles[1], 'li', True, True, 4)
    assert_element_by_tag(tiles[1], 'a', True, True, 4)


def assert_css_loaded(we: WebElement) -> None:
    """Assert that the CSS stylesheet used by Myaku web has loaded.

    Checks that the custom font-family used by Myaku web is set for the body in
    order to tell if the CSS for Myaku web is loaded.

    Args:
        we: WebElement containing the desired content to assert.
    """
    body = we.find_element_by_tag_name('body')
    font_family = body.value_of_css_property('font-family')
    assert font_family == MYAKUWEB_FONT_FAMILY


def assert_start_page(web_driver: webdriver):
    """Test the MyakuWeb start page with the web driver."""
    viewport_width = web_driver.get_window_size()['width']
    _go_to_start_page(web_driver)

    assert_css_loaded(web_driver)
    assert_element_by_tag(web_driver, 'title', 'Myaku', False)

    header_element = web_driver.find_element_by_tag_name('header')
    assert_search_header(header_element, viewport_width)

    main_element = web_driver.find_element_by_tag_name('main')
    assert_start_tiles(main_element)


def test_start_page_xs(web_driver_xs):
    """Test the MyakuWeb start page with an extra small web driver."""
    assert_start_page(web_driver_xs)


def test_start_page_sm(web_driver_sm):
    """Test the MyakuWeb start page with a small web driver."""
    assert_start_page(web_driver_sm)


def test_start_page_md(web_driver_md):
    """Test the MyakuWeb start page with a medium web driver."""
    assert_start_page(web_driver_md)


def test_start_page_lg(web_driver_lg):
    """Test the MyakuWeb start page with a large web driver."""
    assert_start_page(web_driver_lg)


def test_start_page_xl(web_driver_xl):
    """Test the MyakuWeb start page with an extra large web driver."""
    assert_start_page(web_driver_xl)
