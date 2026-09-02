import 'package:flutter/foundation.dart';

/// Root model for Database & Egress telemetry returned by
/// `GET /workforce/admin/database-telemetry/`.
@immutable
class AdminMonitoringData {
  const AdminMonitoringData({
    required this.plainEnglishSummary,
    required this.databaseHealth,
    required this.analytics,
    required this.indexHealth,
    required this.apiTrafficOptimizations,
    required this.supabaseEgress,
  });

  factory AdminMonitoringData.fromJson(Map<String, dynamic> json) {
    return AdminMonitoringData(
      plainEnglishSummary: PlainEnglishSummary.fromJson(
        json['plain_english_summary'] as Map<String, dynamic>? ?? {},
      ),
      databaseHealth: DatabaseHealth.fromJson(
        json['database_health'] as Map<String, dynamic>? ?? {},
      ),
      analytics: DatabaseAnalytics.fromJson(
        json['analytics'] as Map<String, dynamic>? ?? {},
      ),
      indexHealth: IndexHealth.fromJson(
        json['index_health'] as Map<String, dynamic>? ?? {},
      ),
      apiTrafficOptimizations: (json['api_traffic_optimizations'] as List<dynamic>? ?? [])
          .whereType<Map<String, dynamic>>()
          .map(TrafficOptimization.fromJson)
          .toList(),
      supabaseEgress: SupabaseEgress.fromJson(
        json['supabase_egress'] as Map<String, dynamic>? ?? {},
      ),
    );
  }

  final PlainEnglishSummary plainEnglishSummary;
  final DatabaseHealth databaseHealth;
  final DatabaseAnalytics analytics;
  final IndexHealth indexHealth;
  final List<TrafficOptimization> apiTrafficOptimizations;
  final SupabaseEgress supabaseEgress;
}

/// Plain-English executive summary headlines.
@immutable
class PlainEnglishSummary {
  const PlainEnglishSummary({
    this.systemHealthStatus = 'Healthy & Optimal',
    this.speedHeadline = 'Almost all data requests are served instantly from RAM.',
    this.storageHeadline = 'Most storage is safely used for audit logs and notification history.',
    this.optimizationsHeadline = '4 network guardrails are active, eliminating duplicate queries.',
    this.indexUtilizationHeadline = 'Search shortcuts are actively accelerating queries.',
  });

  factory PlainEnglishSummary.fromJson(Map<String, dynamic> json) {
    return PlainEnglishSummary(
      systemHealthStatus: json['system_health_status'] as String? ?? 'Healthy & Optimal',
      speedHeadline: json['speed_headline'] as String? ?? 'Almost all data requests are served instantly from RAM.',
      storageHeadline: json['storage_headline'] as String? ?? 'Most storage is safely used for audit logs and notification history.',
      optimizationsHeadline: json['optimizations_headline'] as String? ?? '4 network guardrails are active, eliminating duplicate queries.',
      indexUtilizationHeadline: json['index_utilization_headline'] as String? ?? 'Search shortcuts are actively accelerating queries.',
    );
  }

  final String systemHealthStatus;
  final String speedHeadline;
  final String storageHeadline;
  final String optimizationsHeadline;
  final String indexUtilizationHeadline;
}

/// PostgreSQL database health and cache efficiency.
@immutable
class DatabaseHealth {
  const DatabaseHealth({
    this.engine = 'postgresql',
    this.databaseSize = 'N/A',
    this.statsResetTimestamp = 'N/A',
    this.databaseCacheEfficiency = const CacheEfficiency(),
    this.indexCacheEfficiency = const CacheEfficiency(),
    this.billingCost = 'Not available from PostgreSQL telemetry.',
    this.measurementType = 'ACTUAL',
  });

  factory DatabaseHealth.fromJson(Map<String, dynamic> json) {
    return DatabaseHealth(
      engine: json['engine'] as String? ?? 'postgresql',
      databaseSize: json['database_size'] as String? ?? 'N/A',
      statsResetTimestamp: json['stats_reset_timestamp'] as String? ?? 'N/A',
      databaseCacheEfficiency: CacheEfficiency.fromJson(
        json['database_cache_efficiency'] as Map<String, dynamic>? ?? {},
      ),
      indexCacheEfficiency: CacheEfficiency.fromJson(
        json['index_cache_efficiency'] as Map<String, dynamic>? ?? {},
      ),
      billingCost: json['billing_cost'] as String? ?? 'Not available from PostgreSQL telemetry.',
      measurementType: json['measurement_type'] as String? ?? 'ACTUAL',
    );
  }

  final String engine;
  final String databaseSize;
  final String statsResetTimestamp;
  final CacheEfficiency databaseCacheEfficiency;
  final CacheEfficiency indexCacheEfficiency;
  final String billingCost;
  final String measurementType;
}

int? _toInt(dynamic value) {
  if (value == null) return null;
  if (value is int) return value;
  if (value is num) return value.toInt();
  if (value is String) return int.tryParse(value) ?? double.tryParse(value)?.toInt();
  return null;
}

