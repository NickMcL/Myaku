/** @module Main header search form component  */

import Collapsable from 'ts/components/generic/Collapsable';
import HistoryStateSaver from 'ts/components/generic/HistoryStateSaver';
import { PAGE_NAVIGATION_EVENT } from 'ts/app/events';
import React from 'react';
import SearchBarInput from 'ts/components/header/SearchBarInput';
import SearchOptionsCollapseToggle from
    'ts/components/header/SearchOptionsCollapseToggle';
import SearchOptionsInput from 'ts/components/header/SearchOptionsInput';
import { getSessionSearchOptions } from 'ts/app/apiRequests';

import {
    DEFAULT_SEARCH_OPTIONS,
    KanaConvertType,
    Search,
    SearchOptions,
    SessionSearchOptionsResponse,
    isKanaConvertType,
    isSearchOption,
} from 'ts/types/types';

interface HeaderSearchFormProps {
    searchQuery: string;
    loadingSearch: boolean;
    onSearchSubmit: (search: Search) => void;
    onSearchQueryChange: (newValue: string) => void;
}
type Props = HeaderSearchFormProps;

interface HeaderSearchFormState {
    options: SearchOptions;
    optionsCollapsed: boolean;
    optionsCollapseAnimating: boolean;
    optionsCollapseAnimateEnabled: boolean;
}
type State = HeaderSearchFormState;

const SEARCH_URL_PARAMS = {
    pageNum: 'p',
    kanaConvertType: 'conv',
};


function getPageNumUrlParam(urlParams: URLSearchParams): number | null {
    var pageNumParamValue = urlParams.get(SEARCH_URL_PARAMS.pageNum);
    if (pageNumParamValue === null) {
        return null;
    }

    var pageNum = Number(pageNumParamValue);
    if (Number.isInteger(pageNum) && pageNum > 0) {
        return pageNum;
    } else {
        return null;
    }
}

function getKanaConvertTypeUrlParam(
    urlParams: URLSearchParams
): KanaConvertType | null {
    var kanaConvertTypeParamValue = urlParams.get(
        SEARCH_URL_PARAMS.kanaConvertType
    );
    if (isKanaConvertType(kanaConvertTypeParamValue)) {
        return kanaConvertTypeParamValue;
    } else {
        return null;
    }
}

class HeaderSearchForm extends React.Component<Props, State> {
    private _defaultSearchOptionUsed: Set<keyof SearchOptions>;

    constructor(props: Props) {
        super(props);
        this.bindEventHandlers();
        this._defaultSearchOptionUsed = new Set<keyof SearchOptions>();

        var urlParams = new URLSearchParams(window.location.search);
        this.state = {
            options: this.getInitSearchOptions(urlParams),
            optionsCollapsed: true,
            optionsCollapseAnimating: false,
            optionsCollapseAnimateEnabled: false,
        };

        if (this.props.searchQuery.length > 0) {
            this.props.onSearchSubmit({
                query: this.props.searchQuery,
                pageNum: getPageNumUrlParam(urlParams) || 1,
                options: this.state.options,
            });
        }

        if (this._defaultSearchOptionUsed.size > 0) {
            getSessionSearchOptions().then(
                this.handleSessionSearchOptionsResponse
            );
        }
    }

    componentDidMount(): void {
        window.addEventListener(
            PAGE_NAVIGATION_EVENT, this.handlePageNavigation
        );
    }

    componentWillUnmount(): void {
        window.removeEventListener(
            PAGE_NAVIGATION_EVENT, this.handlePageNavigation
        );
    }

    bindEventHandlers(): void {
        this.handleRestoreStateFromHistory = (
            this.handleRestoreStateFromHistory.bind(this)
        );
        this.handlePageNavigation = this.handlePageNavigation.bind(this);
        this.handleSubmit = this.handleSubmit.bind(this);
        this.handleSearchOptionsChange = (
            this.handleSearchOptionsChange.bind(this)
        );
        this.handleSessionSearchOptionsResponse = (
            this.handleSessionSearchOptionsResponse.bind(this)
        );
        this.handleSearchOptionsCollapseToggle = (
            this.handleSearchOptionsCollapseToggle.bind(this)
        );
        this.handleSearchOptionsCollapseAnimationEnd = (
            this.handleSearchOptionsCollapseAnimationEnd.bind(this)
        );
    }

    getInitSearchOptions(urlParams: URLSearchParams): SearchOptions {
        var kanaConvertType = getKanaConvertTypeUrlParam(urlParams);
        if (kanaConvertType === null) {
            kanaConvertType = DEFAULT_SEARCH_OPTIONS.kanaConvertType;
            this._defaultSearchOptionUsed.add('kanaConvertType');
        }

        return {
            kanaConvertType: kanaConvertType,
        };
    }

    revertOptionsCollapsedToDefault(): void {
        this.setState({
            optionsCollapsed: true,
            optionsCollapseAnimating: false,
            optionsCollapseAnimateEnabled: false,
        });
    }

    handleRestoreStateFromHistory(): void {
        this.revertOptionsCollapsedToDefault();
    }

    handlePageNavigation(): void {
        this.revertOptionsCollapsedToDefault();
    }

    handleSubmit(event: React.FormEvent): void {
        event.preventDefault();
        this.props.onSearchSubmit({
            query: this.props.searchQuery,
            pageNum: 1,
            options: this.state.options,
        });
    }

    handleSearchOptionsChange<K extends keyof SearchOptions>(
        changedOption: K, newValue: SearchOptions[K]
    ): void {
        function applyChange(
            this: HeaderSearchForm, prevState: State
        ): {options: SearchOptions} {
            if (newValue === prevState.options[changedOption]) {
                return prevState;
            }

            this._defaultSearchOptionUsed.delete(changedOption);
            return {
                options: {
                    ...prevState.options,
                    [changedOption]: newValue,
                },
            };
        }

        this.setState(applyChange.bind(this));
    }

    handleSessionSearchOptionsResponse(
        response: SessionSearchOptionsResponse
    ): void {
        function applySessionSearchOptions(
            this: HeaderSearchForm, prevState: State
        ): {options: SearchOptions} {
            var updatedOptions = {...prevState.options};
            for (const searchOption of Object.keys(response)) {
                if (!isSearchOption(searchOption)) {
                    continue;
                }

                if (
                    this._defaultSearchOptionUsed.has(searchOption)
                    && response[searchOption] !== null
                ) {
                    updatedOptions[searchOption] = response[searchOption];
                }
            }
            return {
                options: updatedOptions,
            };
        }

        this.setState(applySessionSearchOptions.bind(this));
    }

    handleSearchOptionsCollapseToggle(): void {
        function updateState(prevState: State): Omit<State, 'options'> | null {
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

    handleSearchOptionsCollapseAnimationEnd(): void {
        this.setState({
            optionsCollapseAnimating: false,
        });
    }

    render(): React.ReactElement {
        return (
            <div className='search-container'>
                <HistoryStateSaver
                    componentKey={'HeaderSearchForm'}
                    currentState={null}
                    onRestoreStateFromHistory={
                        this.handleRestoreStateFromHistory
                    }
                />
                <form className='search-form' onSubmit={this.handleSubmit}>
                    <SearchBarInput
                        searchQuery={this.props.searchQuery}
                        onChange={this.props.onSearchQueryChange}
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
