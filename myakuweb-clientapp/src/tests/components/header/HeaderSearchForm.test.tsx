/**
 * Tests for the [[HeaderSearchForm]] component.
 */

import Collapsable from 'ts/components/generic/Collapsable';
import HeaderSearchForm from 'ts/components/header/HeaderSearchForm';
import React from 'react';
import SearchBarInput from 'ts/components/header/SearchBarInput';
import { SearchOptions } from 'ts/types/types';
import SearchOptionsCollapseToggle from
    'ts/components/header/SearchOptionsCollapseToggle';
import SearchOptionsInput from 'ts/components/header/SearchOptionsInput';
import { act } from 'react-dom/test-utils';
import { blurActiveElement } from 'ts/app/utils';
import { createMemoryHistory } from 'history';
import { expectComponent } from 'tests/testUtils';

import {
    ShallowWrapper,
    shallow,
} from 'enzyme';
import {
    loadUserSearchOptions,
    setUserSearchOption,
} from 'ts/app/search';

const mockLoadUserSearchOptions = loadUserSearchOptions as jest.Mock;
const mockSetUserSearchOption = setUserSearchOption as jest.Mock;
const mockBlurActiveElement = blurActiveElement as jest.Mock;
const mockPromise = {
    then: (): void => {},
    catch: (): void => {},
};

/**
 * Mock only the async functions from the search module to avoid getting errors
 * when these functions get called in HeaderSearchForm during synchronous
 * tests.
 */
jest.mock('ts/app/search', function() {
    const original = jest.requireActual('ts/app/search');

    return {
        __esModule: true,
        ...original,
        loadUserSearchOptions: jest.fn(function() {
            return mockPromise;
        }),
        setUserSearchOption: jest.fn(function() {
            return mockPromise;
        }),
    };
});

jest.mock('ts/app/utils', function() {
    const original = jest.requireActual('ts/app/utils');

    return {
        __esModule: true,
        ...original,
        blurActiveElement: jest.fn(() => {}),
    };
});

var history = createMemoryHistory();
var wrapper = shallow(<div />);
beforeEach(function() {
    mockLoadUserSearchOptions.mockClear();
    mockSetUserSearchOption.mockClear();
    mockBlurActiveElement.mockClear();

    history = createMemoryHistory();
    wrapper = shallow(
        <HeaderSearchForm
            loadingSearch={false}
            location={history.location}
            history={history}
        />
    );
});


function expectSearchBarLoading(
    wrapper: ShallowWrapper, loading: boolean
): void {
    expectComponent(wrapper, SearchBarInput, {
        searchQuery: expect.any(String),
        loading: loading,
        maxQueryLength: expect.any(Number),
        errorValueSubmitted: false,
        onChange: expect.any(Function),
    });
}

function expectSearchBarQuery(
    wrapper: ShallowWrapper, query: string
): void {
    expectComponent(wrapper, SearchBarInput, {
        searchQuery: query,
        loading: false,
        maxQueryLength: expect.any(Number),
        errorValueSubmitted: false,
        onChange: expect.any(Function),
    });
}

function expectSearchBarError(
    wrapper: ShallowWrapper, errorValueSubmitted: boolean
): void {
    expectComponent(wrapper, SearchBarInput, {
        searchQuery: expect.any(String),
        loading: false,
        maxQueryLength: expect.any(Number),
        errorValueSubmitted: errorValueSubmitted,
        onChange: expect.any(Function),
    });
}

function expectSearchOptionsCollapsed(
    wrapper: ShallowWrapper, collapsed: boolean,
    animate: boolean = expect.any(Boolean)
): void {
    expectComponent(wrapper, Collapsable, {
        collapsed: collapsed,
        animate: animate,
        onAnimationEnd: expect.any(Function),
        children: expect.anything(),
    });
}

function expectSearchOptions(
    wrapper: ShallowWrapper, options: SearchOptions
): void {
    expectComponent(wrapper, SearchOptionsInput, {
        searchOptions: options,
        onChange: expect.any(Function),
    });
}

function expectStartHistory(): void {
    expect(history).toHaveLength(1);
    expect(history.location.pathname).toBe('/');
    expect(history.location.search).toBe('');
}

function expectSearchHistoryLocation(
    query: string, historyLength: number
): void {
    expect(history).toHaveLength(historyLength);
    expect(history.location.pathname).toBe('/search/');
    expect(history.location.search).toBe(`?q=${query}&p=1`);
}

function toggleSearchOptionsCollapse(wrapper: ShallowWrapper): void {
    const collapseToggle = wrapper.find(SearchOptionsCollapseToggle);
    expect(collapseToggle).toHaveLength(1);
    act(() => collapseToggle.props().onToggle());
}

