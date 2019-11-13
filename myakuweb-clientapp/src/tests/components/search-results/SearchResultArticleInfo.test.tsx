/**
 * Tests for the [[SearchResultArticleInfo]] component.
 */

import React from 'react';
import SearchResultArticleInfo from
    'ts/components/search-results/SearchResultArticleInfo';

import {
    BASELINE_SEARCH_RESULT_PAGE,
    getSearchResultPageDataClone,
} from 'tests/testData';
import {
    ShallowWrapper,
    render,
    shallow,
} from 'enzyme';

var searchResult = BASELINE_SEARCH_RESULT_PAGE.results[0];
beforeEach(function() {
    searchResult = getSearchResultPageDataClone().results[0];
});

function expectLastUpdatedTimeShowing(showing: boolean): void {
    const wrapper = shallow(
        <SearchResultArticleInfo
            searchResult={searchResult}
        />
    );

    const lastUpdatedTimeLi = wrapper.findWhere(
        function(node: ShallowWrapper) {
            return node.name() === 'li' && node.key() === 'updated-datetime';
        }
    );
    expect(lastUpdatedTimeLi).toHaveLength(Number(showing));
}

function getDateDaysBeforeNow(days: number): Date {
    const now = new Date();
    return new Date(now.setDate(now.getDate() - days));
}

function getDateDaysBeforeDate(date: Date, days: number): Date {
    const clone = new Date(date.getTime());
    return new Date(clone.setDate(clone.getDate() - days));
}

function getDateDaysAfterDate(date: Date, days: number): Date {
    const clone = new Date(date.getTime());
    return new Date(clone.setDate(clone.getDate() + days));
}

function getDateMinutesAfterDate(date: Date, minutes: number): Date {
    const clone = new Date(date.getTime());
    return new Date(clone.setMinutes(clone.getMinutes() + minutes));
}


describe('<SearchResultArticleInfo /> render', function() {
    it('renders correctly with last updated time', function() {
        const wrapper = shallow(
            <SearchResultArticleInfo
                searchResult={searchResult}
            />
        );
        expect(wrapper).toMatchSnapshot();
    });

    it('renders correctly without last updated time', function() {
        searchResult.lastUpdatedDatetime = null;

        const wrapper = shallow(
            <SearchResultArticleInfo
                searchResult={searchResult}
            />
        );
        expect(wrapper).toMatchSnapshot();
    });

    it('uses int comma for instance count', function() {
        searchResult.instanceCount = 1222333;

        const wrapper = render(
            <SearchResultArticleInfo
                searchResult={searchResult}
            />
        );
        expect(wrapper.text()).toStrictEqual(
            expect.stringContaining('1,222,333 instances')
        );
    });
});

describe('<SearchResultArticleInfo /> last updated time', function() {
    it('does not display if same day as publication', function() {
        searchResult.lastUpdatedDatetime = getDateMinutesAfterDate(
            searchResult.publicationDatetime, 1
        );
        expectLastUpdatedTimeShowing(false);
    });

    it('does not display if publication within week of now', function() {
        searchResult.publicationDatetime = getDateDaysBeforeNow(6);
        searchResult.lastUpdatedDatetime = getDateDaysAfterDate(
            searchResult.publicationDatetime, 2
        );
        expectLastUpdatedTimeShowing(false);
    });

    it('does display if update within week of now', function() {
        searchResult.lastUpdatedDatetime = getDateDaysBeforeNow(6);
        searchResult.publicationDatetime = getDateDaysBeforeDate(
            searchResult.lastUpdatedDatetime, 2
        );
        expectLastUpdatedTimeShowing(true);
    });

    it('does display if publish <= 180d and updated after 30d', function() {
        searchResult.publicationDatetime = getDateDaysBeforeNow(150);
        searchResult.lastUpdatedDatetime = getDateDaysAfterDate(
            searchResult.publicationDatetime, 30
        );
        expectLastUpdatedTimeShowing(false);

        searchResult.publicationDatetime = getDateDaysBeforeNow(150);
        searchResult.lastUpdatedDatetime = getDateDaysAfterDate(
            searchResult.publicationDatetime, 31
        );
        expectLastUpdatedTimeShowing(true);
    });

    it('does display if publish <= 365d and updated after 90d', function() {
        searchResult.publicationDatetime = getDateDaysBeforeNow(300);
        searchResult.lastUpdatedDatetime = getDateDaysAfterDate(
            searchResult.publicationDatetime, 90
        );
        expectLastUpdatedTimeShowing(false);

        searchResult.publicationDatetime = getDateDaysBeforeNow(300);
        searchResult.lastUpdatedDatetime = getDateDaysAfterDate(
            searchResult.publicationDatetime, 91
        );
        expectLastUpdatedTimeShowing(true);
    });

    it('does display if publish <= 730d and updated after 180d', function() {
        searchResult.publicationDatetime = getDateDaysBeforeNow(700);
        searchResult.lastUpdatedDatetime = getDateDaysAfterDate(
            searchResult.publicationDatetime, 180
        );
        expectLastUpdatedTimeShowing(false);

        searchResult.publicationDatetime = getDateDaysBeforeNow(700);
        searchResult.lastUpdatedDatetime = getDateDaysAfterDate(
            searchResult.publicationDatetime, 181
        );
        expectLastUpdatedTimeShowing(true);
    });

    it('does display if updated after 365d', function() {
        searchResult.publicationDatetime = getDateDaysBeforeNow(731);
        searchResult.lastUpdatedDatetime = getDateDaysAfterDate(
            searchResult.publicationDatetime, 365
        );
        expectLastUpdatedTimeShowing(false);

        searchResult.publicationDatetime = getDateDaysBeforeNow(731);
        searchResult.lastUpdatedDatetime = getDateDaysAfterDate(
            searchResult.publicationDatetime, 366
        );
        expectLastUpdatedTimeShowing(true);

        searchResult.publicationDatetime = getDateDaysBeforeNow(2000);
        searchResult.lastUpdatedDatetime = getDateDaysAfterDate(
            searchResult.publicationDatetime, 366
        );
        expectLastUpdatedTimeShowing(true);
    });
});
