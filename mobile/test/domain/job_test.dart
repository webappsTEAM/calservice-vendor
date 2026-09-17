import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/jobs/domain/job.dart';

void main() {
  group('Job Domain Model & JSON Parsing', () {
    test('parses full Job JSON with cart items and customer contact', () {
      final json = {
        'id': 2649,
        'request_id': 'EL0827',
        'customer_name': 'Thejjaa',
        'phone': '+919876543210',
        'email': 'customer@example.com',
        'service_category': 'Electrical',
        'service_title': 'Modular Switch Replacement',
        'issue_title': 'Switch sparking',
        'description': 'Main hall light switch needs urgent replacement.',
        'status': 'offered',
        'priority': 'HIGH',
        'address': 'a1, 05, Bagalur Rd, KCC Nagar, Nallur, Tamil Nadu 635109',
        'latitude': 12.7409,
        'longitude': 77.8253,
        'distance_km': 0.12,
        'preferred_date': '2026-08-24',
        'preferred_time': '11:00 AM',
        'total_amount': 999.00,
        'payment_status': 'pending',
        'payment_method': 'CASH_ON_SERVICE',
        'cart_data': [
          {
            'name': 'Modular Switch (16A)',
            'description': 'Anchor Roma 16A modular switch',
            'selectedOption': '1-Way Switch',
            'quantity': 2,
          },
          {
            'name': 'Installation Labor',
            'quantity': 1,
          },
        ],
        'is_offer': true,
        'is_accepted_by_current_employee': false,
        'is_assigned_to_current_employee': false,
        'can_cancel': false,
      };

      final job = Job.fromJson(json);

      expect(job.id, equals(2649));
      expect(job.requestId, equals('EL0827'));
      expect(job.customerName, equals('Thejjaa'));
      expect(job.phone, equals('+919876543210'));
      expect(job.email, equals('customer@example.com'));
      expect(job.displayTitle, equals('Modular Switch Replacement'));
      expect(job.totalAmount, equals(999.00));
      expect(job.cartData.length, equals(2));
      expect(job.cartData[0].name, equals('Modular Switch (16A)'));
      expect(job.cartData[0].selectedOption, equals('1-Way Switch'));
      expect(job.cartData[0].quantity, equals(2));
      expect(job.hasCoordinates, isTrue);
      expect(job.isOffer, isTrue);
    });

    test('falls back correctly when titles are null', () {
      final json = {
        'id': 100,
        'request_id': '#100',
        'service_category': 'Appliance Repair',
        'status': 'assigned',
        'is_offer': false,
        'is_accepted_by_current_employee': false,
        'is_assigned_to_current_employee': false,
        'can_cancel': false,
      };

      final job = Job.fromJson(json);
      expect(job.displayTitle, equals('Appliance Repair'));
    });

    test('parses technician details from flat JSON fields', () {
      final json = {
        'id': 101,
        'request_id': 'REQ-101',
        'status': 'assigned',
        'technician_name': 'Gokul',
        'technician_phone': '9876543210',
        'technician_email': 'gokul.m@caldimengg.in',
        'technician_id': 42,
        'is_offer': false,
        'is_accepted_by_current_employee': false,
        'is_assigned_to_current_employee': true,
        'can_cancel': false,
      };

      final job = Job.fromJson(json);
      expect(job.technicianName, equals('Gokul'));
      expect(job.technicianPhone, equals('9876543210'));
      expect(job.technicianEmail, equals('gokul.m@caldimengg.in'));
      expect(job.technicianId, equals(42));
    });

    test('parses technician details from nested assigned_employee object', () {
      final json = {
        'id': 102,
        'request_id': 'REQ-102',
        'status': 'in_progress',
        'assigned_employee': {
          'id': 55,
          'name': 'Priya Kumar',
          'phone': '9123456780',
          'email': 'priya.k@example.com',
        },
        'is_offer': false,
        'is_accepted_by_current_employee': true,
        'is_assigned_to_current_employee': true,
        'can_cancel': false,
      };

      final job = Job.fromJson(json);
      expect(job.technicianName, equals('Priya Kumar'));
      expect(job.technicianPhone, equals('9123456780'));
      expect(job.technicianEmail, equals('priya.k@example.com'));
      expect(job.technicianId, equals(55));
    });

    test('parses technician details from nested technician object with user profile', () {
      final json = {
        'id': 103,
        'request_id': 'REQ-103',
        'status': 'assigned',
        'technician': {
          'id': 88,
          'user': {
            'first_name': 'Anand',
            'last_name': 'Raj',
            'email': 'anand.r@example.com',
          },
          'phone_number': '9988776655',
        },
        'is_offer': false,
        'is_accepted_by_current_employee': false,
        'is_assigned_to_current_employee': false,
        'can_cancel': true,
      };

      final job = Job.fromJson(json);
      expect(job.technicianName, equals('Anand Raj'));
      expect(job.technicianPhone, equals('9988776655'));
      expect(job.technicianEmail, equals('anand.r@example.com'));
      expect(job.technicianId, equals(88));
    });
  });
}
