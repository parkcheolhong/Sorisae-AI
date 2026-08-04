const baseConfig = require('./app.json').expo;
const withNotificationColorToolsReplace = require('./plugins/withNotificationColorToolsReplace');

module.exports = ({ config }) => ({
  ...config,
  ...baseConfig,
  plugins: [...(baseConfig.plugins ?? []), withNotificationColorToolsReplace],
});
