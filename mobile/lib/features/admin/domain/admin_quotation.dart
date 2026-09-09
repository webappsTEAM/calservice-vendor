import '../../../core/utils/json_parsing.dart';

/// Represents a quotation in the SEVO back office approval and pre-send review queues.
///
/// Backed by `/api/workforce/quotes/pending-approval/` and `/api/workforce/quotes/pending-review/`.
class AdminQuotation {
  const AdminQuotation({
    required this.id,
    required this.quoteNumber,
    this.quoteVersion = 1,
    required this.title,
    this.description = '',
    required this.status,
    required this.statusDisplay,
    required this.serviceCategory,
    required this.serviceName,
    required this.jobId,
    this.workJobId,
    this.technicianId,
    this.companyId,
    this.customerId,
    this.customerName = 'Customer',
    this.estimatedLaborCost = 0.0,
    this.estimatedMaterialsCost = 0.0,
    this.subtotalAmount = 0.0,
    this.discountAmount = 0.0,
    this.taxAmount = 0.0,
    this.totalAmount = 0.0,
    this.inspectionFee = 0.0,
    this.inspectionFeeAdjusted = 0.0,
    this.netPayable = 0.0,
    this.requiresStructuralClearance = false,
    this.isStructurallyCleared = false,
    this.customerDecision,
    this.customerDeclineReason,
    this.customerNotes,
    this.submittedForApprovalAt,
    this.validUntil,
    this.createdAt,
    this.updatedAt,
  });

  factory AdminQuotation.fromJson(Map<String, dynamic> json) {
    return AdminQuotation(
      id: parseInt(json['id']) ?? 0,
      quoteNumber: parseString(json['quote_number']) ?? 'QT-${json['id']}',
      quoteVersion: parseInt(json['quote_version']) ?? 1,
      title: parseString(json['title']) ?? '',
      description: parseString(json['description']) ?? '',
      status: parseString(json['status'])?.toUpperCase() ?? 'DRAFT',
      statusDisplay: parseString(json['status_display']) ??
          parseString(json['status']) ??
          'Draft',
      serviceCategory: parseString(json['service_category']) ?? 'Service',
      serviceName: parseString(json['service_name']) ??
          parseString(json['title']) ??
          'Quotation',
      jobId: parseInt(json['job_id']) ?? 0,
      workJobId: parseInt(json['work_job_id']),
      technicianId: parseInt(json['technician_id']),
      companyId: parseInt(json['company_id']),
      customerId: parseInt(json['customer_id']),
      customerName: parseString(json['customer_name']) ?? 'Customer',
      estimatedLaborCost: parseDouble(json['estimated_labor_cost']) ?? 0.0,
      estimatedMaterialsCost:
          parseDouble(json['estimated_materials_cost']) ?? 0.0,
      subtotalAmount: parseDouble(json['subtotal_amount']) ?? 0.0,
      discountAmount: parseDouble(json['discount_amount']) ?? 0.0,
      taxAmount: parseDouble(json['tax_amount']) ?? 0.0,
      totalAmount: parseDouble(json['total_amount']) ?? 0.0,
      inspectionFee: parseDouble(json['inspection_fee']) ?? 0.0,
      inspectionFeeAdjusted:
          parseDouble(json['inspection_fee_adjusted']) ?? 0.0,
      netPayable: parseDouble(json['net_payable']) ??
          parseDouble(json['total_amount']) ??
          0.0,
      requiresStructuralClearance:
          parseBool(json['requires_structural_clearance']),
      isStructurallyCleared: parseBool(json['is_structurally_cleared']),
      customerDecision: parseString(json['customer_decision']),
      customerDeclineReason: parseString(json['customer_decline_reason']),
      customerNotes: parseString(json['customer_notes']),
      submittedForApprovalAt:
          parseDateTime(json['submitted_for_approval_at']),
      validUntil: parseDateTime(json['valid_until']),
      createdAt: parseDateTime(json['created_at']),
      updatedAt: parseDateTime(json['updated_at']),
    );
  }

  final int id;
  final String quoteNumber;
  final int quoteVersion;
  final String title;
  final String description;
  final String status;
  final String statusDisplay;
  final String serviceCategory;
  final String serviceName;
  final int jobId;
  final int? workJobId;
  final int? technicianId;
  final int? companyId;
  final int? customerId;
  final String customerName;
  final double estimatedLaborCost;
  final double estimatedMaterialsCost;
  final double subtotalAmount;
  final double discountAmount;
  final double taxAmount;
  final double totalAmount;
  final double inspectionFee;
  final double inspectionFeeAdjusted;
  final double netPayable;
  final bool requiresStructuralClearance;
  final bool isStructurallyCleared;
  final String? customerDecision;
  final String? customerDeclineReason;
  final String? customerNotes;
  final DateTime? submittedForApprovalAt;
  final DateTime? validUntil;
  final DateTime? createdAt;
  final DateTime? updatedAt;
}
