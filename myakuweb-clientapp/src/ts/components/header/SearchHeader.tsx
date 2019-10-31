/**
 * Header component containing the site nav and a search query form.
 * @module ts/components/header/SearchHeader
 */

import Header from 'ts/components/header/Header';
import HeaderNav from 'ts/components/header/HeaderNav';
import HeaderSearchForm from 'ts/components/header/HeaderSearchForm';
import History from 'history';
import React from 'react';

interface SearchHeaderProps {
    loadingSearch: boolean;
    location: History.Location;
    history: History.History;
}
type Props = SearchHeaderProps;


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
