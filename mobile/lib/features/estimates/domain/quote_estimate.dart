import 'package:flutter/material.dart';

import '../../../core/utils/json_parsing.dart';

/// Represents a quote or estimate in the Workforce system.
///
/// Matches `/api/workforce/quotes/` and `/api/vendor/estimations/`.
class QuoteEstimate {
  const QuoteEstimate({
    required this.id,
    required this.quoteNumber,
    required this.jobId,
    required this.serviceName,
    required this.customerName,
    required this.status,
    required this.grandTotal,
    required this.laborCost,
    required this.materialsCost,
    required this.taxAmount,
    required this.discountAmount,
    required this.notes,
    this.brand = '',
    this.createdAt,
    this.expiresAt,
    this.itemsCount = 0,
  });

  factory QuoteEstimate.fromJson(Map<String, dynamic> json) {
    final jobDetails = json['job_details'] is Map<String, dynamic>
        ? json['job_details'] as Map<String, dynamic>
        : <String, dynamic>{};
    final acDetails = json['ac_details'] is Map<String, dynamic>
        ? json['ac_details'] as Map<String, dynamic>
        : <String, dynamic>{};

    return QuoteEstimate(
      id: parseInt(json['id']) ?? 0,
      quoteNumber: parseString(json['quote_number']) ??
          parseString(json['quote_ref']) ??
          parseString(json['request_id']) ??
          'QT-${json['id']}',
      jobId: parseInt(json['job_id']) ??
          parseInt(json['job']) ??
          parseInt(jobDetails['id']) ??
          parseInt(json['id']) ??
          0,
      serviceName: parseString(json['service_name']) ??
          parseString(jobDetails['issue_title']) ??
          parseString(json['issue_title']) ??
          parseString(json['service_category']) ??
          'AC Inspection',
      customerName: parseString(json['customer_name']) ??
          parseString(jobDetails['customer_name']) ??
          parseString(json['customer_display_name']) ??
          'Customer',
      brand: parseString(json['brand']) ??
          parseString(json['ac_brand']) ??
          parseString(json['unit_brand']) ??
          parseString(acDetails['ac_brand']) ??
          parseString(acDetails['brand']) ??
          parseString(jobDetails['brand']) ??
          parseString(jobDetails['ac_brand']) ??
          '',
      status: parseString(json['status'])?.toUpperCase() ?? 'DRAFT',
      grandTotal: parseDouble(json['grand_total']) ??
          parseDouble(json['total_amount']) ??
          parseDouble(json['estimated_total_cost']) ??
          parseDouble(json['quote_total']) ??
          0.0,
      laborCost: parseDouble(json['total_labor_cost']) ??
          parseDouble(json['labor_cost']) ??
          parseDouble(json['estimated_labor_cost']) ??
          0.0,
      materialsCost: parseDouble(json['total_materials_cost']) ??
          parseDouble(json['materials_cost']) ??
          parseDouble(json['estimated_materials_cost']) ??
          0.0,
      taxAmount: parseDouble(json['tax_amount']) ?? 0.0,
      discountAmount: parseDouble(json['discount_amount']) ?? 0.0,
      notes: parseString(json['notes']) ??
          parseString(json['description']) ??
          '',
      createdAt: parseDateTime(json['created_at']) ??
          parseDateTime(json['preferred_date']),
      expiresAt: parseDateTime(json['expires_at']),
      itemsCount: parseInt(json['items_count']) ??
          (json['items'] is List ? (json['items'] as List).length : 0),
    );
  }

  final int id;
  final String quoteNumber;
  final int jobId;
  final String serviceName;
  final String customerName;
  final String brand;
  final String status;
  final double grandTotal;
  final double laborCost;
  final double materialsCost;
  final double taxAmount;
  final double discountAmount;
  final String notes;
  final DateTime? createdAt;
  final DateTime? expiresAt;
  final int itemsCount;

  bool get isDraft =>
      status == 'DRAFT' ||
      status == 'NEW' ||
      status == 'REQUESTED' ||
      status == 'NEW_REQUEST' ||
      status == 'UNASSIGNED';

