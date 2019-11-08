/**
 * Tests for the SearchResultTile component.
 * @module tests/components/search-results/SearchResultTile.test
 */

import Collapsable from 'ts/components/generic/Collapsable';
import React from 'react';
import SearchResultArticleInfo from
    'ts/components/search-results/SearchResultArticleInfo';
import SearchResultHeader from
    'ts/components/search-results/SearchResultHeader';
import SearchResultSampleText from
    'ts/components/search-results/SearchResultSampleText';
import SearchResultTags from 'ts/components/search-results/SearchResultTags';
import SearchResultTile from 'ts/components/search-results/SearchResultTile';
import Tile from 'ts/components/generic/Tile';
import TileFooterButton from 'ts/components/generic/TileFooterButton';
import { act } from 'react-dom/test-utils';
import { expectComponent } from 'tests/testUtils';
import { getSearchResultPageDataClone } from 'tests/testData';

import {
    ShallowWrapper,
    shallow,
} from 'enzyme';

const testResultPage = getSearchResultPageDataClone();
var searchQuery = testResultPage.search.query;
var searchResultWithMoreSampleText = testResultPage.results[0];
var searchResultWithoutMoreSampleText = testResultPage.results[1];
beforeEach(function() {
    const testResultPage = getSearchResultPageDataClone();
    searchQuery = testResultPage.search.query;
    searchResultWithMoreSampleText = testResultPage.results[0];
    searchResultWithoutMoreSampleText = testResultPage.results[1];
});

function getTile(wrapper: ShallowWrapper): ShallowWrapper {
    const tile = wrapper.find(Tile);
    expect(tile).toHaveLength(1);
    return tile;
}

function expectMoreSampleTextCollapsed(
    wrapper: ShallowWrapper, collapsed: boolean,
    animate: boolean = expect.any(Boolean)
): void {
    expectComponent(getTile(wrapper), Collapsable, {
        collapsed: collapsed,
        animate: animate,
        onAnimationEnd: expect.any(Function),
        children: expect.anything(),
    });
}

function toggleMoreSampleTextCollapse(wrapper: ShallowWrapper): void {
    const collapseToggle = getTile(wrapper).find(TileFooterButton);
    expect(collapseToggle).toHaveLength(1);
    act(() => collapseToggle.props().onClick());
}

function mockCollapseOnAnimationEndEvent(wrapper: ShallowWrapper): void {
    const collapsable = getTile(wrapper).find(Collapsable);
    expect(collapsable).toHaveLength(1);

    const onAnimationEnd = collapsable.props().onAnimationEnd;
    if (onAnimationEnd === undefined) {
        throw new Error(
            'Search options collapsable has no onAnimationEnd callback set'
        );
    }
    act(() => onAnimationEnd());
}

function expectCollapseToggleButtonText(
    wrapper: ShallowWrapper, collapsed: boolean
): void {
    var startText = '';
    if (collapsed) {
        startText = 'Show more ';
    } else {
        startText = 'Show less ';
    }

    const children = getTile(wrapper).find(TileFooterButton).children();
    expect(children).toHaveLength(3);
    expect(children.at(0).text()).toBe(startText);
    expect(children.at(1).name()).toBe('span');
    expect(children.at(1).props().lang).toBe('ja');
    expect(children.at(1).text()).toBe(searchQuery);
    expect(children.at(2).text()).toBe(' instances from this article');
}


