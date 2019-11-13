/**
 * MyakuWebRouter component module. See [[MyakuWebRouter]].
 */

import MainContent from 'ts/components/generic/MainContent';
import React from 'react';
import SearchHeader from 'ts/components/header/SearchHeader';
import SearchResults from 'ts/components/search-results/SearchResults';
import StartContent from 'ts/components/start/StartContent';
import { scrollToTop } from 'ts/app/utils';

import {
    Route,
    Switch,
    useHistory,
} from 'react-router-dom';
import {
    useEffect,
    useState,
} from 'react';


/**
 * Get a Route element for the search header component used on all pages.
 *
 * @param loadingSearchQuery - If true, the search header will be set to show a
 * search loading indicator. If false, it will be set to not show a loading
 * indiciator.
 *
 * @returns A Route element that matches all pages and renders a SearchHeader
 * element.
 */
function getHeaderRoute(loadingSearchQuery: boolean): React.ReactElement {
    return (
        <Route
            path='/'
            render={(routeProps): React.ReactElement => (
                <SearchHeader
                    loadingSearch={loadingSearchQuery}
                    location={routeProps.location}
                    history={routeProps.history}
                />
            )}
        />
    );
}

/**
 * Get a Route element for a search results component.
 *
 * @param setLoadingSearchQuery - A callback function for indicating when a new
 * search query starts and stops loading.
 *
 * @returns A Route element that matches /search pages and renders a
 * SearchResults element.
 */
function getSearchResultsRoute(
    setLoadingSearchQuery: (loading: boolean) => void
): React.ReactElement {
    return (
        <Route
            path='/search'
            render={(routeProps): React.ReactElement => (
                <SearchResults
                    onLoadingNewSearchQueryChange={
                        setLoadingSearchQuery
                    }
                    location={routeProps.location}
                    history={routeProps.history}
                />
            )}
        />
    );
}

/**
 * Top-level router component for all pages of the MyakuWeb app.
 *
 * @remarks
 * Sets an effect to scroll to the top of the page on every page change.
 */
const MyakuWebRouter: React.FC<{}> = function() {
    const [loadingSearchQuery, setLoadingSearchQuery] = useState(false);
    const history = useHistory();

    useEffect(function(): () => void {
        window.history.scrollRestoration = 'manual';
        const unlistenCallback = history.listen(scrollToTop);
        return (): void => unlistenCallback();
    }, [history]);

    return (
        <React.Fragment>
            {getHeaderRoute(loadingSearchQuery)}
            <MainContent>
                <Switch>
                    {getSearchResultsRoute(setLoadingSearchQuery)}
                    <Route path='/'>
                        <StartContent />
                    </Route>
                </Switch>
            </MainContent>
        </React.Fragment>
    );
};

export default MyakuWebRouter;
