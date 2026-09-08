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
    this.createdAt,
    this.expiresAt,
    this.itemsCount = 0,
  });

  factory QuoteEstimate.fromJson(Map<String, dynamic> json) {
    final jobDetails = json['job_details'] is Map<String, dynamic>
        ? json['job_details'] as Map<String, dynamic>
        : <String, dynamic>{};

    return QuoteEstimate(
      id: parseInt(json['id']) ?? 0,
      quoteNumber: parseString(json['quote_number']) ??
          parseString(json['quote_ref']) ??
          'QT-${json['id']}',
      jobId: parseInt(json['job_id']) ??
          parseInt(json['job']) ??
          parseInt(jobDetails['id']) ??
          0,
      serviceName: parseString(json['service_name']) ??
          parseString(jobDetails['issue_title']) ??
          parseString(json['issue_title']) ??
          'Service Estimate',
      customerName: parseString(json['customer_name']) ??
          parseString(jobDetails['customer_name']) ??
          parseString(json['customer_display_name']) ??
          'Customer',
      status: parseString(json['status'])?.toUpperCase() ?? 'DRAFT',
      grandTotal: parseDouble(json['grand_total']) ??
          parseDouble(json['total_amount']) ??
          parseDouble(json['estimated_total_cost']) ??
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
      createdAt: parseDateTime(json['created_at']),
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

  bool get isDraft => status == 'DRAFT';
  bool get isPendingReview => status == 'PENDING_REVIEW';
  bool get isSent =>
      status == 'SENT_TO_CUSTOMER' || status == 'SENT';
  bool get isAccepted =>
      status == 'CUSTOMER_ACCEPTED' ||
      status == 'ACCEPTED' ||
      status == 'CONVERTED';
  bool get isDeclined =>
      status == 'CUSTOMER_DECLINED' || status == 'DECLINED' || status == 'REJECTED';
  bool get isExpired => status == 'EXPIRED';

  String get statusDisplay {
    switch (status) {
      case 'DRAFT':
        return 'Draft';
      case 'PENDING_REVIEW':
        return 'Pending Review';
      case 'SENT_TO_CUSTOMER':
      case 'SENT':
        return 'Sent to Client';
      case 'CUSTOMER_ACCEPTED':
      case 'ACCEPTED':
        return 'Accepted';
      case 'CONVERTED':
        return 'Converted to Work';
      case 'CUSTOMER_DECLINED':
      case 'DECLINED':
      case 'REJECTED':
        return 'Declined';
      case 'CHANGES_REQUESTED':
        return 'Changes Requested';
      case 'EXPIRED':
        return 'Expired';
      default:
        return status;
    }
  }

  Color get statusColor {
    switch (status) {
      case 'DRAFT':
        return const Color(0xFF64748B); // Slate
      case 'PENDING_REVIEW':
        return const Color(0xFF6366F1); // Indigo
      case 'SENT_TO_CUSTOMER':
      case 'SENT':
        return const Color(0xFF0284C7); // Sky Blue
      case 'CUSTOMER_ACCEPTED':
      case 'ACCEPTED':
      case 'CONVERTED':
        return const Color(0xFF059669); // Emerald Green
      case 'CUSTOMER_DECLINED':
      case 'DECLINED':
      case 'REJECTED':
        return const Color(0xFFDC2626); // Rose/Red
      case 'CHANGES_REQUESTED':
        return const Color(0xFFD97706); // Amber
      case 'EXPIRED':
        return const Color(0xFF94A3B8); // Gray
      default:
        return const Color(0xFF004E89); // Peacock Blue
    }
  }
}
