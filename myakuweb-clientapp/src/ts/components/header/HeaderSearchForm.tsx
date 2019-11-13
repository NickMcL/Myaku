/**
 * HeaderSearchForm component module. See [[HeaderSearchForm]].
 */

import Collapsable from 'ts/components/generic/Collapsable';
import History from 'history';
import React from 'react';
import SearchBarInput from 'ts/components/header/SearchBarInput';
import SearchOptionsCollapseToggle from
    'ts/components/header/SearchOptionsCollapseToggle';
import SearchOptionsInput from 'ts/components/header/SearchOptionsInput';
import { blurActiveElement } from 'ts/app/utils';

import {
    AllNullable,
    SearchOptions,
    assertIsSearchOption,
} from 'ts/types/types';
import {
    applyDefaultSearchOptions,
    getSearchOptionsFromLocation,
    getSearchQueryFromLocation,
    getSearchUrl,
    loadUserSearchOptions,
    setUserSearchOption,
} from 'ts/app/search';
import {
    isRomaji,
    toHiragana,
    toKatakana,
} from 'wanakana';

/** Props for the [[HeaderSearchForm]] component. */
interface HeaderSearchFormProps {
    /**
     * Whether a search is currently being loaded by the app or not.
     *
     * If true, a loading icon will be displayed within the header search from,
     * the search query input will be set to readonly, and the form submit
     * button will be disabled.
     */
    loadingSearch: boolean;

    /**
     * Current page location of the app.
     *
     * The URL search parameters will be parsed from this location to set the
     * initial form values.
     */
    location: History.Location;

    /**
     * History object currently being used by the app.
     *
     * When a search is submitted via the form in the component, a URL for the
     * search result page for that search will be pushed to this history.
     */
    history: History.History;
}
type Props = HeaderSearchFormProps;

/** State for the [[HeaderSearchForm]] component. */
interface HeaderSearchFormState {
    /** The currently inputted search query for the search form */
    query: string;

    /** The currently inputted search options for the search form */
    options: SearchOptions;

    /**
     * Set to true if a form submit is made with erroneous values.
     *
     * Set back to false once any change to inputted form values happens after
     * the erroneous submit.
     */
    errorValueSubmitted: boolean;

    /**
     * If true, the search options portion of the search form is currently
     * collapsed. If false, it is uncollapsed.
     */
    optionsCollapsed: boolean;

    /**
     * If true, the collapse/uncollapse animation for the search options
     * portion of the search form is currently happening. If false, the
     * animation is not currently happening.
     */
    optionsCollapseAnimating: boolean;

    /**
     * If true, when the search options portion of the search form has its
     * collapse state toggled, the collapse/uncollapse will be animated.
     *
     * If false, the collapse/uncollapse change will happen instantly with no
     * animation instead.
     */
    optionsCollapseAnimateEnabled: boolean;
}
type State = HeaderSearchFormState;

/** Max allowable length for a search query */
const MAX_QUERY_LENGTH = 100;


/**
 * Log a warning to console that no IndexedDB is available in the current
 * environment, so search options can not be stored across sessions.
 */
function logNoIndexedDbWarning(): void {
    console.warn(
        'Unable to use IndexedDB, so user-specified search options will not '
        + 'be stored across sessions.'
    );
}

/**
 * The site-header search form component for MyakuWeb.
 *
 * Contains a search query input box with clear and submit buttons as well as a
 * collapsable section containing search options inputs.
 *
 * @remarks
 * See [[HeaderSearchFormProps]] and [[HeaderSearchFormState]] for props and
 * state details.
 */
class HeaderSearchForm extends React.Component<Props, State> {
    /**
     * Set of the search options that were not explicitly specified in the
     * initial location URL prop given to the component.
     *
     * These options are tracked in this set so that when the search options
     * stored in the session for the user finish being loaded asynchronously,
     * only the options that were not explicitly specified in the initial
     * location URL have their values overridden by the user session options.
     */
    private _searchOptionsNotInLocation: Set<keyof SearchOptions>;

    /**
     * Callback to unregister the history change listener registered by this
     * component on mount.
     *
     * This callback is saved in an instance variable on component mount so
     * that it can be called later during component unmount.
     */
    private _historyUnlistenCallback: History.UnregisterCallback | null;

