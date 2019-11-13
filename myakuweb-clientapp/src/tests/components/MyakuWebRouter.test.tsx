/**
 * Tests for the [[MyakuWebRouter]] component.
 */

import MainContent from 'ts/components/generic/MainContent';
import MyakuWebRouter from 'ts/components/MyakuWebRouter';
import React from 'react';
import SearchHeader from 'ts/components/header/SearchHeader';
import SearchResults from 'ts/components/search-results/SearchResults';
import StartContent from 'ts/components/start/StartContent';
import { act } from 'react-dom/test-utils';
import { createMemoryHistory } from 'history';
import { expectComponent } from 'tests/testUtils';
import { mount } from 'enzyme';

import {
    MemoryRouter,
    Router,
} from 'react-router-dom';

const SEARCH_HEADER_PROPS = {
    'loadingSearch': false,
    'location': expect.anything(),
    'history': expect.anything(),
};

const MAIN_CONTENT_PROPS = {
    'children': expect.anything(),
};

const SEARCH_RESULTS_PROPS = {
    'onLoadingNewSearchQueryChange': expect.any(Function),
    'location': expect.anything(),
    'history': expect.anything(),
};


jest.mock('ts/components/header/SearchHeader', () => jest.fn(() => null));
jest.mock(
    'ts/components/search-results/SearchResults', () => jest.fn(() => null)
);
jest.mock('ts/components/start/StartContent', () => jest.fn(() => null));

describe('<MyakuWebRouter /> navigation', function() {
    it('can navigate to start page', function() {
        const wrapper = mount(
            <MemoryRouter initialEntries={['/']}>
                <MyakuWebRouter />
            </MemoryRouter>
        );
        expectComponent(wrapper, SearchHeader, SEARCH_HEADER_PROPS);
        expectComponent(wrapper, MainContent, MAIN_CONTENT_PROPS);

        expectComponent(wrapper, StartContent, {});
        expect(wrapper.find(SearchResults)).toHaveLength(0);
    });

    it('can navigate to search result page', function() {
        const wrapper = mount(
            <MemoryRouter initialEntries={['/search/?q=OB']}>
                <MyakuWebRouter />
            </MemoryRouter>
        );
        expectComponent(wrapper, SearchHeader, SEARCH_HEADER_PROPS);
        expectComponent(wrapper, MainContent, MAIN_CONTENT_PROPS);

        expectComponent(wrapper, SearchResults, SEARCH_RESULTS_PROPS);
        expect(wrapper.find(StartContent)).toHaveLength(0);
    });
});

describe('<MyakuWebRouter /> scroll on history change', function() {
    var history = createMemoryHistory();
    beforeEach(function() {
        window.scrollTo = jest.fn();

        history = createMemoryHistory();
        history.push('/');
        history.push('/');
        history.push('/search/?q=OB');
        history.goBack();
        mount(
            <Router history={history}>
                <MyakuWebRouter />
            </Router>
        );
    });

    it('scrolls to top on history push', function() {
        const scrollToSpy = jest.spyOn(window, 'scrollTo');
        act(() => history.push('/search/?q=OB'));
        expect(scrollToSpy).toBeCalledTimes(1);
        expect(scrollToSpy).toBeCalledWith(0, 0);
    });

    it('scrolls to top on history replace', function() {
        const scrollToSpy = jest.spyOn(window, 'scrollTo');
        act(() => history.replace('/search/?q=OB'));
        expect(scrollToSpy).toBeCalledTimes(1);
        expect(scrollToSpy).toBeCalledWith(0, 0);
    });

    it('scrolls to top on history back', function() {
        const scrollToSpy = jest.spyOn(window, 'scrollTo');
        act(() => history.goBack());
        expect(scrollToSpy).toBeCalledTimes(1);
        expect(scrollToSpy).toBeCalledWith(0, 0);
    });

    it('scrolls to top on history forward', function() {
        const scrollToSpy = jest.spyOn(window, 'scrollTo');
        act(() => history.goForward());
        expect(scrollToSpy).toBeCalledTimes(1);
        expect(scrollToSpy).toBeCalledWith(0, 0);
    });
});
