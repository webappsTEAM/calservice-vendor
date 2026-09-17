/// Central place for environment-level configuration such as the API base URL.
class AppConfig {
  AppConfig._();

  static const String productionApiBaseUrl =
      'https://vendor.caldimservices.online/api';

  /// The API base URL the app talks to.
  ///
  /// Defaults to the production API. Override for local backend testing with:
  /// `flutter run --dart-define=API_BASE_URL=http://your-lan-ip:8001/api`
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: productionApiBaseUrl,
  );

  /// Root host/origin of the backend (e.g. `https://vendor.caldimservices.online`
  /// or `http://192.168.1.100:8001`), derived by stripping the API path.
  static String get backendBaseUrl {
    final trimmed = apiBaseUrl.trim();
    final uri = Uri.tryParse(trimmed);
    if (uri != null && uri.hasScheme && uri.host.isNotEmpty) {
      final portPart = uri.hasPort ? ':${uri.port}' : '';
      return '${uri.scheme}://${uri.host}$portPart';
    }
    var base = trimmed;
    if (base.endsWith('/')) {
      base = base.substring(0, base.length - 1);
    }
    if (base.endsWith('/api')) {
      base = base.substring(0, base.length - 4);
    }
    return base;
  }

  /// Converts a relative or absolute media path into a fully-qualified URL.
  ///
  /// Examples:
  /// - `null` or `""` -> `null`
  /// - `"https://example.com/avatar.jpg"` -> `"https://example.com/avatar.jpg"`
  /// - `"/media/avatars/u1.jpg"` -> `"https://vendor.caldimservices.online/media/avatars/u1.jpg"`
  /// - `"media/avatars/u1.jpg"` -> `"https://vendor.caldimservices.online/media/avatars/u1.jpg"`
  static String? resolveMediaUrl(String? path) {
    if (path == null) return null;
    final trimmed = path.trim();
    if (trimmed.isEmpty) return null;

    if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
      return trimmed;
    }

    final host = backendBaseUrl;
    if (trimmed.startsWith('/')) {
      return '$host$trimmed';
    } else {
      return '$host/$trimmed';
    }
  }
}
