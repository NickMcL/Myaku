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

MYAKUWEB_FONT_FAMILY = '"Noto Sans", "Noto Sans JP", sans-serif'

# Bootstrap viewport width size breakpoints
SM_MIN_WIDTH = 576
MD_MIN_WIDTH = 768
LG_MIN_WIDTH = 992
XL_MIN_WIDTH = 1200

SHORT_SEARCH_PLACEHOLDER = 'Japanese word, phrase, etc.'
FULL_SEARCH_PLACEHOLDER = 'Japanese word, set phrase, idiom, etc.'


@pytest.fixture
def web_driver():
    """Inits a headless Firefox web driver for testing."""
    options = firefox.options.Options()
    options.headless = True
    test_web_driver = webdriver.Firefox(options=options)

    # When the reverseproxy service is using the dev/test allowed hosts list,
    # it will only accept connections with the host header set as localhost, so
    # we must override the host header on selenium's requests to be localhost.
    # test_web_driver.header_overrides = {'Host': 'localhost'}

    yield test_web_driver
    test_web_driver.close()


@pytest.fixture
def web_driver_xs(web_driver):
    """Sets up a web driver with an extram small viewport for testing."""
    web_driver.set_window_size(SM_MIN_WIDTH - 100, 720)
    return web_driver


@pytest.fixture
def web_driver_sm(web_driver):
    """Sets up a web driver with a small viewport for testing."""
    web_driver.set_window_size(SM_MIN_WIDTH, 720)
    return web_driver


@pytest.fixture
def web_driver_md(web_driver):
    """Sets up a web driver with a medium viewport for testing."""
    web_driver.set_window_size(MD_MIN_WIDTH, 720)
    return web_driver


@pytest.fixture
def web_driver_lg(web_driver):
    """Sets up a web driver with a small viewport for testing."""
    web_driver.set_window_size(LG_MIN_WIDTH, 720)
    return web_driver


@pytest.fixture
def web_driver_xl(web_driver):
    """Sets up a web driver with an extra large viewport for testing."""
    web_driver.set_window_size(XL_MIN_WIDTH, 720)
    return web_driver


def _go_to_start_page(web_driver) -> None:
    """Goes to the MyakuWeb start page with the web driver."""
    host = os.environ[REVERSEPROXY_HOST_ENV_VAR]
    web_driver.get(f'http://{host}/')


def _go_to_search_result_page(web_driver, query: str) -> None:
    """Goes to the MyakuWeb start page with the web driver."""
    host = os.environ[REVERSEPROXY_HOST_ENV_VAR]
    web_driver.get(f'http://{host}/?q={query}')


def filter_to_displayed(tags: List[WebElement]) -> List[WebElement]:
    """Filters out tags that are not being displayed on the page."""
    filtered_tags = []
    for tag in tags:
        if not tag.is_displayed():
            continue

        # An img having a natural widht or height of 0 means it failed to load
        # and isn't being displayed.
        if (tag.tag_name == 'img'
            and (tag.get_property('naturalHeight') == 0
                 or tag.get_property('naturalWidth') == 0)):
            continue

        filtered_tags.append(tag)

    return filtered_tags


def filter_by_attrs(tags: List[WebElement], attrs: Dict) -> List[WebElement]:
    """Filters out tags that do not have all of the given attributes."""
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
    """Filters out tags that do not have all of the given properties."""
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
    tags: List[WebElement], expected_text: Union[str, bool],
    include_only_displayed: bool
) -> None:
    """Asserts the text for the given tag elements is as expected.

    Args:
        tags: Elements whose text to check.
        text: If a string, will check that the elements have this text. If
            True, will check that the elements have any text.
        include_only_displayed: If True, will only check the displayed text for
            the elements. If False, will also include the undisplayed text or
            the elements.
    """
    for tag in tags:
        if expected_text is True:
            assert len(tag.text) > 0
        elif include_only_displayed:
            assert tag.text == expected_text
        else:
            # textContent attr will include undisplayed text
            assert tag.get_attribute('textContent') == expected_text


def assert_element(
    we: WebElement, tag_name: str, by_attr: By, attr_value: str,
    expected_text: str = None, include_only_displayed: bool = True,
    expected_count: int = 1, attrs: Dict = None, properties: Dict = None
) -> None:
    """Asserts that the specified element(s) are in the current webdriver page.

    Args:
        we: WebElement containing the desired content to assert.
        tag_name: Name of the tag of the elements to check for.
        by_attr: Attr to use to search for the elements.
        attr_value: Attr value that the by_attr must have for the elements.
        expected_text: Expected text contained by the elements. If None, does
            not check the text of the elements.
        include_only_displayed: If True, will only look for elements that are
            displayed to the user in the page. If False, will look for all
            elements regardless of if they are displayed.
        expected_count: Expected count of the matching elements in the page.
        attrs: Dictionary of attrs that the elements must have.
        properties: Dictionary of properties that the elements must have.
    """
    tags = we.find_elements(by_attr, attr_value)
    if include_only_displayed:
        tags = filter_to_displayed(tags)
    tags = filter_by_attrs(tags, attrs)
    tags = filter_by_properties(tags, properties)

    assert len(tags) == expected_count
    if expected_text is not None:
        assert_element_text(tags, expected_text, include_only_displayed)


