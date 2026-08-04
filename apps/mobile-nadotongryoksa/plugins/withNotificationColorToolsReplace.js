const { createRunOncePlugin, withDangerousMod } = require('@expo/config-plugins');
const fs = require('fs/promises');
const path = require('path');

const MANIFEST_META_DATA_NAME = 'com.google.firebase.messaging.default_notification_color';
const TOOLS_XMLNS = 'http://schemas.android.com/tools';

function patchManifest(contents) {
  let next = contents;
  if (!next.includes('xmlns:tools=')) {
    next = next.replace(
      '<manifest ',
      `<manifest xmlns:tools="${TOOLS_XMLNS}" `,
    );
  }

  const metaDataPattern = new RegExp(
    '(<meta-data\\s+android:name="' + MANIFEST_META_DATA_NAME + '"\\s+android:resource="@color/notification_icon_color"\\s*/>)',
  );
  if (metaDataPattern.test(next) && !next.includes('tools:replace="android:resource"')) {
    next = next.replace(
      metaDataPattern,
      `<meta-data android:name="${MANIFEST_META_DATA_NAME}" android:resource="@color/notification_icon_color" tools:replace="android:resource"/>`,
    );
  }

  return next;
}

function withNotificationColorToolsReplace(config) {
  return withDangerousMod(config, [
    'android',
    async (androidConfig) => {
      const manifestPath = path.join(
        androidConfig.modRequest.platformProjectRoot,
        'app',
        'src',
        'main',
        'AndroidManifest.xml',
      );
      const original = await fs.readFile(manifestPath, 'utf8');
      const patched = patchManifest(original);
      if (patched !== original) {
        await fs.writeFile(manifestPath, patched);
      }
      return androidConfig;
    },
  ]);
}

module.exports = createRunOncePlugin(
  withNotificationColorToolsReplace,
  'with-notification-color-tools-replace',
  '2.0.0',
);
