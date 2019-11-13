/**
 * Tests for the [[SearchResultPageNav]] component.
 */

import { LinkProps } from 'react-router-dom';
import React from 'react';
import { Search } from 'ts/types/types';
import SearchResultPageNav from
    'ts/components/search-results/SearchResultPageNav';
import { getSearchUrl } from 'ts/app/search';

import {
    ShallowWrapper,
    shallow,
} from 'enzyme';

function expectNextPageLink(
    wrapper: ShallowWrapper, search: Search | null
): void {
    const nextPageLink = wrapper.findWhere(function(node: ShallowWrapper) {
        return node.name() === 'Link' && node.key() === 'next';
    }) as ShallowWrapper<LinkProps>;

    if (search === null) {
        expect(nextPageLink).toHaveLength(0);
    } else {
        expect(nextPageLink).toHaveLength(1);

        const nextPageSearch = {
            ...search,
            pageNum: search.pageNum + 1,
        };
        expect(nextPageLink.props().to).toBe(getSearchUrl(nextPageSearch));
    }
}

function expectPrevPageLink(
    wrapper: ShallowWrapper, search: Search | null
): void {
    const prevPageLink = wrapper.findWhere(function(node: ShallowWrapper) {
        return node.name() === 'Link' && node.key() === 'previous';
    }) as ShallowWrapper<LinkProps>;

    if (search === null) {
        expect(prevPageLink).toHaveLength(0);
    } else {
        expect(prevPageLink).toHaveLength(1);

        const nextPageSearch = {
            ...search,
            pageNum: search.pageNum - 1,
        };
        expect(prevPageLink.props().to).toBe(getSearchUrl(nextPageSearch));
    }
}

function findTopButton(wrapper: ShallowWrapper): ShallowWrapper {
    return wrapper.findWhere(function(node: ShallowWrapper) {
        return node.name() === 'button' && node.key() === 'top';
    });
}

function expectTopButton(wrapper: ShallowWrapper, showing: boolean): void {
    const topButton = findTopButton(wrapper);
    if (showing) {
        expect(topButton).toHaveLength(1);
    } else {
        expect(topButton).toHaveLength(0);
    }
}

function expectMaxPageReached(
    wrapper: ShallowWrapper, showing: boolean
): void {
    const maxPageReached = wrapper.findWhere(function(node: ShallowWrapper) {
        return node.name() === 'span' && node.key() === 'max-page';
    });

    if (showing) {
        expect(maxPageReached).toHaveLength(1);
    } else {
        expect(maxPageReached).toHaveLength(0);
    }
}

function expectEndOfResults(wrapper: ShallowWrapper, showing: boolean): void {
    const endOfResults = wrapper.findWhere(function(node: ShallowWrapper) {
        return node.name() === 'span' && node.key() === 'end';
    });

    if (showing) {
        expect(endOfResults).toHaveLength(1);
    } else {
        expect(endOfResults).toHaveLength(0);
    }
}


describe('<SearchResultPageNav /> top button', function() {
    it('scrolls to top on click', function() {
        const search: Search = {
            query: 'OB',
            pageNum: 1,
        };
        const wrapper = shallow(
            <SearchResultPageNav
                search={search}
                hasNextPage={true}
                maxPageReached={false}
            />
        );
        expectTopButton(wrapper, true);

        const mockScrollTo = jest.spyOn(window, 'scrollTo');
        mockScrollTo.mockImplementation(() => {});

        findTopButton(wrapper).simulate('click');
        expect(mockScrollTo).toBeCalledTimes(1);
        expect(mockScrollTo).lastCalledWith(0, 0);
    });
});

describe('<SearchResultPageNav /> at page 1', function() {
    var search: Search = {
        query: 'OB',
        pageNum: 1,
    };
    beforeEach(function() {
        search = {
            query: 'OB',
            pageNum: 1,
        };
    });

    it('renders with next page correctly', function() {
        const wrapper = shallow(
            <SearchResultPageNav
                search={search}
                hasNextPage={true}
                maxPageReached={false}
            />
        );
        expectNextPageLink(wrapper, search);
        expectPrevPageLink(wrapper, null);
        expectTopButton(wrapper, true);
        expectEndOfResults(wrapper, false);
        expectMaxPageReached(wrapper, false);
    });

    it('renders without next page correctly', function() {
        const wrapper = shallow(
            <SearchResultPageNav
                search={search}
                hasNextPage={false}
                maxPageReached={false}
            />
        );
        expectNextPageLink(wrapper, null);
        expectPrevPageLink(wrapper, null);
        expectTopButton(wrapper, true);
        expectEndOfResults(wrapper, true);
        expectMaxPageReached(wrapper, false);
    });

    it('renders at max page no next page correctly', function() {
        const wrapper = shallow(
            <SearchResultPageNav
                search={search}
                hasNextPage={false}
                maxPageReached={true}
            />
        );
        expectNextPageLink(wrapper, null);
        expectPrevPageLink(wrapper, null);
        expectTopButton(wrapper, true);
        expectEndOfResults(wrapper, false);
        expectMaxPageReached(wrapper, true);
    });

    it('renders at max page with next page correctly', function() {
        const wrapper = shallow(
            <SearchResultPageNav
                search={search}
                hasNextPage={true}
                maxPageReached={true}
            />
        );
        expectNextPageLink(wrapper, null);
        expectPrevPageLink(wrapper, null);
        expectTopButton(wrapper, true);
        expectEndOfResults(wrapper, false);
        expectMaxPageReached(wrapper, true);
    });
});