double? _toDouble(dynamic value) {
  if (value == null) return null;
  if (value is double) return value;
  if (value is num) return value.toDouble();
  if (value is String) return double.tryParse(value);
  return null;
}

/// Cache hit ratio metrics.
@immutable
class CacheEfficiency {
  const CacheEfficiency({
    this.blocksHit = 0,
    this.blocksRead = 0,
    this.hitRatioPercent,
    this.status = 'OPTIMAL',
    this.measurementType = 'ACTUAL',
  });

  factory CacheEfficiency.fromJson(Map<String, dynamic> json) {
    return CacheEfficiency(
      blocksHit: _toInt(json['blocks_hit']) ?? 0,
      blocksRead: _toInt(json['blocks_read']) ?? 0,
      hitRatioPercent: _toDouble(json['hit_ratio_percent']),
      status: json['status'] as String? ?? 'OPTIMAL',
      measurementType: json['measurement_type'] as String? ?? 'ACTUAL',
    );
  }

  final int blocksHit;
  final int blocksRead;
  final double? hitRatioPercent;
  final String status;
  final String measurementType;

  String get formattedRatio {
    if (hitRatioPercent == null) return '100%';
    return '${hitRatioPercent!.toStringAsFixed(hitRatioPercent! % 1 == 0 ? 0 : 2)}%';
  }
}

/// Analytics breakdown including categories and utilization rates.
@immutable
class DatabaseAnalytics {
  const DatabaseAnalytics({
    this.totalIndexes = 0,
    this.usedIndexes = 0,
    this.unusedIndexes = 0,
    this.utilizationRatePercent = 0.0,
    this.categoryStorageBytes = const {},
    this.topUsedIndexes = const [],
  });

  factory DatabaseAnalytics.fromJson(Map<String, dynamic> json) {
    final catRaw = json['category_storage_bytes'] as Map<String, dynamic>? ?? {};
    final categoryBytes = catRaw.map(
      (key, value) => MapEntry(key, _toInt(value) ?? 0),
    );

    return DatabaseAnalytics(
      totalIndexes: _toInt(json['total_indexes']) ?? 0,
      usedIndexes: _toInt(json['used_indexes']) ?? 0,
      unusedIndexes: _toInt(json['unused_indexes']) ?? 0,
      utilizationRatePercent: _toDouble(json['utilization_rate_percent']) ?? 0.0,
      categoryStorageBytes: categoryBytes,
      topUsedIndexes: (json['top_used_indexes'] as List<dynamic>? ?? [])
          .whereType<Map<String, dynamic>>()
          .map(DatabaseIndex.fromJson)
          .toList(),
    );
  }

  final int totalIndexes;
  final int usedIndexes;
  final int unusedIndexes;
  final double utilizationRatePercent;
  final Map<String, int> categoryStorageBytes;
  final List<DatabaseIndex> topUsedIndexes;

  int get totalCategoryBytes =>
      categoryStorageBytes.values.fold(0, (sum, val) => sum + val);
}

/// Index health, pagination, and table storage.
@immutable
class IndexHealth {
  const IndexHealth({
    this.totalMonitoredIndexes = 0,
    this.filteredCount = 0,
    this.page = 1,
    this.pageSize = 15,
    this.totalPages = 1,
    this.indexes = const [],
    this.allTables = const [],
    this.tableStorage = const [],
    this.note = '',
  });

  factory IndexHealth.fromJson(Map<String, dynamic> json) {
    return IndexHealth(
      totalMonitoredIndexes: _toInt(json['total_monitored_indexes']) ?? 0,
      filteredCount: _toInt(json['filtered_count']) ?? 0,
      page: _toInt(json['page']) ?? 1,
      pageSize: _toInt(json['page_size']) ?? 15,
      totalPages: _toInt(json['total_pages']) ?? 1,
      indexes: (json['indexes'] as List<dynamic>? ?? [])
          .whereType<Map<String, dynamic>>()
          .map(DatabaseIndex.fromJson)
          .toList(),
      allTables: (json['all_tables'] as List<dynamic>? ?? [])
          .map((e) => e.toString())
          .toList(),
      tableStorage: (json['table_storage'] as List<dynamic>? ?? [])
          .whereType<Map<String, dynamic>>()
          .map(TableStorage.fromJson)
          .toList(),
      note: json['note'] as String? ?? '',
    );
  }

  final int totalMonitoredIndexes;
  final int filteredCount;
  final int page;
  final int pageSize;
  final int totalPages;
  final List<DatabaseIndex> indexes;
  final List<String> allTables;
  final List<TableStorage> tableStorage;
  final String note;
}

/// A specific PostgreSQL index's telemetry.
@immutable
class DatabaseIndex {
  const DatabaseIndex({
    this.schema = 'public',
    required this.tableName,
    required this.indexName,
    this.indexBytes = 0,
    this.indexSize = '0 bytes',
    this.cumulativeScans = 0,
    this.tuplesRead = 0,
    this.tuplesFetched = 0,
    this.indexDefinition = '',
    this.status = 'USED',
    this.note = '',
    this.measurementType = 'ACTUAL',
  });

