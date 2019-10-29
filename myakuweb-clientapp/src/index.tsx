/**
 * Entrypoint for the MyakuWeb React app.
 * @module index
 */

import 'scss/myakuweb.scss';

import { BrowserRouter } from 'react-router-dom';
import MyakuWebRouter from 'ts/components/MyakuWebRouter';
import React from 'react';
import ReactDOM from 'react-dom';


ReactDOM.render(
    <BrowserRouter>
        <MyakuWebRouter />
    </BrowserRouter>,
    document.getElementById('root')
);
