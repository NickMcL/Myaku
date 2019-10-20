/** @module Main header search form component  */

import Collapsable from './Collapsable';
import React from 'react';
import SearchBarInput from './SearchBarInput';
import SearchOptionsCollapseToggle from './SearchOptionsCollapseToggle';
import SearchOptionsInput from './SearchOptionsInput';
import { getSessionSearchOptions } from '../apiRequests';

import {
    KanaConvertType,
    SearchOptions,
    SessionSearchOptionsResponse,
    isKanaConvertType,
    isSearchOption,
} from '../types';

interface HeaderSearchFormProps {
    onSearchSubmit: (
        query: string, pageNum: number, searchOptions: SearchOptions,
        queryConvertedCallback: (convertedQuery: string) => void
    ) => void;
}
type Props = HeaderSearchFormProps;

interface HeaderSearchFormState {
    query: string;
    options: SearchOptions;
    optionsCollapsed: boolean;
    optionsCollapseAnimating: boolean;
}
type State = HeaderSearchFormState;

const SEARCH_OPTIONS_DEFAULTS: SearchOptions = {
    kanaConvertType: 'hira',
};

const SEARCH_URL_PARAMS = {
    query: 'q',
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
            query: urlParams.get(SEARCH_URL_PARAMS.query) || '',
            options: this.getInitSearchOptions(urlParams),
            optionsCollapsed: true,
            optionsCollapseAnimating: false,
        };

        if (this.state.query.length > 0) {
            this.props.onSearchSubmit(
                this.state.query,
                getPageNumUrlParam(urlParams) || 1,
                this.state.options,
                this.handleSearchQueryChange
            );
        }

        if (this._defaultSearchOptionUsed.size > 0) {
            getSessionSearchOptions().then(
                this.handleSessionSearchOptionsResponse
            );
        }
    }

    bindEventHandlers(): void {
        this.handleSubmit = this.handleSubmit.bind(this);
        this.handleSearchQueryChange = this.handleSearchQueryChange.bind(this);
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
            kanaConvertType = SEARCH_OPTIONS_DEFAULTS.kanaConvertType;
            this._defaultSearchOptionUsed.add('kanaConvertType');
        }

        return {
            kanaConvertType: kanaConvertType,
        };
    }

    handleSubmit(event: React.FormEvent): void {
        event.preventDefault();
        this.props.onSearchSubmit(
            this.state.query, 1, this.state.options,
            this.handleSearchQueryChange
        );
    }

    handleSearchQueryChange(searchQuery: string): void {
        this.setState({
            query: searchQuery,
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
        if (this.state.optionsCollapseAnimating) {
            return;
        }

        this.setState((prevState: State) => ({
            optionsCollapsed: !prevState.optionsCollapsed,
            optionsCollapseAnimating: true,
        }));
    }

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
                        onChange={this.handleSearchQueryChange}
                    />
                    <Collapsable
                        collapsed={this.state.optionsCollapsed}
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
