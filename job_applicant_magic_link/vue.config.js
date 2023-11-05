const path = require('path');

module.exports = {
  filenameHashing: false,
  chainWebpack: config => {
    config.resolve.alias.set('@', path.resolve(__dirname, 'src'));
  }
};