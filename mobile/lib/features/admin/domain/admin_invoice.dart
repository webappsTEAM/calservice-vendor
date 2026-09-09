import '../../../core/utils/json_parsing.dart';

/// Represents a line item on an invoice.
class AdminInvoiceItem {
  const AdminInvoiceItem({
    required this.id,
    required this.name,
    this.description = '',
    this.itemType = 'SERVICE',
    this.quantity = 1.0,
    this.unit = 'unit',
    this.unitPrice = 0.0,
    this.taxRate = 0.0,
    this.discountAmount = 0.0,
    this.totalAmount = 0.0,
  });

  factory AdminInvoiceItem.fromJson(Map<String, dynamic> json) {
    return AdminInvoiceItem(
      id: parseInt(json['id']) ?? 0,
      name: parseString(json['name']) ?? 'Item',
      description: parseString(json['description']) ?? '',
      itemType: parseString(json['item_type']) ?? 'SERVICE',
      quantity: parseDouble(json['quantity']) ?? 1.0,
      unit: parseString(json['unit']) ?? 'unit',
      unitPrice: parseDouble(json['unit_price']) ?? 0.0,
      taxRate: parseDouble(json['tax_rate']) ?? 0.0,
      discountAmount: parseDouble(json['discount_amount']) ?? 0.0,
      totalAmount: parseDouble(json['total_amount']) ??
          parseDouble(json['line_total']) ??
          0.0,
    );
  }

  final int id;
  final String name;
  final String description;
  final String itemType;
  final double quantity;
  final String unit;
  final double unitPrice;
  final double taxRate;
  final double discountAmount;
  final double totalAmount;
}

/// Represents a payment recorded against an invoice.
class AdminInvoicePayment {
  const AdminInvoicePayment({
    required this.id,
    required this.amount,
    required this.method,
    this.reference = '',
    this.status = 'COMPLETED',
    this.recordedAt,
    this.ledgerEntryId,
  });

  factory AdminInvoicePayment.fromJson(Map<String, dynamic> json) {
    return AdminInvoicePayment(
      id: parseInt(json['id']) ?? 0,
      amount: parseDouble(json['amount']) ?? 0.0,
      method: parseString(json['method']) ?? 'ONLINE',
      reference: parseString(json['reference']) ?? '',
      status: parseString(json['status']) ?? 'COMPLETED',
      recordedAt: parseDateTime(json['recorded_at']) ??
          parseDateTime(json['created_at']),
      ledgerEntryId: parseInt(json['ledger_entry_id']),
    );
  }

  final int id;
  final double amount;
  final String method;
  final String reference;
  final String status;
  final DateTime? recordedAt;
  final int? ledgerEntryId;
}

/// Represents an invoice in the SEVO back office and workforce operations.
///
/// Backed by `/api/workforce/invoices/` and `/api/workforce/invoices/<id>/`.
class AdminInvoice {
  const AdminInvoice({
    required this.id,
    required this.invoiceNumber,
    required this.status,
    required this.statusDisplay,
    this.quoteId,
    this.quoteNumber,
    this.jobId,
    this.customerId,
    this.companyId,
    this.technicianId,
    this.billToName = 'Customer',
    this.billToPhone = '',
    this.billToEmail = '',
    this.billToAddress = '',
    this.serviceCategory = 'Service',
    this.serviceName = 'Service Invoice',
    this.subtotalAmount = 0.0,
    this.discountAmount = 0.0,
    this.taxAmount = 0.0,
    this.inspectionFeeAdjusted = 0.0,
    this.totalAmount = 0.0,
    this.amountPaid = 0.0,
    this.balanceDue = 0.0,
    this.advancePercent,
    this.advanceAmount = 0.0,
    this.balanceAmount = 0.0,
    this.issuedAt,
    this.dueDate,
    this.paidAt,
    this.cancelledAt,
    this.items = const [],
    this.payments = const [],
  });

