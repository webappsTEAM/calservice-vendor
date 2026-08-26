import 'package:dio/dio.dart';

/// Turns a failed API call into a short, user-facing message.
///
/// Matches the error shapes the existing backend returns:
/// - `{"error": "..."}` or `{"detail": "..."}`
/// - `{"field_name": ["Error 1", "Error 2"]}`
/// - `{"non_field_errors": ["..."]}`
/// - Generic network errors
String describeDioError(
  DioException error, {
  String fallback = 'Unable to complete sign-in. Please try again.',
}) {
  final data = error.response?.data;
  if (data is Map) {
    final apiError = data['error'];
    if (apiError is String && apiError.isNotEmpty) {
      return apiError;
    }
    final detail = data['detail'];
    if (detail is String && detail.isNotEmpty) {
      return detail;
    }
    final nonField = data['non_field_errors'];
    if (nonField is List && nonField.isNotEmpty) {
      return nonField.map((e) => e.toString()).join(' ');
    } else if (nonField is String && nonField.isNotEmpty) {
      return nonField;
    }

    // Extract any other field-specific errors e.g. email, mobile_number
    final fieldErrors = <String>[];
    for (final entry in data.entries) {
      final key = entry.key.toString();
      if (key == 'code' || key == 'status' || key == 'status_code') continue;
      final val = entry.value;
      if (val is List && val.isNotEmpty) {
        fieldErrors.addAll(val.map((e) => e.toString()));
      } else if (val is String && val.isNotEmpty) {
        fieldErrors.add(val);
      }
    }
    if (fieldErrors.isNotEmpty) {
      return fieldErrors.join(' ');
    }
  } else if (data is String && data.isNotEmpty) {
    return data;
  }

  switch (error.type) {
    case DioExceptionType.connectionError:
    case DioExceptionType.connectionTimeout:
    case DioExceptionType.receiveTimeout:
    case DioExceptionType.sendTimeout:
      return 'Network error. Please check your internet connection.';
    default:
      return fallback;
  }
}
