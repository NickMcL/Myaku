/** @module Search bar input component  */

import { MEDIUM_VIEWPORT_MIN_WIDTH } from '../viewport';
import React from 'react';

interface SearchBarInputProps {
    searchQuery: string;
    onChange: (searchQuery: string) => void;
}
type Props = SearchBarInputProps;

interface SearchBarInputState {
    placeholder: string;
}
type State = SearchBarInputState;

// Search box placeholder text adjusts based on viewport size
const FULL_SEARCH_PLACEHOLDER = 'Japanese word, set phrase, idiom, etc.';
const SHORT_SEARCH_PLACEHOLDER = 'Japanese word, phrase, etc.';

class SearchBarInput extends React.Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.bindEventHandlers();
        this.state = {
            placeholder: this.getViewportPlaceholder(),
        };
    }

    componentDidMount(): void {
        window.addEventListener('resize', this.updatePlaceholder);
    }

    componentWillUnmount(): void {
        window.removeEventListener('resize', this.updatePlaceholder);
    }

    bindEventHandlers(): void {
        this.updatePlaceholder = this.updatePlaceholder.bind(this);
        this.handleInputClear = this.handleInputClear.bind(this);
        this.handleInputChange = this.handleInputChange.bind(this);
    }

    getViewportPlaceholder(): string {
        if (window.innerWidth >= MEDIUM_VIEWPORT_MIN_WIDTH) {
            return FULL_SEARCH_PLACEHOLDER;
        } else {
            return SHORT_SEARCH_PLACEHOLDER;
        }
    }

    updatePlaceholder(): void {
        this.setState({
            placeholder: this.getViewportPlaceholder(),
        });
    }

    handleInputClear(): void {
        this.props.onChange('');
    }

    handleInputChange(event: React.FormEvent<HTMLInputElement>): void {
        this.props.onChange(event.currentTarget.value);
    }

    render(): React.ReactElement {
        return (
            <div className='search-bar'>
                <input
                    className='search-input'
                    id='search-input'
                    type='text'
                    name='q'
                    aria-label='Search input'
                    value={this.props.searchQuery}
                    placeholder={this.state.placeholder}
                    onChange={this.handleInputChange}
                />
                <button
                    className='search-clear'
                    type='button'
                    aria-label='Search clear'
                    onClick={this.handleInputClear}
                >
                    <i className='fa fa-times'></i>
                </button>
                <button
                    className='search-submit'
                    type='submit'
                    aria-label='Search submit button'
                >
                    <i className='fa fa-search'></i>
                </button>
            </div>
        );
    }
}

export default SearchBarInput;