  factory AdminInvoice.fromJson(Map<String, dynamic> json) {
    final itemsJson = json['items'];
    final paymentsJson = json['payments'];

    return AdminInvoice(
      id: parseInt(json['id']) ?? 0,
      invoiceNumber:
          parseString(json['invoice_number']) ?? 'INV-${json['id']}',
      status: parseString(json['status'])?.toUpperCase() ?? 'ISSUED',
      statusDisplay: parseString(json['status_display']) ??
          parseString(json['status']) ??
          'Issued',
      quoteId: parseInt(json['quote_id']),
      quoteNumber: parseString(json['quote_number']),
      jobId: parseInt(json['job_id']),
      customerId: parseInt(json['customer_id']),
      companyId: parseInt(json['company_id']),
      technicianId: parseInt(json['technician_id']),
      billToName: parseString(json['bill_to_name']) ?? 'Customer',
      billToPhone: parseString(json['bill_to_phone']) ?? '',
      billToEmail: parseString(json['bill_to_email']) ?? '',
      billToAddress: parseString(json['bill_to_address']) ?? '',
      serviceCategory: parseString(json['service_category']) ?? 'Service',
      serviceName: parseString(json['service_name']) ?? 'Service Invoice',
      subtotalAmount: parseDouble(json['subtotal_amount']) ?? 0.0,
      discountAmount: parseDouble(json['discount_amount']) ?? 0.0,
      taxAmount: parseDouble(json['tax_amount']) ?? 0.0,
      inspectionFeeAdjusted:
          parseDouble(json['inspection_fee_adjusted']) ?? 0.0,
      totalAmount: parseDouble(json['total_amount']) ?? 0.0,
      amountPaid: parseDouble(json['amount_paid']) ?? 0.0,
      balanceDue: parseDouble(json['balance_due']) ?? 0.0,
      advancePercent: parseDouble(json['advance_percent']),
      advanceAmount: parseDouble(json['advance_amount']) ?? 0.0,
      balanceAmount: parseDouble(json['balance_amount']) ?? 0.0,
      issuedAt: parseDateTime(json['issued_at']) ??
          parseDateTime(json['created_at']),
      dueDate: parseDateTime(json['due_date']),
      paidAt: parseDateTime(json['paid_at']),
      cancelledAt: parseDateTime(json['cancelled_at']),
      items: itemsJson is List
          ? itemsJson
              .whereType<Map<String, dynamic>>()
              .map(AdminInvoiceItem.fromJson)
              .toList()
          : const [],
      payments: paymentsJson is List
          ? paymentsJson
              .whereType<Map<String, dynamic>>()
              .map(AdminInvoicePayment.fromJson)
              .toList()
          : const [],
    );
  }

  final int id;
  final String invoiceNumber;
  final String status;
  final String statusDisplay;
  final int? quoteId;
  final String? quoteNumber;
  final int? jobId;
  final int? customerId;
  final int? companyId;
  final int? technicianId;
  final String billToName;
  final String billToPhone;
  final String billToEmail;
  final String billToAddress;
  final String serviceCategory;
  final String serviceName;
  final double subtotalAmount;
  final double discountAmount;
  final double taxAmount;
  final double inspectionFeeAdjusted;
  final double totalAmount;
  final double amountPaid;
  final double balanceDue;
  final double? advancePercent;
  final double advanceAmount;
  final double balanceAmount;
  final DateTime? issuedAt;
  final DateTime? dueDate;
  final DateTime? paidAt;
  final DateTime? cancelledAt;
  final List<AdminInvoiceItem> items;
  final List<AdminInvoicePayment> payments;

  bool get isIssued => status == 'ISSUED';
  bool get isPartiallyPaid => status == 'PARTIALLY_PAID';
  bool get isPaid => status == 'PAID';
  bool get isCancelled => status == 'CANCELLED';
  bool get isRefunded => status == 'REFUNDED';
  bool get isDraft => status == 'DRAFT';
}