    /**
     * Sets the initial search query and search options based on the initially
     * given URL location prop.
     *
     * @param props - See [[HeaderSearchFormProps]].
     */
    constructor(props: Props) {
        super(props);
        this.bindEventHandlers();
        this._searchOptionsNotInLocation = new Set<keyof SearchOptions>();
        this._historyUnlistenCallback = null;

        this.state = {
            query: getSearchQueryFromLocation(props.location) ?? '',
            options: this.getInitSearchOptions(),
            errorValueSubmitted: false,
            optionsCollapsed: true,
            optionsCollapseAnimating: false,
            optionsCollapseAnimateEnabled: false,
        };
    }

    /**
     * Does two tasks on mount:
     *   1. Register the history change listener for the component.
     *   2. Start the async load of the session search options for the user.
     */
    componentDidMount(): void {
        this._historyUnlistenCallback = this.props.history.listen(
            this.handleHistoryChange
        );

        if (this._searchOptionsNotInLocation.size > 0) {
            loadUserSearchOptions().then(
                this.handleLoadedUserSearchOptions,
                logNoIndexedDbWarning
            );
        }
    }

    /**
     * Unregister the history change listener for the component on unmount.
     */
    componentWillUnmount(): void {
        this._historyUnlistenCallback?.();
    }

    /**
     * Bind "this" for the event handlers used by the component.
     */
    bindEventHandlers(): void {
        this.handleHistoryChange = this.handleHistoryChange.bind(this);
        this.handleSubmit = this.handleSubmit.bind(this);
        this.handleInputtedQueryChange = (
            this.handleInputtedQueryChange.bind(this)
        );
        this.handleSearchOptionsChange = (
            this.handleSearchOptionsChange.bind(this)
        );
        this.handleLoadedUserSearchOptions = (
            this.handleLoadedUserSearchOptions.bind(this)
        );
        this.handleSearchOptionsCollapseToggle = (
            this.handleSearchOptionsCollapseToggle.bind(this)
        );
        this.handleSearchOptionsCollapseAnimationEnd = (
            this.handleSearchOptionsCollapseAnimationEnd.bind(this)
        );
    }

    /**
     * Get the initial search option values to set for the form based on the
     * search URL params of the current location.
     *
     * Any options not specified in the location will have default values set
     * for them.
     *
     * @returns The initial search option values that should be set for the
     * form for the component.
     */
    getInitSearchOptions(): SearchOptions {
        const locationOptions = getSearchOptionsFromLocation();
        for (const optionKey of Object.keys(locationOptions)) {
            assertIsSearchOption(optionKey);
            if (locationOptions[optionKey] === null) {
                this._searchOptionsNotInLocation.add(optionKey);
            }
        }

        return applyDefaultSearchOptions(locationOptions);
    }

    /**
     * Apply romaji to kana conversion to the currently inputted search query
     * based on the currently selected kana convert type search option.
     *
     * @remarks
     * Regardless of the currently selected kana convert type options, always
     * applies no conversion if the inputted query already contains any
     * Japanese characters.
     *
     * @returns The currently inputted search query with the currently select
     * kana convert type applied to it.
     */
    getConvertedSearchQuery(): string {
        if (!isRomaji(this.state.query)) {
            return this.state.query;
        }

        if (this.state.options.kanaConvertType === 'hira') {
            return toHiragana(this.state.query);
        } else if (this.state.options.kanaConvertType === 'kata') {
            return toKatakana(this.state.query);
        } else {
            return this.state.query;
        }
    }

    /**
     * History change handler for the component. Does the following:
     *   1. Sets the inputted query to match the query specified in the current
     *   location.
     *   2. Clears any form validation errors.
     *   3. Collapses the search options without animation.
     */
    handleHistoryChange(location: History.Location): void {
        this.setState({
            query: getSearchQueryFromLocation(location) ?? '',
            errorValueSubmitted: false,
            optionsCollapsed: true,
            optionsCollapseAnimating: false,
            optionsCollapseAnimateEnabled: false,
        });
    }

    /**
     * Search form submit handler.
     *
     * Checks if the form values are valid, and if so, pushes a URL for the
     * search result page for the currently inputted search to the history
     * prop.
     *
     * If a form value is invalid, just sets that an error value was submitted
     * in state and takes no other action.
     *
     * In addition, blurs the focused element if the form submit was valid.
     */
    handleSubmit(event: React.FormEvent): void {
        event.preventDefault();
        if (
            this.state.query.length === 0
            || this.state.query.length > MAX_QUERY_LENGTH
        ) {
            this.setState({
                errorValueSubmitted: true,
            });
        } else {
            const convertedQuery = this.getConvertedSearchQuery();
            var searchUrl = getSearchUrl({
                query: convertedQuery,
                pageNum: 1,
            });
            this.setState({
                query: convertedQuery,
            });
            this.props.history.push(searchUrl);
            blurActiveElement();
        }
    }

