import 'package:flutter/foundation.dart';

class PlatformSourceDetector {
  const PlatformSourceDetector();

  String detect() {
    return detectFrom(platform: defaultTargetPlatform, isWeb: kIsWeb);
  }

  @visibleForTesting
  String detectFrom({required TargetPlatform platform, required bool isWeb}) {
    if (isWeb) {
      return 'app_web';
    }
    switch (platform) {
      case TargetPlatform.android:
      case TargetPlatform.iOS:
        return 'app_mobile';
      case TargetPlatform.linux:
      case TargetPlatform.macOS:
      case TargetPlatform.windows:
      case TargetPlatform.fuchsia:
        return 'app_desktop';
    }
  }
}
