/**
 * Search result tile component.
 * @module ts/components/search-results/SearchResultTile
 */

import { ArticleSearchResult } from 'ts/types/types';
import Collapsable from 'ts/components/generic/Collapsable';
import React from 'react';
import SearchResultArticleInfo from
    'ts/components/search-results/SearchResultArticleInfo';
import SearchResultHeader from
    'ts/components/search-results/SearchResultHeader';
import SearchResultSampleText from
    'ts/components/search-results/SearchResultSampleText';
import SearchResultTags from 'ts/components/search-results/SearchResultTags';
import Tile from 'ts/components/generic/Tile';
import TileFooterButton from 'ts/components/generic/TileFooterButton';

interface SearchResultTileProps {
    searchQuery: string | null;
    searchResult: ArticleSearchResult | null;
}
type Props = SearchResultTileProps;

interface SearchResultTileState {
    moreSampleTextsCollapsed: boolean;
    moreSampleTextsCollapseAnimating: boolean;
}
type State = SearchResultTileState;

const LOADING_HEIGHT = '13rem';


class SearchResultTile extends React.Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.bindEventHandlers();
        this.state = {
            moreSampleTextsCollapsed: true,
            moreSampleTextsCollapseAnimating: false,
        };
    }

    bindEventHandlers(): void {
        this.handleMoreSampleTextCollapseToggle = (
            this.handleMoreSampleTextCollapseToggle.bind(this)
        );
        this.handleMoreSampleTextCollapseAnimationEnd = (
            this.handleMoreSampleTextCollapseAnimationEnd.bind(this)
        );
    }

    handleMoreSampleTextCollapseToggle(): void {
        function updateState(prevState: State): State | null {
            if (prevState.moreSampleTextsCollapseAnimating) {
                return null;
            }

            return {
                moreSampleTextsCollapsed: !prevState.moreSampleTextsCollapsed,
                moreSampleTextsCollapseAnimating: true,
            };
        }

        this.setState(updateState);
    }

    handleMoreSampleTextCollapseAnimationEnd(): void {
        this.setState({
            moreSampleTextsCollapseAnimating: false,
        });
    }

    hasMoreSampleText(searchResult: ArticleSearchResult | null): boolean {
        return (
            searchResult !== null && searchResult.moreSampleTexts.length > 0
        );
    }

    getMoreSampleTextElement(
        searchResult: ArticleSearchResult | null
    ): React.ReactElement | null {
        if (!this.hasMoreSampleText(searchResult) || searchResult === null) {
            return null;
        }

        var moreSampleTexts = searchResult.moreSampleTexts;
        var moreSampleTextLis: React.ReactElement[] = [];
        for (let i = 0; i < moreSampleTexts.length; ++i) {
            moreSampleTextLis.push(
                <li key={`more-sample-${i}`}>
                    <SearchResultSampleText sampleText={moreSampleTexts[i]} />
                </li>
            );
        }
        return (
            <Collapsable
                animate
                collapsed={this.state.moreSampleTextsCollapsed}
                onAnimationEnd={this.handleMoreSampleTextCollapseAnimationEnd}
            >
                <ul className='more-samples-list'>
                    {moreSampleTextLis}
                </ul>
            </Collapsable>
        );
    }

    getMoreSampleTextCollapseToggleElement(
        searchQuery: string | null, searchResult: ArticleSearchResult | null
    ): React.ReactElement | null {
        if (!this.hasMoreSampleText(searchResult) || searchQuery === null) {
            return null;
        }

        var buttonStartText = 'Show less ';
        if (this.state.moreSampleTextsCollapsed) {
            buttonStartText = 'Show more ';
        }
        return (
            <TileFooterButton
                onClick={this.handleMoreSampleTextCollapseToggle}
            >
                {buttonStartText}
                <span className='japanese-text' lang='ja'>
                    {searchQuery}
                </span>
                {' instances from this article'}
            </TileFooterButton>
        );
    }

    getLoadingTile(): React.ReactElement {
        return (
            <Tile
                tileClasses='result-tile'
                loadingHeight={LOADING_HEIGHT}
            />
        );
    }

    render(): React.ReactElement {
        if (
            this.props.searchQuery === null
            || this.props.searchResult === null
        ) {
            return this.getLoadingTile();
        }

        return (
            <Tile tileClasses='result-tile'>
                <SearchResultHeader
                    searchResult={this.props.searchResult}
                />
                <SearchResultArticleInfo
                    searchResult={this.props.searchResult}
                />
                <SearchResultTags
                    searchResult={this.props.searchResult}
                />
                <hr />

                <SearchResultSampleText
                    sampleText={this.props.searchResult.mainSampleText}
                />
                {this.getMoreSampleTextElement(this.props.searchResult)}
                {this.getMoreSampleTextCollapseToggleElement(
                    this.props.searchQuery, this.props.searchResult
                )}
            </Tile>
        );
    }
}

export default SearchResultTile;