describe('<SearchResultPageNav /> at page 2', function() {
    var search: Search = {
        query: 'OB',
        pageNum: 2,
    };
    beforeEach(function() {
        search = {
            query: 'OB',
            pageNum: 2,
        };
    });

    it('renders with next page correctly', function() {
        const wrapper = shallow(
            <SearchResultPageNav
                search={search}
                hasNextPage={true}
                maxPageReached={false}
            />
        );
        expectNextPageLink(wrapper, search);
        expectPrevPageLink(wrapper, search);
        expectTopButton(wrapper, true);
        expectEndOfResults(wrapper, false);
        expectMaxPageReached(wrapper, false);
    });

    it('renders without next page correctly', function() {
        const wrapper = shallow(
            <SearchResultPageNav
                search={search}
                hasNextPage={false}
                maxPageReached={false}
            />
        );
        expectNextPageLink(wrapper, null);
        expectPrevPageLink(wrapper, search);
        expectTopButton(wrapper, true);
        expectEndOfResults(wrapper, true);
        expectMaxPageReached(wrapper, false);
    });

    it('renders at max page no next page correctly', function() {
        const wrapper = shallow(
            <SearchResultPageNav
                search={search}
                hasNextPage={false}
                maxPageReached={true}
            />
        );
        expectNextPageLink(wrapper, null);
        expectPrevPageLink(wrapper, search);
        expectTopButton(wrapper, true);
        expectEndOfResults(wrapper, false);
        expectMaxPageReached(wrapper, true);
    });

    it('renders at max page with next page correctly', function() {
        const wrapper = shallow(
            <SearchResultPageNav
                search={search}
                hasNextPage={true}
                maxPageReached={true}
            />
        );
        expectNextPageLink(wrapper, null);
        expectPrevPageLink(wrapper, search);
        expectTopButton(wrapper, true);
        expectEndOfResults(wrapper, false);
        expectMaxPageReached(wrapper, true);
    });
});

describe('<SearchResultPageNav /> at page >2', function() {
    var search: Search = {
        query: 'OB',
        pageNum: 25,
    };
    beforeEach(function() {
        search = {
            query: 'OB',
            pageNum: 25,
        };
    });

    it('renders with next page correctly', function() {
        const wrapper = shallow(
            <SearchResultPageNav
                search={search}
                hasNextPage={true}
                maxPageReached={false}
            />
        );
        expectNextPageLink(wrapper, search);
        expectPrevPageLink(wrapper, search);
        expectTopButton(wrapper, true);
        expectEndOfResults(wrapper, false);
        expectMaxPageReached(wrapper, false);
    });

    it('renders without next page correctly', function() {
        const wrapper = shallow(
            <SearchResultPageNav
                search={search}
                hasNextPage={false}
                maxPageReached={false}
            />
        );
        expectNextPageLink(wrapper, null);
        expectPrevPageLink(wrapper, search);
        expectTopButton(wrapper, true);
        expectEndOfResults(wrapper, true);
        expectMaxPageReached(wrapper, false);
    });

    it('renders at max page no next page correctly', function() {
        const wrapper = shallow(
            <SearchResultPageNav
                search={search}
                hasNextPage={false}
                maxPageReached={true}
            />
        );
        expectNextPageLink(wrapper, null);
        expectPrevPageLink(wrapper, search);
        expectTopButton(wrapper, true);
        expectEndOfResults(wrapper, false);
        expectMaxPageReached(wrapper, true);
    });

    it('renders at max page with next page correctly', function() {
        const wrapper = shallow(
            <SearchResultPageNav
                search={search}
                hasNextPage={true}
                maxPageReached={true}
            />
        );
        expectNextPageLink(wrapper, null);
        expectPrevPageLink(wrapper, search);
        expectTopButton(wrapper, true);
        expectEndOfResults(wrapper, false);
        expectMaxPageReached(wrapper, true);
    });
});

describe('<SearchResultPageNav /> at page <1', function() {
    var search: Search = {
        query: 'OB',
        pageNum: -5,
    };
    beforeEach(function() {
        search = {
            query: 'OB',
            pageNum: -5,
        };
    });

    it('renders with next page correctly', function() {
        const wrapper = shallow(
            <SearchResultPageNav
                search={search}
                hasNextPage={true}
                maxPageReached={false}
            />
        );
        expectNextPageLink(wrapper, search);
        expectPrevPageLink(wrapper, null);
        expectTopButton(wrapper, true);
        expectEndOfResults(wrapper, false);
        expectMaxPageReached(wrapper, false);
    });

    it('renders without next page correctly', function() {
        const wrapper = shallow(
            <SearchResultPageNav
                search={search}
                hasNextPage={false}
                maxPageReached={false}
            />
        );
        expectNextPageLink(wrapper, null);
        expectPrevPageLink(wrapper, null);
        expectTopButton(wrapper, true);
        expectEndOfResults(wrapper, true);
        expectMaxPageReached(wrapper, false);
    });

    it('renders at max page no next page correctly', function() {
        const wrapper = shallow(
            <SearchResultPageNav
                search={search}
                hasNextPage={false}
                maxPageReached={true}
            />
        );
        expectNextPageLink(wrapper, null);
        expectPrevPageLink(wrapper, null);
        expectTopButton(wrapper, true);
        expectEndOfResults(wrapper, false);
        expectMaxPageReached(wrapper, true);
    });

    it('renders at max page with next page correctly', function() {
        const wrapper = shallow(
            <SearchResultPageNav
                search={search}
                hasNextPage={true}
                maxPageReached={true}
            />
        );
        expectNextPageLink(wrapper, null);
        expectPrevPageLink(wrapper, null);
        expectTopButton(wrapper, true);
        expectEndOfResults(wrapper, false);
        expectMaxPageReached(wrapper, true);
    });
});