function uncollapseSearchOptions(wrapper: ShallowWrapper): void {
    expectSearchOptionsCollapsed(wrapper, true);
    toggleSearchOptionsCollapse(wrapper);
    expectSearchOptionsCollapsed(wrapper, false);
}

function mockCollapseOnAnimationEndEvent(wrapper: ShallowWrapper): void {
    const collapsable = wrapper.find(Collapsable);
    expect(collapsable).toHaveLength(1);

    const onAnimationEnd = collapsable.props().onAnimationEnd;
    if (onAnimationEnd === undefined) {
        throw new Error(
            'Search options collapsable has no onAnimationEnd callback set'
        );
    }
    act(() => onAnimationEnd());
}

function inputSearchQuery(wrapper: ShallowWrapper, query: string): void {
    const searchBarInput = wrapper.find(SearchBarInput);
    expect(searchBarInput).toHaveLength(1);
    act(() => searchBarInput.props().onChange(query));
}

function inputSearchOption<K extends keyof SearchOptions>(
    wrapper: ShallowWrapper, option: K, value: SearchOptions[K]
): void {
    const searchOptionsInput = wrapper.find(SearchOptionsInput);
    expect(SearchOptionsInput).toHaveLength(1);
    act(() => searchOptionsInput.props().onChange(option, value));
}

async function inputSearchOptionAsync<K extends keyof SearchOptions>(
    wrapper: ShallowWrapper, option: K, value: SearchOptions[K]
): Promise<void> {
    const searchOptionsInput = wrapper.find(SearchOptionsInput);
    expect(SearchOptionsInput).toHaveLength(1);
    act(() => searchOptionsInput.props().onChange(option, value));
}

function simulateMockSubmitEvent(wrapper: ShallowWrapper): jest.Mock {
    const mockPreventDefault = jest.fn();
    wrapper.simulate('submit', {preventDefault: mockPreventDefault});

    return mockPreventDefault;
}

async function getShallowWrapperAsync(): Promise<ShallowWrapper> {
    return shallow(
        <HeaderSearchForm
            loadingSearch={false}
            location={history.location}
            history={history}
        />
    );
}


describe('<HeaderSearchForm /> mount/unmount/page change', function() {
    it('renders correctly', function() {
        expect(wrapper).toMatchSnapshot();
    });

    it('sets rendered components as loading when loading', function() {
        expectSearchBarLoading(wrapper, false);

        wrapper.setProps({loadingSearch: true});
        expectSearchBarLoading(wrapper, true);
    });

    it('sets search query from location on mount', function() {
        act(() => history.push('/'));
        wrapper = shallow(
            <HeaderSearchForm
                loadingSearch={false}
                location={history.location}
                history={history}
            />
        );
        expectSearchBarQuery(wrapper, '');

        act(() => history.push('/search/?q=力士'));
        wrapper = shallow(
            <HeaderSearchForm
                loadingSearch={false}
                location={history.location}
                history={history}
            />
        );
        expectSearchBarQuery(wrapper, '力士');

        act(() => history.push('/search/?q=OB&p=1'));
        wrapper = shallow(
            <HeaderSearchForm
                loadingSearch={false}
                location={history.location}
                history={history}
            />
        );
        expectSearchBarQuery(wrapper, 'OB');
    });

    it('sets search query from location on history change', function() {
        act(() => history.push('/search/?q=力士'));
        expectSearchBarQuery(wrapper, '力士');

        act(() => history.push('/search/?q=OB&p=1'));
        expectSearchBarQuery(wrapper, 'OB');

        act(() => history.push('/'));
        expectSearchBarQuery(wrapper, '');
    });

    it('unlistens to history changes on unmount', function() {
        wrapper.unmount();
        expect(() => history.push('/search/?q=OB')).not.toThrow();
    });

    it('collapses search options by default on mount', function() {
        expectSearchOptionsCollapsed(wrapper, true, false);
    });

    it('resets search options to collapsed on history change', function() {
        uncollapseSearchOptions(wrapper);
        history.push('/search/?q=OB');
        expectSearchOptionsCollapsed(wrapper, true, false);

        uncollapseSearchOptions(wrapper);
        history.goBack();
        expectSearchOptionsCollapsed(wrapper, true, false);

        uncollapseSearchOptions(wrapper);
        history.goForward();
        expectSearchOptionsCollapsed(wrapper, true, false);

        uncollapseSearchOptions(wrapper);
        history.replace('/');
        expectSearchOptionsCollapsed(wrapper, true, false);
    });

    it('loads session search options on mount', async function() {
        mockLoadUserSearchOptions.mockResolvedValue({kanaConvertType: 'hira'});
        const wrapperHira = await getShallowWrapperAsync();
        expectSearchOptions(wrapperHira, {kanaConvertType: 'hira'});

        mockLoadUserSearchOptions.mockResolvedValue({kanaConvertType: 'kata'});
        const wrapperKata = await getShallowWrapperAsync();
        expectSearchOptions(wrapperKata, {kanaConvertType: 'kata'});

        mockLoadUserSearchOptions.mockResolvedValue({kanaConvertType: 'none'});
        const wrapperNone = await getShallowWrapperAsync();
        expectSearchOptions(wrapperNone, {kanaConvertType: 'none'});
    });

    it('logs warning on mount if no IndexedDB available', async function() {
        const mockConsoleWarning = jest.spyOn(console, 'warn');
        mockConsoleWarning.mockImplementation(() => {});
        mockLoadUserSearchOptions.mockRejectedValueOnce(new Error('error'));

        await getShallowWrapperAsync();
        expect(mockConsoleWarning).toBeCalledTimes(1);
        expect(mockConsoleWarning).lastCalledWith(
            expect.stringContaining('Unable to use IndexedDB')
        );
    });
});

