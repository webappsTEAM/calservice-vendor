import 'package:flutter_test/flutter_test.dart';

import 'package:mobile/features/admin/domain/admin_monitoring.dart';

void main() {
  group('AdminMonitoringData Domain Tests', () {
    test('parses full backend JSON response correctly', () {
      final sampleJson = <String, dynamic>{
        'plain_english_summary': {
          'system_health_status': 'Healthy & Optimal',
          'speed_headline': '99.88% of data requests are served instantly from RAM.',
          'storage_headline': 'Total database size is 170 MB.',
          'optimizations_headline': '4 network guardrails are active.',
          'index_utilization_headline': '584 of 923 search shortcuts are actively accelerating queries.',
        },
        'database_health': {
          'engine': 'postgresql',
          'database_size': '170 MB',
          'stats_reset_timestamp': '2026-08-01T00:00:00Z',
          'database_cache_efficiency': {
            'blocks_hit': 1500000,
            'blocks_read': 1200,
            'hit_ratio_percent': 99.92,
            'status': 'OPTIMAL',
            'measurement_type': 'ACTUAL',
          },
          'index_cache_efficiency': {
            'blocks_hit': 800000,
            'blocks_read': 300,
            'hit_ratio_percent': 99.96,
            'status': 'OPTIMAL',
            'measurement_type': 'ACTUAL',
          },
          'billing_cost': 'Not available from PostgreSQL telemetry.',
          'measurement_type': 'ACTUAL',
        },
        'analytics': {
          'total_indexes': 923,
          'used_indexes': 584,
          'unused_indexes': 339,
          'utilization_rate_percent': 63.3,
          'category_storage_bytes': {
            'Logs & Audit History': 72771584,
            'Notifications & Messaging': 20971520,
            'Core Workforce & Personnel': 15728640,
            'Jobs & Service Requests': 18874368,
            'Financial & Billing': 12582912,
            'Other System Tables': 37748736,
          },
          'top_used_indexes': [
            {
              'schema': 'public',
              'table_name': 'workforce_servicerequest',
              'index_name': 'idx_sr_status_company',
              'index_bytes': 24576,
              'index_size': '24 kB',
              'cumulative_scans_since_stats_reset': 4520,
              'tuples_read': 4520,
              'tuples_fetched': 4520,
              'index_definition': 'CREATE INDEX idx_sr_status_company ON workforce_servicerequest (company_id, status);',
              'status': 'USED',
              'note': 'Actively serving queries',
              'measurement_type': 'ACTUAL',
            }
          ],
        },
        'index_health': {
          'total_monitored_indexes': 923,
          'filtered_count': 923,
          'page': 1,
          'page_size': 15,
          'total_pages': 62,
          'indexes': [
            {
              'schema': 'public',
              'table_name': 'workforce_servicerequest',
              'index_name': 'idx_sr_status_company',
              'index_bytes': 24576,
              'index_size': '24 kB',
              'cumulative_scans_since_stats_reset': 4520,
              'tuples_read': 4520,
              'tuples_fetched': 4520,
              'index_definition': 'CREATE INDEX idx_sr_status_company ON workforce_servicerequest (company_id, status);',
              'status': 'USED',
              'note': 'Actively serving queries',
              'measurement_type': 'ACTUAL',
            }
          ],
          'all_tables': ['workforce_servicerequest', 'workforce_employee'],
          'table_storage': [
            {
              'table_name': 'workforce_servicerequest',
              'data_size': '45 MB',
              'index_size': '12 MB',
              'total_size': '57 MB',
              'total_bytes': 59768832,
              'data_bytes': 47185920,
              'index_bytes': 12582912,
              'measurement_type': 'ACTUAL',
            }
          ],
          'note': 'Index scans reflect cumulative PostgreSQL engine scans.',
        },
        'api_traffic_optimizations': [
          {
            'endpoint': 'GET /api/workforce/jobs/ (Admin)',
            'title': 'Admin Job List Optimization',
            'simple_explanation': 'Sends only essential job summary data (18 fields).',
            'serializer': 'WorkforceJobListSerializer',
            'field_count': 18,
            'omitted_fields': ['cart_data', 'payments'],
            'payload_reduction': 'Eliminated large nested objects',
            'status': 'IMPLEMENTED',
            'measurement_type': 'CODE-DERIVED',
          }
        ],
        'supabase_egress': {
          'historical_period_egress': '36.13 GB',
          'post_remediation_egress': 'NOT MEASURED',
          'daily_rate': 'NOT MEASURED',
          'reason': 'Requires 48-hour observation window on Supabase dashboard.',
          'measurement_type': 'NOT MEASURED',
        },
      };

      final data = AdminMonitoringData.fromJson(sampleJson);

      // Plain English
      expect(data.plainEnglishSummary.systemHealthStatus, 'Healthy & Optimal');
      expect(data.plainEnglishSummary.speedHeadline, contains('99.88%'));

      // Database Health
      expect(data.databaseHealth.engine, 'postgresql');
      expect(data.databaseHealth.databaseSize, '170 MB');
      expect(data.databaseHealth.databaseCacheEfficiency.formattedRatio, '99.92%');
      expect(data.databaseHealth.databaseCacheEfficiency.status, 'OPTIMAL');

      // Analytics
      expect(data.analytics.totalIndexes, 923);
      expect(data.analytics.usedIndexes, 584);
      expect(data.analytics.unusedIndexes, 339);
      expect(data.analytics.utilizationRatePercent, 63.3);
      expect(data.analytics.categoryStorageBytes['Logs & Audit History'], 72771584);
      expect(data.analytics.totalCategoryBytes, greaterThan(0));

      // Indexes
      expect(data.indexHealth.indexes.length, 1);
      final idx = data.indexHealth.indexes.first;
      expect(idx.tableName, 'workforce_servicerequest');
      expect(idx.indexName, 'idx_sr_status_company');
      expect(idx.isUsed, isTrue);
      expect(idx.cumulativeScans, 4520);
      expect(idx.indexDefinition, contains('CREATE INDEX'));

      // Table Storage
      expect(data.indexHealth.tableStorage.length, 1);
      final tbl = data.indexHealth.tableStorage.first;
      expect(tbl.tableName, 'workforce_servicerequest');
      expect(tbl.totalSize, '57 MB');

      // Optimizations
      expect(data.apiTrafficOptimizations.length, 1);
      final opt = data.apiTrafficOptimizations.first;
      expect(opt.title, 'Admin Job List Optimization');
      expect(opt.status, 'IMPLEMENTED');
      expect(opt.measurementType, 'CODE-DERIVED');

      // Egress
      expect(data.supabaseEgress.historicalPeriodEgress, '36.13 GB');
      expect(data.supabaseEgress.postRemediationEgress, 'NOT MEASURED');
    });

    test('handles empty or missing JSON fields gracefully with safe fallbacks', () {
      final data = AdminMonitoringData.fromJson({});

      expect(data.plainEnglishSummary.systemHealthStatus, 'Healthy & Optimal');
      expect(data.databaseHealth.engine, 'postgresql');
      expect(data.databaseHealth.databaseSize, 'N/A');
      expect(data.databaseHealth.databaseCacheEfficiency.blocksHit, 0);
      expect(data.analytics.totalIndexes, 0);
      expect(data.analytics.categoryStorageBytes, isEmpty);
      expect(data.indexHealth.indexes, isEmpty);
      expect(data.indexHealth.allTables, isEmpty);
      expect(data.apiTrafficOptimizations, isEmpty);
      expect(data.supabaseEgress.postRemediationEgress, 'NOT MEASURED');
    });

    test('parses double and decimal values in numeric fields without type cast errors', () {
      final doubleJson = <String, dynamic>{
        'database_health': {
          'database_cache_efficiency': {
            'blocks_hit': 1500000.0,
            'blocks_read': 1200.0,
            'hit_ratio_percent': 99.92,
          },
          'index_cache_efficiency': {
            'blocks_hit': 800000.0,
            'blocks_read': 300.0,
            'hit_ratio_percent': 99.96,
          },
        },
        'analytics': {
          'total_indexes': 923.0,
          'used_indexes': 584.0,
          'unused_indexes': 339.0,
          'utilization_rate_percent': 63.3,
          'category_storage_bytes': {
            'Logs & Audit History': 72771584.0,
            'Notifications': '20971520',
          },
        },
        'index_health': {
          'total_monitored_indexes': 923.0,
          'filtered_count': 923.0,
          'page': 1.0,
          'page_size': 15.0,
          'total_pages': 62.0,
          'indexes': [
            {
              'table_name': 'test_table',
              'index_name': 'idx_test',
              'index_bytes': 24576.0,
              'cumulative_scans_since_stats_reset': 4520.0,
              'tuples_read': 100.0,
              'tuples_fetched': 90.0,
            }
          ],
          'table_storage': [
            {
              'table_name': 'test_table',
              'total_bytes': 59768832.0,
              'data_bytes': 47185920.0,
              'index_bytes': 12582912.0,
            }
          ],
        },
        'api_traffic_optimizations': [
          {
            'endpoint': 'GET /test/',
            'title': 'Test Optimization',
            'simple_explanation': 'Test',
            'field_count': 18.0,
          }
        ],
      };

      final data = AdminMonitoringData.fromJson(doubleJson);

      expect(data.databaseHealth.databaseCacheEfficiency.blocksHit, 1500000);
      expect(data.databaseHealth.databaseCacheEfficiency.blocksRead, 1200);
      expect(data.databaseHealth.indexCacheEfficiency.blocksHit, 800000);
      expect(data.analytics.totalIndexes, 923);
      expect(data.analytics.usedIndexes, 584);
      expect(data.analytics.categoryStorageBytes['Logs & Audit History'], 72771584);
      expect(data.analytics.categoryStorageBytes['Notifications'], 20971520);
      expect(data.indexHealth.totalMonitoredIndexes, 923);
      expect(data.indexHealth.page, 1);
      expect(data.indexHealth.pageSize, 15);
      expect(data.indexHealth.totalPages, 62);
      expect(data.indexHealth.indexes.first.cumulativeScans, 4520);
      expect(data.indexHealth.indexes.first.indexBytes, 24576);
      expect(data.indexHealth.tableStorage.first.totalBytes, 59768832);
      expect(data.apiTrafficOptimizations.first.fieldCount, 18);
    });
  });
}
