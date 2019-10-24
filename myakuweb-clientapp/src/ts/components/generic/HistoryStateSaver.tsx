/**
 * Saves component state in browser history and restores component state from
 * history on browser back/forward.
 * @module ts/components/generic/HistoryStateSaver
 */

import {
    useCallback,
    useEffect,
} from 'react';

interface HistoryStateSaverProps<T> {
    componentKey: string;
    currentState: T;
    onRestoreStateFromHistory(restoreState: T): void;
}
type Props<T> = HistoryStateSaverProps<T>;


function updateHistoryState<T>(
    componentKey: string, currentState: T
): void {
    var savedState = window.history.state;
    if (savedState === null) {
        savedState = {};
    }

    var updatedState = {
        ...savedState,
        [componentKey]: currentState,
    };
    window.history.replaceState(
        updatedState,
        document.title,
        window.location.pathname + window.location.search
    );
}

function getWindowPopStateHandler<T>(
    componentKey: string,
    onRestoreStateFromHistory: (restoreState: T) => void
): (event: PopStateEvent) => void {
    return function(event: PopStateEvent): void {
        if (event.state === null) {
            return;
        }

        var restoreState = event.state[componentKey];
        if (restoreState !== undefined) {
            onRestoreStateFromHistory(restoreState as T);
        }
    };
}

function HistoryStateSaver<T>(props: Props<T>): null {
    const { componentKey, currentState, onRestoreStateFromHistory } = props;
    useEffect((): void => updateHistoryState(componentKey, currentState));

    const windowPopStateHandler = useCallback(
        getWindowPopStateHandler(componentKey, onRestoreStateFromHistory),
        [componentKey, onRestoreStateFromHistory]
    );
    useEffect(
        function() {
            window.addEventListener('popstate', windowPopStateHandler);
            return function(): void {
                window.removeEventListener('popstate', windowPopStateHandler);
            };
        }
    );

    return null;
}

export default HistoryStateSaver;