describe('<SearchResultTile /> render', function() {
    var moreSampleTextTile = shallow(<div />);
    var noMoreSampleTextTile = shallow(<div />);
    beforeEach(function() {
        const wrapperWithMoreSampleText = shallow(
            <SearchResultTile
                searchQuery={searchQuery}
                searchResult={searchResultWithMoreSampleText}
            />
        );
        moreSampleTextTile = wrapperWithMoreSampleText.find(Tile);

        const wrapperWithoutMoreSampleText = shallow(
            <SearchResultTile
                searchQuery={searchQuery}
                searchResult={searchResultWithoutMoreSampleText}
            />
        );
        noMoreSampleTextTile = wrapperWithoutMoreSampleText.find(Tile);
    });

    it('renders loading tile if null search result', function() {
        const wrapper = shallow(
            <SearchResultTile
                searchQuery={null}
                searchResult={null}
            />
        );
        expect(wrapper).toMatchSnapshot();
    });

    it('renders header if non-null search result', function() {
        expectComponent(moreSampleTextTile, SearchResultHeader, {
            searchResult: searchResultWithMoreSampleText,
        });
        expectComponent(noMoreSampleTextTile, SearchResultHeader, {
            searchResult: searchResultWithoutMoreSampleText,
        });
    });

    it('renders article info if non-null search result', function() {
        expectComponent(moreSampleTextTile, SearchResultArticleInfo, {
            searchResult: searchResultWithMoreSampleText,
        });
        expectComponent(noMoreSampleTextTile, SearchResultArticleInfo, {
            searchResult: searchResultWithoutMoreSampleText,
        });
    });

    it('renders tags if non-null search result', function() {
        expectComponent(moreSampleTextTile, SearchResultTags, {
            searchResult: searchResultWithMoreSampleText,
        });
        expectComponent(noMoreSampleTextTile, SearchResultTags, {
            searchResult: searchResultWithoutMoreSampleText,
        });
    });

    it('renders main sample text if non-null search result', function() {
        var mainSampleText = moreSampleTextTile.find(
            SearchResultSampleText
        ).first();
        expect(mainSampleText).toHaveLength(1);
        expect(mainSampleText.props()).toStrictEqual({
            sampleText: searchResultWithMoreSampleText.mainSampleText,
        });

        mainSampleText = noMoreSampleTextTile.find(
            SearchResultSampleText
        ).first();
        expect(mainSampleText).toHaveLength(1);
        expect(mainSampleText.props()).toStrictEqual({
            sampleText: searchResultWithoutMoreSampleText.mainSampleText,
        });
    });

    it('renders all more sample text if given', function() {
        const searchResult = searchResultWithMoreSampleText;
        const sampleTexts = moreSampleTextTile.find(SearchResultSampleText);

        // Add 1 to account for the main sample text on the tile.
        expect(sampleTexts).toHaveLength(
            searchResult.moreSampleTexts.length + 1
        );

        // Start i from 1 to skip the main sample text on the tile.
        for (let i = 1; i < sampleTexts.length; ++i) {
            expect(sampleTexts.at(i).props()).toStrictEqual({
                sampleText: searchResult.moreSampleTexts[i - 1],
            });
        }
    });

    it(
        'does not render collapsable if only main sample text given',
        function() {
            const collapsable = noMoreSampleTextTile.find(Collapsable);
            expect(collapsable).toHaveLength(0);
        }
    );

    it('renders toggle if more sample text given', function() {
        expectComponent(moreSampleTextTile, TileFooterButton, {
            onClick: expect.any(Function),
            children: expect.anything(),
        });
    });

    it('does not render toggle if more sample text not given', function() {
        const tileFooterButton = noMoreSampleTextTile.find(TileFooterButton);
        expect(tileFooterButton).toHaveLength(0);
    });
});

describe('<SearchResultTile /> more sample text collapsable', function() {
    var wrapper = shallow(<div />);
    beforeEach(function() {
        wrapper = shallow(
            <SearchResultTile
                searchQuery={searchQuery}
                searchResult={searchResultWithMoreSampleText}
            />
        );
    });

    it('collapses more sample text by default on mount', function() {
        expectMoreSampleTextCollapsed(wrapper, true);
    });

    it('handles more sample text collapse toggle', function() {
        expectMoreSampleTextCollapsed(wrapper, true);

        toggleMoreSampleTextCollapse(wrapper);
        expectMoreSampleTextCollapsed(wrapper, false, true);

        mockCollapseOnAnimationEndEvent(wrapper);
        toggleMoreSampleTextCollapse(wrapper);
        expectMoreSampleTextCollapsed(wrapper, true, true);

        mockCollapseOnAnimationEndEvent(wrapper);
        toggleMoreSampleTextCollapse(wrapper);
        expectMoreSampleTextCollapsed(wrapper, false, true);
    });

    it('ignores more sample text collapse toggle if animating', function() {
        expectMoreSampleTextCollapsed(wrapper, true);

        toggleMoreSampleTextCollapse(wrapper);
        expectMoreSampleTextCollapsed(wrapper, false, true);

        toggleMoreSampleTextCollapse(wrapper);
        expectMoreSampleTextCollapsed(wrapper, false, true);

        mockCollapseOnAnimationEndEvent(wrapper);
        toggleMoreSampleTextCollapse(wrapper);
        expectMoreSampleTextCollapsed(wrapper, true, true);

        toggleMoreSampleTextCollapse(wrapper);
        expectMoreSampleTextCollapsed(wrapper, true, true);
    });

    it('sets footer button text to match collapsed state', function() {
        expectCollapseToggleButtonText(wrapper, true);

        toggleMoreSampleTextCollapse(wrapper);
        expectCollapseToggleButtonText(wrapper, false);

        mockCollapseOnAnimationEndEvent(wrapper);
        toggleMoreSampleTextCollapse(wrapper);
        expectCollapseToggleButtonText(wrapper, true);

        mockCollapseOnAnimationEndEvent(wrapper);
        toggleMoreSampleTextCollapse(wrapper);
        expectCollapseToggleButtonText(wrapper, false);
    });
});
