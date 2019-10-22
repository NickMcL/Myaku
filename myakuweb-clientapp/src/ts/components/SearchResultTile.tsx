/** @module Search result tile component */

import { ArticleSearchResult } from '../types';
import Collapsable from './Collapsable';
import React from 'react';
import SearchResultArticleInfo from './SearchResultArticleInfo';
import SearchResultHeader from './SearchResultHeader';
import SearchResultSampleText from './SearchResultSampleText';
import SearchResultTags from './SearchResultTags';
import Tile from './Tile';
import TileFooterButton from './TileFooterButton';

interface SearchResultTileProps {
    searchQuery: string;
    searchResult: ArticleSearchResult;
}
type Props = SearchResultTileProps;

interface SearchResultTileState {
    moreSampleTextsCollapsed: boolean;
    moreSampleTextsCollapseAnimating: boolean;
}
type State = SearchResultTileState;


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

    hasMoreSampleText(): boolean {
        return this.props.searchResult.moreSampleTexts.length > 0;
    }

    getMoreSampleTextElement(): React.ReactElement | null {
        if (!this.hasMoreSampleText()) {
            return null;
        }

        var moreSampleTexts = this.props.searchResult.moreSampleTexts;
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
                collapsed={this.state.moreSampleTextsCollapsed}
                onAnimationEnd={this.handleMoreSampleTextCollapseAnimationEnd}
            >
                <ul className='more-samples-list'>
                    {moreSampleTextLis}
                </ul>
            </Collapsable>
        );
    }

    getMoreSampleTextCollapseToggleElement(): React.ReactElement | null {
        if (!this.hasMoreSampleText()) {
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
                    {this.props.searchQuery}
                </span>
                {' instances from this article'}
            </TileFooterButton>
        );
    }

    render(): React.ReactElement {
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
                {this.getMoreSampleTextElement()}
                {this.getMoreSampleTextCollapseToggleElement()}
            </Tile>
        );
    }
}

export default SearchResultTile;