def assert_element_by_tag(
    we: WebElement, tag_name: str, *args, **kwargs
) -> None:
    """Asserts that a single element with tag is in the webdriver page.

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
    """Asserts that a single element with classes is in the webdriver page.

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
    """Asserts that a single element with id is in the webdriver page.

    Args:
        we: WebElement containing the desired content to assert.
        tag_name: Name of the tag of the element to check for.
        id_: id attr of the element to check for.
    """
    assert_element(we, tag_name, By.ID, id_, *args, **kwargs)


def assert_search_header(we: WebElement, window_width: int) -> None:
    """Asserts that the search header part of the page is as expected.

    Args:
        we: WebElement containing the desired content to assert.
        window_width: Width of the viewport in pixels for the web driver used
            to access the page.
    """
    assert_element_by_tag(we, 'title', 'Myaku', False)
    assert_element_by_classes(we, 'button', 'search-clear')
    assert_element_by_classes(we, 'button', 'search-button')
    assert_element_by_classes(
        we, 'button', 'search-options-toggle', 'Show search options'
    )
    assert_element_by_classes(
        we, 'a', 'nav-link', 'Github', attrs={'href': GITHUB_LINK}
    )

    if window_width < MD_MIN_WIDTH:
        placeholder = SHORT_SEARCH_PLACEHOLDER
    else:
        placeholder = FULL_SEARCH_PLACEHOLDER
    assert_element_by_id(
        we, 'input', 'search-input', attrs={'placeholder': placeholder}
    )

    assert_element_by_classes(we, 'img', 'myaku-logo')
    if window_width < MD_MIN_WIDTH:
        assert_element_by_classes(we, 'img', 'myaku-logo-sm')
    else:
        assert_element_by_classes(we, 'img', 'myaku-logo-lg')


def assert_start_tiles(we: WebElement) -> None:
    """Asserts that the start page tiles are as expected.

    Args:
        we: WebElement containing the desired content to assert.
    """
    assert_element_by_classes(we, 'div', 'row', expected_count=2)
    assert_element_by_classes(we, 'div', 'col', expected_count=2)
    assert_element_by_classes(we, 'h4', 'myaku-color', True, expected_count=2)
    assert_element_by_classes(we, 'span', 'key-word', True, expected_count=2)
    assert_element_by_classes(we, 'ul', 'myaku-color-ul')
    assert_element_by_classes(we, 'ol', 'myaku-color-ol')


def assert_css_loaded(we: WebElement) -> None:
    """Asserts that the custom CSS used by Myaku web has loaded.

    Args:
        we: WebElement containing the desired content to assert.
    """
    # Check that the custom font-family used by Myaku web is set for the body
    # as a way to tell if the custom CSS for Myaku web is loaded.
    body = we.find_element_by_tag_name('body')
    font_family = body.value_of_css_property('font-family')
    assert font_family == MYAKUWEB_FONT_FAMILY


def assert_start_page(web_driver: webdriver):
    """Tests the MyakuWeb start page with the web driver."""
    viewport_width = web_driver.get_window_size()['width']
    _go_to_start_page(web_driver)

    assert_css_loaded(web_driver)
    assert_search_header(web_driver, viewport_width)

    tile_container = web_driver.find_element_by_id('tile-container')
    assert_start_tiles(tile_container)


def test_start_page_xs(web_driver_xs):
    """Tests the MyakuWeb start page with an extra small web driver."""
    assert_start_page(web_driver_xs)


def test_start_page_sm(web_driver_sm):
    """Tests the MyakuWeb start page with a small web driver."""
    assert_start_page(web_driver_sm)


def test_start_page_md(web_driver_md):
    """Tests the MyakuWeb start page with a medium web driver."""
    assert_start_page(web_driver_md)


def test_start_page_lg(web_driver_lg):
    """Tests the MyakuWeb start page with a large web driver."""
    assert_start_page(web_driver_lg)


def test_start_page_xl(web_driver_xl):
    """Tests the MyakuWeb start page with an extra large web driver."""
    assert_start_page(web_driver_xl)
