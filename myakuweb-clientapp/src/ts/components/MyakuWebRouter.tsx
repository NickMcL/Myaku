/**
 * Top-level router component for the MyakuWeb app.
 * @module ts/components/MyakuWebRouter
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
