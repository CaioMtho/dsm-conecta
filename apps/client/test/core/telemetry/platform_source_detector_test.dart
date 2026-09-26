import 'package:client/core/telemetry/platform_source_detector.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('PlatformSourceDetector', () {
    test('detects mobile platforms', () {
      const detector = PlatformSourceDetector();
      expect(detector.detectFrom(platform: TargetPlatform.android, isWeb: false), 'app_mobile');
      expect(detector.detectFrom(platform: TargetPlatform.iOS, isWeb: false), 'app_mobile');
    });

    test('detects web platform regardless of underlying platform', () {
      const detector = PlatformSourceDetector();
      expect(detector.detectFrom(platform: TargetPlatform.linux, isWeb: true), 'app_web');
      expect(detector.detectFrom(platform: TargetPlatform.android, isWeb: true), 'app_web');
    });

    test('detects desktop platforms', () {
      const detector = PlatformSourceDetector();
      expect(detector.detectFrom(platform: TargetPlatform.linux, isWeb: false), 'app_desktop');
      expect(detector.detectFrom(platform: TargetPlatform.windows, isWeb: false), 'app_desktop');
      expect(detector.detectFrom(platform: TargetPlatform.macOS, isWeb: false), 'app_desktop');
    });
  });
}
