import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/network/api_error.dart';

void main() {
  group('describeDioError and extractErrorMessage tests', () {
    test('extracts direct error string', () {
      final dioError = DioException(
        requestOptions: RequestOptions(path: '/workforce/signup/'),
        response: Response(
          requestOptions: RequestOptions(path: '/workforce/signup/'),
          statusCode: 400,
          data: {'error': 'An account with this email already exists.'},
        ),
      );
      expect(
        describeDioError(dioError),
        'An account with this email already exists.',
      );
    });

    test('extracts field-specific validation list errors (e.g. email uniqueness)', () {
      final dioError = DioException(
        requestOptions: RequestOptions(path: '/workforce/signup/'),
        response: Response(
          requestOptions: RequestOptions(path: '/workforce/signup/'),
          statusCode: 400,
          data: {
            'email': ['An account with this email already exists.'],
          },
        ),
      );
      expect(
        describeDioError(dioError),
        'An account with this email already exists.',
      );
    });

    test('extracts mobile number uniqueness validation errors', () {
      final dioError = DioException(
        requestOptions: RequestOptions(path: '/workforce/signup/'),
        response: Response(
          requestOptions: RequestOptions(path: '/workforce/signup/'),
          statusCode: 400,
          data: {
            'mobile_number': ['An account with this mobile number already exists.'],
          },
        ),
      );
      expect(
        describeDioError(dioError),
        'An account with this mobile number already exists.',
      );
    });

    test('extracts multiple field errors cleanly', () {
      final dioError = DioException(
        requestOptions: RequestOptions(path: '/workforce/signup/'),
        response: Response(
          requestOptions: RequestOptions(path: '/workforce/signup/'),
          statusCode: 400,
          data: {
            'email': ['An account with this email already exists.'],
            'mobile_number': ['An account with this mobile number already exists.'],
          },
        ),
      );
      final msg = describeDioError(dioError);
      expect(msg, contains('An account with this email already exists.'));
      expect(msg, contains('An account with this mobile number already exists.'));
    });

    test('extracts non_field_errors', () {
      final dioError = DioException(
        requestOptions: RequestOptions(path: '/workforce/signup/'),
        response: Response(
          requestOptions: RequestOptions(path: '/workforce/signup/'),
          statusCode: 400,
          data: {
            'non_field_errors': ['Unable to create user in requested organization.'],
          },
        ),
      );
      expect(
        describeDioError(dioError),
        'Unable to create user in requested organization.',
      );
    });

    test('extracts detail string', () {
      final dioError = DioException(
        requestOptions: RequestOptions(path: '/workforce/signup/'),
        response: Response(
          requestOptions: RequestOptions(path: '/workforce/signup/'),
          statusCode: 401,
          data: {'detail': 'Invalid credentials.'},
        ),
      );
      expect(
        describeDioError(dioError),
        'Invalid credentials.',
      );
    });

    test('handles network connection error', () {
      final dioError = DioException(
        requestOptions: RequestOptions(path: '/workforce/signup/'),
        type: DioExceptionType.connectionTimeout,
      );
      expect(
        describeDioError(dioError),
        'Network error. Please check your internet connection.',
      );
    });

    test('uses fallback message when data has no message and unknown status', () {
      final dioError = DioException(
        requestOptions: RequestOptions(path: '/workforce/signup/'),
        response: Response(
          requestOptions: RequestOptions(path: '/workforce/signup/'),
          statusCode: 418,
          data: null,
        ),
      );
      expect(
        describeDioError(dioError, fallback: 'Custom signup fallback.'),
        'Custom signup fallback.',
      );
    });
  });
}
