const path = require('path');

const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const PreloadWebpackPlugin = require('preload-webpack-plugin');
const { CleanWebpackPlugin } = require('clean-webpack-plugin');

const TerserJSPlugin = require('terser-webpack-plugin');
const OptimizeCSSAssetsPlugin = require('optimize-css-assets-webpack-plugin');

const APP_PATH = path.resolve(__dirname, 'src');

module.exports = {
    mode: process.env.NODE_ENV === 'production' ? 'production' : 'development',

    entry: {
        myakuweb: APP_PATH,
    },

    output: {
        filename: '[name].[contenthash].js',
        path: path.resolve(__dirname, 'dist', 'static'),
        publicPath: '/static/',
    },

    devtool: 'source-map',

    optimization: {
        moduleIds: 'hashed',
        runtimeChunk: 'single',
        minimizer: [
            new TerserJSPlugin(),
            new OptimizeCSSAssetsPlugin(),
        ],
        splitChunks: {
            cacheGroups: {
                vendor: {
                    test: /[\\/]node_modules[\\/]/,
                    name: 'vendors',
                    chunks: 'all',
                },
            },
        },
    },

    resolve: {
        extensions: ['.ts', '.tsx', '.js', '.jsx'],
    },

    module: {
        rules: [
            {
                test: /\.ts(x?)$/i,
                use: [
                    {
                        loader: 'babel-loader',
                        options: {
                            cacheDirectory: true,
                            presets: [
                                '@babel/env',
                                '@babel/react',
                            ],
                        },
                    },
                    'ts-loader',
                ],
                exclude: /node_modules/,
            },
            {
                test: /\.s[ac]ss$/i,
                use: [
                    MiniCssExtractPlugin.loader,
                    'css-loader',
                    'sass-loader',
                ],
            },
            {
                test: /\.svg$/i,
                use: [
                    {
                        loader: 'file-loader',
                        options: {
                            name: '[name].[contenthash].[ext]',
                            outputPath: 'images',
                        },
                    },
                    'image-webpack-loader',
                ],
            },
            {
                test: /\.(woff|woff2)$/i,
                loader: 'file-loader',
                options: {
                    name: '[name].[contenthash].[ext]',
                    outputPath: 'webfonts',
                },
            },
        ],
    },

    plugins: [
        new CleanWebpackPlugin(),
        new MiniCssExtractPlugin({
            filename: '[name].[contenthash].css',
            chunkFilename: '[name].[contenthash].css',
        }),
        new HtmlWebpackPlugin({
            template: path.resolve(APP_PATH, 'index.html'),
            filename: '../index.html',
            minify: false,
        }),
        new PreloadWebpackPlugin({
            rel: 'preload',
            as: 'font',
            include: 'allAssets',
            fileBlacklist: [/^(?!.*\.woff2$)/],
        }),
    ],
};