  factory DatabaseIndex.fromJson(Map<String, dynamic> json) {
    return DatabaseIndex(
      schema: json['schema'] as String? ?? 'public',
      tableName: json['table_name'] as String? ?? '',
      indexName: json['index_name'] as String? ?? '',
      indexBytes: _toInt(json['index_bytes']) ?? 0,
      indexSize: json['index_size'] as String? ?? '0 bytes',
      cumulativeScans: _toInt(json['cumulative_scans_since_stats_reset']) ?? 0,
      tuplesRead: _toInt(json['tuples_read']) ?? 0,
      tuplesFetched: _toInt(json['tuples_fetched']) ?? 0,
      indexDefinition: json['index_definition'] as String? ?? '',
      status: json['status'] as String? ?? 'USED',
      note: json['note'] as String? ?? '',
      measurementType: json['measurement_type'] as String? ?? 'ACTUAL',
    );
  }

  final String schema;
  final String tableName;
  final String indexName;
  final int indexBytes;
  final String indexSize;
  final int cumulativeScans;
  final int tuplesRead;
  final int tuplesFetched;
  final String indexDefinition;
  final String status;
  final String note;
  final String measurementType;

  bool get isUsed => cumulativeScans > 0 || status == 'USED';
}

/// Table disk storage breakdown.
@immutable
class TableStorage {
  const TableStorage({
    required this.tableName,
    this.dataSize = '0 bytes',
    this.indexSize = '0 bytes',
    this.totalSize = '0 bytes',
    this.totalBytes = 0,
    this.dataBytes = 0,
    this.indexBytes = 0,
    this.measurementType = 'ACTUAL',
  });

  factory TableStorage.fromJson(Map<String, dynamic> json) {
    return TableStorage(
      tableName: json['table_name'] as String? ?? '',
      dataSize: json['data_size'] as String? ?? '0 bytes',
      indexSize: json['index_size'] as String? ?? '0 bytes',
      totalSize: json['total_size'] as String? ?? '0 bytes',
      totalBytes: _toInt(json['total_bytes']) ?? 0,
      dataBytes: _toInt(json['data_bytes']) ?? 0,
      indexBytes: _toInt(json['index_bytes']) ?? 0,
      measurementType: json['measurement_type'] as String? ?? 'ACTUAL',
    );
  }

  final String tableName;
  final String dataSize;
  final String indexSize;
  final String totalSize;
  final int totalBytes;
  final int dataBytes;
  final int indexBytes;
  final String measurementType;
}

/// Code-derived network guardrail & traffic optimization.
@immutable
class TrafficOptimization {
  const TrafficOptimization({
    required this.endpoint,
    required this.title,
    required this.simpleExplanation,
    this.serializer,
    this.mechanism,
    this.fieldCount,
    this.omittedFields = const [],
    this.payloadReduction = '',
    this.status = 'IMPLEMENTED',
    this.measurementType = 'CODE-DERIVED',
  });

  factory TrafficOptimization.fromJson(Map<String, dynamic> json) {
    return TrafficOptimization(
      endpoint: json['endpoint'] as String? ?? '',
      title: json['title'] as String? ?? '',
      simpleExplanation: json['simple_explanation'] as String? ?? '',
      serializer: json['serializer'] as String?,
      mechanism: json['mechanism'] as String?,
      fieldCount: _toInt(json['field_count']),
      omittedFields: (json['omitted_fields'] as List<dynamic>? ?? [])
          .map((e) => e.toString())
          .toList(),
      payloadReduction: json['payload_reduction'] as String? ?? '',
      status: json['status'] as String? ?? 'IMPLEMENTED',
      measurementType: json['measurement_type'] as String? ?? 'CODE-DERIVED',
    );
  }

  final String endpoint;
  final String title;
  final String simpleExplanation;
  final String? serializer;
  final String? mechanism;
  final int? fieldCount;
  final List<String> omittedFields;
  final String payloadReduction;
  final String status;
  final String measurementType;
}

/// Supabase platform egress telemetry.
@immutable
class SupabaseEgress {
  const SupabaseEgress({
    this.historicalPeriodEgress = '36.13 GB',
    this.postRemediationEgress = 'NOT MEASURED',
    this.dailyRate = 'NOT MEASURED',
    this.reason = '',
    this.measurementType = 'NOT MEASURED',
  });

  factory SupabaseEgress.fromJson(Map<String, dynamic> json) {
    return SupabaseEgress(
      historicalPeriodEgress: json['historical_period_egress'] as String? ?? '36.13 GB',
      postRemediationEgress: json['post_remediation_egress'] as String? ?? 'NOT MEASURED',
      dailyRate: json['daily_rate'] as String? ?? 'NOT MEASURED',
      reason: json['reason'] as String? ?? '',
      measurementType: json['measurement_type'] as String? ?? 'NOT MEASURED',
    );
  }

  final String historicalPeriodEgress;
  final String postRemediationEgress;
  final String dailyRate;
  final String reason;
  final String measurementType;
}