  bool get isPendingReview =>
      status == 'PENDING_REVIEW' || status == 'PENDING_ADMIN_APPROVAL';

  bool get isAssigned =>
      status == 'ASSIGNED' ||
      status == 'TECHNICIAN_ASSIGNED' ||
      status == 'VENDOR_CONFIRMED';

  bool get isInProgress =>
      status == 'IN_PROGRESS' ||
      status == 'INSPECTION_IN_PROGRESS' ||
      status == 'TECHNICIAN_ON_THE_WAY' ||
      status == 'TECHNICIAN_ARRIVED' ||
      status == 'INSPECTION_COMPLETED' ||
      status == 'CONVERSION_PENDING';

  bool get isSent =>
      status == 'SENT_TO_CUSTOMER' ||
      status == 'SENT' ||
      status == 'QUOTATION_SENT';

  bool get isAccepted =>
      status == 'CUSTOMER_ACCEPTED' ||
      status == 'CUSTOMER_APPROVED' ||
      status == 'ACCEPTED' ||
      status == 'CONVERTED' ||
      status == 'ADMIN_APPROVED' ||
      status == 'COMPLETED' ||
      status == 'CLOSED';
  bool get isDeclined =>
      status == 'CUSTOMER_DECLINED' ||
      status == 'DECLINED' ||
      status == 'REJECTED' ||
      status == 'ADMIN_REJECTED';
  bool get isExpired => status == 'EXPIRED';

  String get statusDisplay {
    switch (status) {
      case 'DRAFT':
      case 'NEW':
        return 'New Request';
      case 'PENDING_REVIEW':
        return 'Pending Review';
      case 'PENDING_ADMIN_APPROVAL':
        return 'Awaiting Approval';
      case 'ASSIGNED':
        return 'Assigned';
      case 'IN_PROGRESS':
        return 'In Progress';
      case 'SENT_TO_CUSTOMER':
      case 'SENT':
      case 'QUOTATION_SENT':
        return 'Quotation Sent';
      case 'CUSTOMER_ACCEPTED':
      case 'ACCEPTED':
        return 'Accepted';
      case 'ADMIN_APPROVED':
        return 'Approved';
      case 'CONVERSION_PENDING':
        return 'Conversion Pending';
      case 'CONVERTED':
        return 'Converted to Work';
      case 'COMPLETED':
        return 'Completed';
      case 'CUSTOMER_DECLINED':
      case 'DECLINED':
        return 'Declined';
      case 'REJECTED':
      case 'ADMIN_REJECTED':
        return 'Rejected';
      case 'CHANGES_REQUESTED':
        return 'Changes Requested';
      case 'EXPIRED':
        return 'Expired';
      case 'CANCELLED':
        return 'Cancelled';
      default:
        return status;
    }
  }

  Color get statusColor {
    switch (status) {
      case 'DRAFT':
        return const Color(0xFF64748B); // Slate
      case 'PENDING_REVIEW':
      case 'PENDING_ADMIN_APPROVAL':
        return const Color(0xFF6366F1); // Indigo
      case 'ASSIGNED':
        return const Color(0xFF8B5CF6); // Violet
      case 'IN_PROGRESS':
      case 'CONVERSION_PENDING':
        return const Color(0xFFD97706); // Amber
      case 'SENT_TO_CUSTOMER':
      case 'SENT':
        return const Color(0xFF0284C7); // Sky Blue
      case 'CUSTOMER_ACCEPTED':
      case 'ACCEPTED':
      case 'CONVERTED':
      case 'ADMIN_APPROVED':
      case 'COMPLETED':
        return const Color(0xFF059669); // Emerald Green
      case 'CUSTOMER_DECLINED':
      case 'DECLINED':
      case 'REJECTED':
      case 'ADMIN_REJECTED':
      case 'CANCELLED':
        return const Color(0xFFDC2626); // Rose/Red
      case 'CHANGES_REQUESTED':
        return const Color(0xFFF59E0B); // Amber
      case 'EXPIRED':
        return const Color(0xFF94A3B8); // Gray
      default:
        return const Color(0xFF004E89); // Peacock Blue
    }
  }
}
