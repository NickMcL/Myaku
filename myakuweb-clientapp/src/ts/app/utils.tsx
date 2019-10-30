/**
 * Utility functions for the MyakuWeb project.
 * @module utils
 */

import {
    PrimativeType,
    isIndexable,
    isPrimativeType,
} from 'ts/types/types';

interface MonthMap {
    [key: number]: string;
}

const MONTH_SHORT_NAME_MAP: MonthMap = {
    0: 'Jan',
    1: 'Feb',
    2: 'Mar',
    3: 'Apr',
    4: 'May',
    5: 'Jun',
    6: 'Jul',
    7: 'Aug',
    8: 'Sep',
    9: 'Oct',
    10: 'Nov',
    11: 'Dec',
};

/**
 * Recursively transform all primative values of obj using transformFunc.
 *
 * Performs the transformation in-place in the given object.
 *
 * @param obj - Object to transform all values of.
 * @param transformFunc - Function to use to transform the primative values of
 * obj.
 * @param condFunc? - If given, only the key-value pairs of obj that return
 * true when given to this function will have their values transformed.
 */
export function recursivelyTransform(
    obj: unknown,
    transformFunc: (value: PrimativeType) => unknown,
    condFunc?: (key: string, value: PrimativeType) => boolean
): void {
    if (!isIndexable(obj)) {
        return;
    }

    for (const [key, value] of Object.entries(obj)) {
        if (isIndexable(value) && typeof value !== 'function') {
            recursivelyTransform(value, transformFunc, condFunc);
        } else if (
            isPrimativeType(value) && (!condFunc || condFunc(key, value))
        ) {
            obj[key] = transformFunc(value);
        }
    }
}

export function scrollToTop(): void {
    window.scrollTo(0, 0);
}

/**
 * Forces a redraw of the element by the browser.
 *
 * @param element - Element to force a redraw for.
 *
 * @returns The offsetHeight of the element, but this can be ignored. It's only
 * returned to prevent the access of offsetHeight property from being removed
 * by the compiler.
 */
export function reflow(element: HTMLElement): number {
    return element.offsetHeight;
}

/**
 * Get the number of full days between two Dates.
 */
export function getDaysBetween(d1: Date, d2: Date): number {
    var d1DayOnly = new Date(d1.getFullYear(), d1.getMonth(), d1.getDate());
    var d2DayOnly = new Date(d2.getFullYear(), d2.getMonth(), d2.getDate());

    var milliSecsBetween = Math.abs(d1DayOnly.getTime() - d2DayOnly.getTime());
    return milliSecsBetween / (1000 * 60 * 60 * 24);
}

/**
 * Get the ordinal suffix for a number (e.g. 1 -> st, 2 -> nd, ...).
 *
 * @param num - Number to get the ordinal suffix for.
 *
 * @returns The ordinal suffix for the number.
 */
function getOrdinalSuffix(num: number): string {
    var mod100 = num % 100;
    if (mod100 > 10 && mod100 < 20) {
        return 'th';
    }

    var mod10 = num % 10;
    if (mod10 === 1) {
        return 'st';
    } else if (mod10 === 2) {
        return 'nd';
    } else if (mod10 === 3) {
        return 'rd';
    } else {
        return 'th';
    }
}

/**
 * Convert the Date to a string with a nice human-readable date.
 *
 * @param date - Date to convert.
 *
 * @returns If the datetime is within a week of now, a string stating how many
 * days ago the datetime was (i.e. today, yesterday, 2 days ago, ...). If the
 * datetime is not within a week, a formatted date string in the form
 * "Jan 1st, 2019".
 */
export function humanizeDate(date: Date): string {
    var daysBetweenNow = getDaysBetween(new Date(), date);
    if (daysBetweenNow === 0) {
        return 'Today';
    } else if (daysBetweenNow === 1) {
        return 'Yesterday';
    } else if (daysBetweenNow <= 7) {
        return `${daysBetweenNow} days ago`;
    } else {
        var day = `${date.getDate()}${getOrdinalSuffix(date.getDate())}`;
        var month = MONTH_SHORT_NAME_MAP[date.getMonth()];
        var year = date.getFullYear();
        return `${month} ${day}, ${year}`;
    }
}
