/** @module Romaji->kana conversion setting input component */

import React from 'react';

import {
    KANA_CONVERT_TYPE_VALUES,
    KanaConvertType,
} from '../types';

interface KanaConvertTypeInputProps {
    kanaConvertType: KanaConvertType;
    onChange: (kanaConvertType: KanaConvertType) => void;
}
type Props = KanaConvertTypeInputProps;

const CONVERT_TYPE_LABELS: Record<KanaConvertType, string> = {
    'hira': 'Hiragana (a→あ)',
    'kata': 'Katakana (a→ア)',
    'none': 'No conversion (a→a)',
};


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

const KanaConvertTypeInput: React.FC<Props> = function(props) {
    function handleChange(event: React.FormEvent<HTMLInputElement>): void {
        props.onChange(event.currentTarget.value as KanaConvertType);
    }

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
