/**
 * SearchResultTile component module. See [[SearchResultTile]].
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

/** Props for the [[SearchResultTile]] component. */
interface SearchResultTileProps {
    /**
     * Search query that was made to get the search result for the component.
     *
     * If null, a loading tile will be rendered by the component instead of a
     * tile containing search result data.
     */
    searchQuery: string | null;

    /**
     * Article search result data that should be displayed by the component.
     *
     * If null, a loading tile will be rendered by the component instead of a
     * tile containing search result data.
     */
    searchResult: ArticleSearchResult | null;
}
type Props = SearchResultTileProps;

/** State for the [[SearchResultTile]] component. */
interface SearchResultTileState {
    /**
     * If true, the more sample texts portion of the tile is currently
     * collapsed. If false, it is uncollapsed.
     */
    moreSampleTextsCollapsed: boolean;

    /**
     * If true, the collapse/uncollapse animation for the more sample texts
     * portion of the tile is currently happening. If false, the animation is
     * not currently happening.
     */
    moreSampleTextsCollapseAnimating: boolean;
}
type State = SearchResultTileState;

/** The height of the loading tiles rendered by the component. */
const LOADING_HEIGHT = '13rem';


/**
 * Tile component for displaying an article search result.
 *
 * Displays a header containing a link to the search result article, a list of
 * article info, a list of article tags, and the sample text for the search
 * result.
 *
 * Also includes a collapsable section for the extra (more) sample texts for
 * the search result outside of the main sample text.
 *
 * @remarks
 * See [[SearchResultTileProps]] and [[SearchResultTileState]] for props and
 * state details.
 */
class SearchResultTile extends React.Component<Props, State> {
    /**
     * Sets the more sample texts section to be collapsed initially.
     *
     * @param props - See [[HeaderSearchFormProps]].
     */
    constructor(props: Props) {
        super(props);
        this.bindEventHandlers();
        this.state = {
            moreSampleTextsCollapsed: true,
            moreSampleTextsCollapseAnimating: false,
        };
    }

    /**
     * Bind "this" for the event handlers used by the component.
     */
    bindEventHandlers(): void {
        this.handleMoreSampleTextCollapseToggle = (
            this.handleMoreSampleTextCollapseToggle.bind(this)
        );
        this.handleMoreSampleTextCollapseAnimationEnd = (
            this.handleMoreSampleTextCollapseAnimationEnd.bind(this)
        );
    }

    /**
     * Handle toggling the collapse state of the more sample text section.
     *
     * Will only toggle the collapse state if the more sample text section is
     * not currently in the middle of collapse/uncollapse animation.
     */
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

    /**
     * Update component state to mark that the more sample text section is not
     * currently in the middle of collapse/uncollapse animation anymore so that
     * a new animation can now be started if toggled.
     */
    handleMoreSampleTextCollapseAnimationEnd(): void {
        this.setState({
            moreSampleTextsCollapseAnimating: false,
        });
    }

    /**
     * Returns true if the given search result has more sample texts than just
     * the main sample text. Otherwise, returns false.
     */
    hasMoreSampleText(searchResult: ArticleSearchResult | null): boolean {
        return (
            searchResult !== null && searchResult.moreSampleTexts.length > 0
        );
    }

    /**
     * Get the collapsable more sample texts element for the given search
     * result.
     *
     * @param searchResult - Article search result to get the collapsable more
     * sapmle texts element for.
     *
     * @returns If searchResult is non-null and has more sample texts outside
     * of the main sample text, the collapsable more sample texts element.
     * Otherwise, null.
     */
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
                animate={true}
                collapsed={this.state.moreSampleTextsCollapsed}
                onAnimationEnd={this.handleMoreSampleTextCollapseAnimationEnd}
            >
                <ul className='more-samples-list'>
                    {moreSampleTextLis}
                </ul>
            </Collapsable>
        );
    }

    /**
     * Get the toggle footer button for the more sample texts collapsable
     * element for the given search result.
     *
     * @param searchQuery - Search query that was made to get the given search
     * result. Will be displayed in the toggle button text.
     * @param searchResult - Article search result to get the toggle footer
     * button element for.
     *
     * @returns If searchResult is non-null and has more sample texts outside
     * of the main sample text, the toggle footer button element.
     * Otherwise, null.
     */
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
                <span lang='ja'>
                    {searchQuery}
                </span>
                {' instances from this article'}
            </TileFooterButton>
        );
    }

    /**
     * Get the loading tile element for the component.
     */
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