describe('<HeaderSearchForm /> form submit', function() {
    var form = shallow(<div />);
    beforeEach(function() {
        form = wrapper.find('form');
    });

    it('pushes search URL to history on valid form submit', function() {
        inputSearchQuery(wrapper, 'ゆっくり');
        simulateMockSubmitEvent(form);
        expectSearchHistoryLocation('ゆっくり', 2);

        inputSearchQuery(wrapper, 'ゆっくり');
        simulateMockSubmitEvent(form);
        expectSearchHistoryLocation('ゆっくり', 3);

        inputSearchQuery(wrapper, '力士');
        simulateMockSubmitEvent(form);
        expectSearchHistoryLocation('力士', 4);
    });

    it('stops query too long form submit', function() {
        var longStrList = [];
        for (let i = 0; i < 100; ++i) {
            longStrList.push('ゆっくり');
        }
        expectSearchBarError(wrapper, false);
        expectStartHistory();

        inputSearchQuery(wrapper, longStrList.join(''));
        simulateMockSubmitEvent(form);
        expectStartHistory();
        expectSearchBarError(wrapper, true);
    });

    it('stops no query form submit', function() {
        expectSearchBarError(wrapper, false);
        expectStartHistory();

        inputSearchQuery(wrapper, '');
        simulateMockSubmitEvent(form);
        expectStartHistory();
        expectSearchBarError(wrapper, true);
    });

    it('applies hiragana conversion on from submit', function() {
        inputSearchQuery(wrapper, 'yukkuri');
        inputSearchOption(wrapper, 'kanaConvertType', 'hira');
        simulateMockSubmitEvent(form);
        expectSearchHistoryLocation('ゆっくり', 2);
        expectSearchBarQuery(wrapper, 'ゆっくり');
    });

    it('applies katakana conversion on from submit', function() {
        inputSearchQuery(wrapper, 'yukkuri');
        inputSearchOption(wrapper, 'kanaConvertType', 'kata');
        simulateMockSubmitEvent(form);
        expectSearchHistoryLocation('ユックリ', 2);
        expectSearchBarQuery(wrapper, 'ユックリ');
    });

    it('applies none conversion on from submit', function() {
        inputSearchQuery(wrapper, 'yukkuri');
        inputSearchOption(wrapper, 'kanaConvertType', 'none');
        simulateMockSubmitEvent(form);
        expectSearchHistoryLocation('yukkuri', 2);
        expectSearchBarQuery(wrapper, 'yukkuri');
    });

    it('applies no query conversion if query is not romaji', function() {
        inputSearchQuery(wrapper, 'ユックリ');
        inputSearchOption(wrapper, 'kanaConvertType', 'hira');
        simulateMockSubmitEvent(form);
        expectSearchHistoryLocation('ユックリ', 2);
        expectSearchBarQuery(wrapper, 'ユックリ');

        inputSearchQuery(wrapper, 'ゆっくり');
        inputSearchOption(wrapper, 'kanaConvertType', 'kata');
        simulateMockSubmitEvent(form);
        expectSearchHistoryLocation('ゆっくり', 3);
        expectSearchBarQuery(wrapper, 'ゆっくり');
    });

    it('blurs focus on form submit', function() {
        inputSearchQuery(wrapper, 'ゆっくり');

        mockBlurActiveElement.mockClear();
        simulateMockSubmitEvent(form);
        expect(mockBlurActiveElement).toBeCalledTimes(1);
    });

    it('clears submit error on history change', function() {
        inputSearchQuery(wrapper, '');

        simulateMockSubmitEvent(form);
        expectSearchBarError(wrapper, true);
        act(() => history.push('/'));
        expectSearchBarError(wrapper, false);

        simulateMockSubmitEvent(form);
        expectSearchBarError(wrapper, true);
        act(() => history.goBack());
        expectSearchBarError(wrapper, false);

        simulateMockSubmitEvent(form);
        expectSearchBarError(wrapper, true);
        act(() => history.goForward());
        expectSearchBarError(wrapper, false);

        simulateMockSubmitEvent(form);
        expectSearchBarError(wrapper, true);
        act(() => history.replace('/search/?q=OB'));
        expectSearchBarError(wrapper, false);
    });

    it('clears submit error on inputted search query change', function() {
        inputSearchQuery(wrapper, '');
        simulateMockSubmitEvent(form);
        expectSearchBarError(wrapper, true);

        inputSearchQuery(wrapper, 'test');
        expectSearchBarError(wrapper, false);
    });

    it('prevents default of the form submit event', function() {
        inputSearchQuery(wrapper, 'ゆっくり');
        const mockPreventDefault = simulateMockSubmitEvent(form);
        expect(mockPreventDefault).toBeCalledTimes(1);
    });
});

