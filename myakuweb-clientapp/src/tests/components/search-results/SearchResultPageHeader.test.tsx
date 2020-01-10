/**
 * Tests for the [[SearchResultPageHeader]] component.
 */

import { MAX_DISPLAY_PAGE_NUM } from
    'ts/components/search-results/SearchResultPageHeader';
import React from 'react';
import { Search } from 'ts/types/types';
import SearchResultPageHeader from
    'ts/components/search-results/SearchResultPageHeader';

import {
    render,
    shallow,
} from 'enzyme';

const SAMPLE_SEARCH: Search = {
    query: '力士',
    pageNum: 1,
};

const SAMPLE_SEARCH_LARGE_PAGENUM: Search = {
    query: '力士',
    pageNum: MAX_DISPLAY_PAGE_NUM + 1,
};


describe('<SearchResultPageHeader />', function() {
    it(
        'renders correctly with null total results/null search',
        function() {
            const wrapper = shallow(
                <SearchResultPageHeader
                    search={null}
                    totalResults={null}
                />
            );
            expect(wrapper).toMatchSnapshot();
        }
    );

    it(
        'renders correctly with non-null total results/null search',
        function() {
            const wrapper = shallow(
                <SearchResultPageHeader
                    search={null}
                    totalResults={155}
                />
            );
            expect(wrapper).toMatchSnapshot();
        }
    );

    it(
        'renders correctly with null total results/non-null search',
        function() {
            const wrapper = shallow(
                <SearchResultPageHeader
                    search={SAMPLE_SEARCH}
                    totalResults={null}
                />
            );
            expect(wrapper).toMatchSnapshot();
        }
    );

    it(
        'renders correctly with non-null total results/non-null search',
        function() {
            const wrapper = shallow(
                <SearchResultPageHeader
                    search={SAMPLE_SEARCH}
                    totalResults={155}
                />
            );
            expect(wrapper).toMatchSnapshot();
        }
    );

    it('does not show page num if 0 total results', function() {
        const wrapper = shallow(
            <SearchResultPageHeader
                search={SAMPLE_SEARCH}
                totalResults={0}
            />
        );
        expect(wrapper.text()).not.toStrictEqual(
            expect.stringContaining('Page')
        );
        expect(wrapper.text()).not.toStrictEqual(
            expect.stringContaining('1')
        );
    });

    it('uses int comma for total results', function() {
        const wrapper = render(
            <SearchResultPageHeader
                search={SAMPLE_SEARCH}
                totalResults={3444555}
            />
        );
        expect(wrapper.text()).toStrictEqual(
            expect.stringContaining('3,444,555 found')
        );
    });

    it('shows query if 0 total results', function() {
        const wrapper = render(
            <SearchResultPageHeader
                search={SAMPLE_SEARCH}
                totalResults={0}
            />
        );
        expect(wrapper.text()).toStrictEqual(
            expect.stringContaining('力士')
        );
    });

    it('does not show query if at least 1 total result', function() {
        const wrapper = render(
            <SearchResultPageHeader
                search={SAMPLE_SEARCH}
                totalResults={1}
            />
        );
        expect(wrapper.text()).not.toStrictEqual(
            expect.stringContaining('力士')
        );
    });

    it('renders max page num if less than search page num', function() {
        const wrapper = render(
            <SearchResultPageHeader
                search={SAMPLE_SEARCH_LARGE_PAGENUM}
                totalResults={3444555}
            />
        );
        expect(wrapper.text()).toStrictEqual(
            expect.stringContaining(`Page ${MAX_DISPLAY_PAGE_NUM}`)
        );
        expect(wrapper.text()).not.toStrictEqual(
            expect.stringContaining(
                `Page ${SAMPLE_SEARCH_LARGE_PAGENUM.pageNum}`
            )
        );
    });
});
