/**
 * KanaConvertTypeInput component module. See [[KanaConvertTypeInput]].
 */

import React from 'react';
import useInputChangeHandler from 'ts/hooks/useInputChangeHandler';

import {
    KANA_CONVERT_TYPE_VALUES,
    KanaConvertType,
} from 'ts/types/types';

/** Props for the [[KanaConvertTypeInput]] component. */
interface KanaConvertTypeInputProps {
    /**
     * Current inputted kana convert type for the form containing this
     * component.
     * This will be the option displayed as set in the component.
     */
    kanaConvertType: KanaConvertType;

    /**
     * Callback to call with the new kana convert type value whenever it
     * changes.
     */
    onChange: (kanaConvertType: KanaConvertType) => void;
}
type Props = KanaConvertTypeInputProps;

/** Labels to use for each of the possible kana convert type values. */
const CONVERT_TYPE_LABELS: Record<KanaConvertType, string> = {
    'hira': 'Hiragana (a→あ)',
    'kata': 'Katakana (a→ア)',
    'none': 'No conversion (a→a)',
};


/**
 * Create the kana convert type radio input elements to use for the component.
 *
 * @param selected - The kana convert type value that should have its radio
 * input checked.
 * @param handleChangeFunc - The callback to set as the onChange handler for
 * each of the kana convert type radio inputs.
 *
 * @returns The radio input elements.
 */
function createRadioInputs(
    selected: KanaConvertType,
    handleChangeFunc: (event: React.FormEvent<HTMLInputElement>) => void
): React.ReactElement[] {
    var radioInputs: React.ReactElement[] = [];
    for (const convertType of KANA_CONVERT_TYPE_VALUES) {
        const inputId = `kana-conv-${convertType}-radio`;
        radioInputs.push(
            <div key={inputId} className='search-options-check'>
                <input
                    className='search-options-check-input'
                    id={inputId}
                    type='radio'
                    name='kana-convert-type'
                    value={convertType}
                    checked={convertType === selected}
                    onChange={handleChangeFunc}
                />
                <label
                    className='check-input-label'
                    htmlFor={inputId}
                >
                    {CONVERT_TYPE_LABELS[convertType]}
                </label>
            </div>
        );
    }

    return radioInputs;
}

/**
 * Romaji-to-kana conversion search option radio input component.
 *
 * @param props - See [[KanaConvertTypeInputProps]].
 */
const KanaConvertTypeInput: React.FC<Props> = function(props) {
    const handleChange = useInputChangeHandler(props.onChange);

    return (
        <fieldset className='kana-conv-field'>
            <legend className='search-options-legend'>
                Romaji Conversion
            </legend>
            {createRadioInputs(props.kanaConvertType, handleChange)}
        </fieldset>
    );
};

export default KanaConvertTypeInput;
