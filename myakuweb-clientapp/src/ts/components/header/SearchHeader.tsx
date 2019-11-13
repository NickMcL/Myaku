/**
 * SearchHeader component module. See [[SearchHeader]].
 */

import Header from 'ts/components/header/Header';
import HeaderNav from 'ts/components/header/HeaderNav';
import HeaderSearchForm from 'ts/components/header/HeaderSearchForm';
import History from 'history';
import React from 'react';

/** Props for the [[SearchHeader]] component. */
interface SearchHeaderProps {
    /**
     * Whether a search is currently being loaded by the app or not.
     *
     * Will be forwarded to the HeaderSearchForm component.
     */
    loadingSearch: boolean;

    /**
     * Current page location of the app.
     *
     * Will be forwarded to the HeaderSearchForm component.
     */
    location: History.Location;

    /**
     * History object currently being used by the app.
     *
     * Will be forwarded to the HeaderSearchForm component.
     */
    history: History.History;
}
type Props = SearchHeaderProps;


/**
 * Header component containing the app nav and header search query form.
 *
 * @remarks
 * All props are simply forwarded to the HeaderSearchForm component.
 *
 * @param props - See [[SearchHeaderProps]]
 */
const SearchHeader: React.FC<Props> = function(props) {
    return (
        <Header>
            <HeaderNav />
            <HeaderSearchForm
                loadingSearch={props.loadingSearch}
                location={props.location}
                history={props.history}
            />
        </Header>
    );
};

export default SearchHeader;