    /**
     * Handle updating the search query state value when the inputted search
     * query in the form changes.
     *
     * Also, clears any errors due to an invalid form submit.
     *
     * @param newValue - The new inputted search query in the form.
     */
    handleInputtedQueryChange(newValue: string): void {
        this.setState({
            query: newValue,
            errorValueSubmitted: false,
        });
    }

    /**
     * Handle updating the search options state value when an inputted search
     * option in the form changes.
     *
     * Also, stores (asynchronously) the updated search option value in the
     * session search options for the user.
     *
     * @param changedOption - Key of the changed search option value in the
     * form.
     * @param newValue - The new value for that changed option.
     *
     * @typeparam K - Key of the changed search option.
     */
    handleSearchOptionsChange<K extends keyof SearchOptions>(
        changedOption: K, newValue: SearchOptions[K]
    ): void {
        function applyChange(
            this: HeaderSearchForm, prevState: State
        ): Pick<State, 'options'> | null {
            if (newValue === prevState.options[changedOption]) {
                return null;
            }

            setUserSearchOption(changedOption, newValue).catch(
                logNoIndexedDbWarning
            );
            this._searchOptionsNotInLocation.delete(changedOption);
            return {
                options: {
                    ...prevState.options,
                    [changedOption]: newValue,
                },
            };
        }

        this.setState(applyChange.bind(this));
    }

    /**
     * Handle applying loaded session search options to the component state.
     *
     * Will only override a search option value in the state with a value from
     * the loaded session if that value has not be explicitly set in the form
     * yet either via being set in the location search params or being set by
     * user action.
     *
     * @param loadedOptions - The loaded search options from the user session.
     */
    handleLoadedUserSearchOptions(
        loadedOptions: AllNullable<SearchOptions>
    ): void {
        function applyUserSearchOptions(
            this: HeaderSearchForm, prevState: State
        ): Pick<State, 'options'> {
            var updatedOptions = {...prevState.options};
            for (const optionKey of Object.keys(updatedOptions)) {
                assertIsSearchOption(optionKey);

                const loadedOptionValue = loadedOptions[optionKey];
                if (
                    this._searchOptionsNotInLocation.has(optionKey)
                    && loadedOptionValue !== null
                ) {
                    updatedOptions[optionKey] = loadedOptionValue;
                }
            }
            return {
                options: updatedOptions,
            };
        }

        this.setState(applyUserSearchOptions.bind(this));
    }

    /**
     * Handle toggling the collapse state of the search option section.
     *
     * Will only toggle the collapse state if the search option section is not
     * currently in the middle of collapse/uncollapse animation.
     */
    handleSearchOptionsCollapseToggle(): void {
        function updateState(prevState: State): (
            Omit<State, 'query' | 'options' | 'errorValueSubmitted'> | null
        ) {
            if (prevState.optionsCollapseAnimating) {
                return null;
            }

            return {
                optionsCollapsed: !prevState.optionsCollapsed,
                optionsCollapseAnimating: true,
                optionsCollapseAnimateEnabled: true,
            };
        }

        this.setState(updateState);
    }

    /**
     * Update component state to mark that the search option section is not
     * currently in the middle of collapse/uncollapse animation anymore so that
     * a new animation can now be started if toggled.
     */
    handleSearchOptionsCollapseAnimationEnd(): void {
        this.setState({
            optionsCollapseAnimating: false,
        });
    }

    render(): React.ReactElement {
        return (
            <div className='search-container'>
                <form className='search-form' onSubmit={this.handleSubmit}>
                    <SearchBarInput
                        searchQuery={this.state.query}
                        loading={this.props.loadingSearch}
                        maxQueryLength={MAX_QUERY_LENGTH}
                        errorValueSubmitted={this.state.errorValueSubmitted}
                        onChange={this.handleInputtedQueryChange}
                    />
                    <Collapsable
                        collapsed={this.state.optionsCollapsed}
                        animate={this.state.optionsCollapseAnimateEnabled}
                        onAnimationEnd={
                            this.handleSearchOptionsCollapseAnimationEnd
                        }
                    >
                        <SearchOptionsInput
                            searchOptions={this.state.options}
                            onChange={this.handleSearchOptionsChange}
                        />
                    </Collapsable>
                </form>
                <div className='search-options-toggle-container'>
                    <SearchOptionsCollapseToggle
                        collapsed={this.state.optionsCollapsed}
                        onToggle={this.handleSearchOptionsCollapseToggle}
                    />
                </div>
            </div>
        );
    }
}

export default HeaderSearchForm;
