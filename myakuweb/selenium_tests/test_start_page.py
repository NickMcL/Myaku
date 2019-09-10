"""Web driver tests for MyakuWeb."""

import os

from seleniumwire import webdriver
from selenium.webdriver import firefox

import pytest

_REVERSEPROXY_HOST_ENV_VAR = 'REVERSEPROXY_HOST'


@pytest.fixture
def web_driver():
    """Inits a headless Firefox web driver for testing."""
    options = firefox.options.Options()
    options.headless = True
    test_web_driver = webdriver.Firefox(options=options)

    # When the reverseproxy service is using the dev/test allowed hosts list,
    # it will only accept connections with the host header set as localhost, so
    # we must override the host header on selenium's requests to be localhost.
    test_web_driver.header_overrides = {'Host': 'localhost'}

    yield test_web_driver
    test_web_driver.close()


def _go_to_start_page(web_driver) -> None:
    """Goes to the MyakuWeb start page with the web driver."""
    host = os.environ[_REVERSEPROXY_HOST_ENV_VAR]
    web_driver.get(f'http://{host}/')


def _go_to_search_result_page(web_driver, query: str) -> None:
    """Goes to the MyakuWeb start page with the web driver."""
    host = os.environ[_REVERSEPROXY_HOST_ENV_VAR]
    web_driver.get(f'http://{host}/?q={query}')


def test_start_page(web_driver):
    """Tests the MyakuWeb start page with the web driver."""
    _go_to_start_page(web_driver)
    assert web_driver.find_element_by_id('search-input') is not None