describe('<HeaderSearchForm /> form event handlers', function() {
    it('handles inputted search query changes', function() {
        inputSearchQuery(wrapper, 'ゆっくり');
        expectSearchBarQuery(wrapper, 'ゆっくり');

        inputSearchQuery(wrapper, '');
        expectSearchBarQuery(wrapper, '');

        inputSearchQuery(wrapper, 'OB');
        expectSearchBarQuery(wrapper, 'OB');
    });

    it('handles inputted search option changes', function() {
        inputSearchOption(wrapper, 'kanaConvertType', 'hira');
        expectSearchOptions(wrapper, {kanaConvertType: 'hira'});

        inputSearchOption(wrapper, 'kanaConvertType', 'kata');
        expectSearchOptions(wrapper, {kanaConvertType: 'kata'});

        inputSearchOption(wrapper, 'kanaConvertType', 'none');
        expectSearchOptions(wrapper, {kanaConvertType: 'none'});
    });

    it('saves inputted search option changes to session', function() {
        inputSearchOption(wrapper, 'kanaConvertType', 'hira');
        expect(mockSetUserSearchOption).toBeCalledTimes(1);
        expect(mockSetUserSearchOption).lastCalledWith(
            'kanaConvertType', 'hira'
        );

        inputSearchOption(wrapper, 'kanaConvertType', 'kata');
        expect(mockSetUserSearchOption).toBeCalledTimes(2);
        expect(mockSetUserSearchOption).lastCalledWith(
            'kanaConvertType', 'kata'
        );

        inputSearchOption(wrapper, 'kanaConvertType', 'none');
        expect(mockSetUserSearchOption).toBeCalledTimes(3);
        expect(mockSetUserSearchOption).lastCalledWith(
            'kanaConvertType', 'none'
        );
    });

    it(
        'logs warning on search option change if no IndexedDB available',
        async function() {
            const mockConsoleWarning = jest.spyOn(console, 'warn');
            mockConsoleWarning.mockImplementation(() => {});
            mockSetUserSearchOption.mockRejectedValueOnce(new Error('error'));

            wrapper = await getShallowWrapperAsync();
            mockConsoleWarning.mockClear();
            await inputSearchOptionAsync(wrapper, 'kanaConvertType', 'kata');
            expect(mockConsoleWarning).toBeCalledTimes(1);
            expect(mockConsoleWarning).lastCalledWith(
                expect.stringContaining('Unable to use IndexedDB')
            );
        }
    );

    it('handles search options collapse toggle', function() {
        expectSearchOptionsCollapsed(wrapper, true, false);

        toggleSearchOptionsCollapse(wrapper);
        expectSearchOptionsCollapsed(wrapper, false, true);

        mockCollapseOnAnimationEndEvent(wrapper);
        toggleSearchOptionsCollapse(wrapper);
        expectSearchOptionsCollapsed(wrapper, true, true);

        mockCollapseOnAnimationEndEvent(wrapper);
        toggleSearchOptionsCollapse(wrapper);
        expectSearchOptionsCollapsed(wrapper, false, true);
    });

    it('ignores search options collapse toggle if animating', function() {
        expectSearchOptionsCollapsed(wrapper, true, false);

        toggleSearchOptionsCollapse(wrapper);
        expectSearchOptionsCollapsed(wrapper, false, true);

        toggleSearchOptionsCollapse(wrapper);
        expectSearchOptionsCollapsed(wrapper, false, true);

        mockCollapseOnAnimationEndEvent(wrapper);
        toggleSearchOptionsCollapse(wrapper);
        expectSearchOptionsCollapsed(wrapper, true, true);

        toggleSearchOptionsCollapse(wrapper);
        expectSearchOptionsCollapsed(wrapper, true, true);
    });
});
