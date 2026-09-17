import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/config/app_config.dart';

void main() {
  group('AppConfig Media URL Resolution Tests', () {
    test('backendBaseUrl derives root origin without /api prefix', () {
      expect(AppConfig.backendBaseUrl, isNotEmpty);
      expect(AppConfig.backendBaseUrl.endsWith('/api'), isFalse);
      expect(AppConfig.backendBaseUrl.endsWith('/'), isFalse);
      expect(AppConfig.backendBaseUrl.startsWith('http'), isTrue);
    });

    test('resolveMediaUrl returns null for null or empty string', () {
      expect(AppConfig.resolveMediaUrl(null), isNull);
      expect(AppConfig.resolveMediaUrl(''), isNull);
      expect(AppConfig.resolveMediaUrl('   '), isNull);
    });

    test('resolveMediaUrl preserves absolute http and https URLs', () {
      expect(
        AppConfig.resolveMediaUrl('https://example.com/avatar.jpg'),
        'https://example.com/avatar.jpg',
      );
      expect(
        AppConfig.resolveMediaUrl('http://192.168.1.5:8001/media/avatars/user.jpg'),
        'http://192.168.1.5:8001/media/avatars/user.jpg',
      );
    });

    test('resolveMediaUrl correctly prepends backend origin for relative media paths', () {
      final backend = AppConfig.backendBaseUrl;
      expect(
        AppConfig.resolveMediaUrl('/media/profile_images/user.jpg'),
        '$backend/media/profile_images/user.jpg',
      );
      expect(
        AppConfig.resolveMediaUrl('media/avatars/user.jpg'),
        '$backend/media/avatars/user.jpg',
      );
      expect(
        AppConfig.resolveMediaUrl('/media/avatars/john_doe.png'),
        '$backend/media/avatars/john_doe.png',
      );
    });

    test('resolveMediaUrl does not generate duplicate slashes or /api/media/ paths', () {
      final url = AppConfig.resolveMediaUrl('/media/avatars/user.jpg')!;
      expect(url.contains('/api/media/'), isFalse);
      expect(url.contains('://'), isTrue);
      final withoutScheme = url.split('://')[1];
      expect(withoutScheme.contains('//'), isFalse);
    });
  });
}
