/**
 * Entrypoint for the MyakuWeb React app.
 * @module index
 */

import 'scss/myakuweb.scss';

import MyakuWeb from 'ts/components/MyakuWeb';
import React from 'react';
import ReactDOM from 'react-dom';


ReactDOM.render(<MyakuWeb />, document.getElementById('root'));
