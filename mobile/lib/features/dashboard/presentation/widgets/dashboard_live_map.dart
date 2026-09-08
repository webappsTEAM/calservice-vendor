import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import '../../../../core/theme/app_theme.dart';

/// Live location & geofence radar map for the mobile technician dashboard.
///
/// Mirrors the web PortalCockpitLayout first-person site map/standby radar
/// in a compact, touch-friendly, mobile-optimized container.
class DashboardLiveMap extends StatefulWidget {
  const DashboardLiveMap({
    super.key,
    this.latitude,
    this.longitude,
    this.accuracy,
    required this.isOnline,
    required this.onRefreshLocation,
    this.isGpsLoading = false,
    this.locationError,
    this.height = 200,
  });

  final double? latitude;
  final double? longitude;
  final double? accuracy;
  final bool isOnline;
  final VoidCallback onRefreshLocation;
  final bool isGpsLoading;
  final String? locationError;
  final double height;

  @override
  State<DashboardLiveMap> createState() => _DashboardLiveMapState();
}

class _DashboardLiveMapState extends State<DashboardLiveMap> {
  late final MapController _mapController;

  // Default fallback: India centre (20.5937, 78.9629)
  static const double _defaultLat = 20.5937;
  static const double _defaultLng = 78.9629;

  @override
  void initState() {
    super.initState();
    _mapController = MapController();
  }

  @override
  void didUpdateWidget(covariant DashboardLiveMap oldWidget) {
    super.didUpdateWidget(oldWidget);
    final lat = widget.latitude;
    final lng = widget.longitude;
    if (lat != null &&
        lng != null &&
        (lat != oldWidget.latitude || lng != oldWidget.longitude)) {
      try {
        _mapController.move(LatLng(lat, lng), 15);
      } catch (_) {}
    }
  }

  @override
  void dispose() {
    _mapController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final lat = widget.latitude;
    final lng = widget.longitude;
    final hasCoords = lat != null && lng != null;
    final center = hasCoords ? LatLng(lat, lng) : const LatLng(_defaultLat, _defaultLng);
    final zoom = hasCoords ? 15.0 : 5.0;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (widget.locationError != null && widget.locationError!.isNotEmpty) ...[
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            margin: const EdgeInsets.only(bottom: AppSpacing.sm),
            decoration: BoxDecoration(
              color: const Color(0xFFFEF2F2),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: const Color(0xFFFCA5A5)),
            ),
            child: Row(
              children: [
                const Icon(Icons.location_off_rounded, size: 16, color: Color(0xFFDC2626)),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    widget.locationError!,
                    style: const TextStyle(
                      fontSize: 11.5,
                      fontWeight: FontWeight.w600,
                      color: Color(0xFF991B1B),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
        Container(
          height: widget.height,
          decoration: BoxDecoration(
            color: const Color(0xFF0F172A), // Dark slate canvas
            borderRadius: BorderRadius.circular(AppRadius.card),
            border: Border.all(color: AppColors.border),
            boxShadow: AppElevation.subtle,
          ),
          clipBehavior: Clip.antiAlias,
          child: Stack(
            children: [
              FlutterMap(
                mapController: _mapController,
                options: MapOptions(
                  initialCenter: center,
                  initialZoom: zoom,
                  minZoom: 3,
                  maxZoom: 19,
                  interactionOptions: const InteractionOptions(
                    flags: InteractiveFlag.all,
                  ),
                ),
                children: [
                  TileLayer(
                    urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                    userAgentPackageName: 'online.caldimservices.vendor',
                    maxZoom: 19,
                  ),
                  if (hasCoords) ...[
                    CircleLayer(
                      circles: [
                        CircleMarker(
                          point: LatLng(lat, lng),
                          radius: 250, // 250m geofence radar
                          useRadiusInMeter: true,
                          color: const Color(0xFF004E89).withValues(alpha: 0.18),
                          borderColor: const Color(0xFF004E89),
                          borderStrokeWidth: 1.5,
                        ),
                      ],
                    ),
                    MarkerLayer(
                      markers: [
                        Marker(
                          point: LatLng(lat, lng),
                          width: 44,
                          height: 44,
                          alignment: Alignment.center,
                          child: Stack(
                            alignment: Alignment.center,
                            children: [
                              Container(
                                width: 36,
                                height: 36,
                                decoration: BoxDecoration(
                                  shape: BoxShape.circle,
                                  color: widget.isOnline
                                      ? const Color(0xFF10B981).withValues(alpha: 0.3)
                                      : Colors.grey.withValues(alpha: 0.3),
                                ),
                              ),
                              Container(
                                width: 26,
                                height: 26,
                                decoration: BoxDecoration(
                                  shape: BoxShape.circle,
                                  color: widget.isOnline
                                      ? const Color(0xFF004E89)
                                      : const Color(0xFF64748B),
                                  border: Border.all(color: Colors.white, width: 2),
                                  boxShadow: [
                                    BoxShadow(
                                      color: Colors.black.withValues(alpha: 0.25),
                                      blurRadius: 4,
                                      offset: const Offset(0, 2),
                                    ),
                                  ],
                                ),
                                child: const Icon(
                                  Icons.navigation_rounded,
                                  size: 14,
                                  color: Colors.white,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ],
                ],
              ),

              // ── Top Status Overlay Bar ────────────────────────────────────
              Positioned(
                top: 10,
                left: 10,
                right: 10,
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.92),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: AppColors.border),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withValues(alpha: 0.08),
                            blurRadius: 4,
                          ),
                        ],
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Container(
                            width: 7,
                            height: 7,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: widget.isOnline
                                  ? const Color(0xFF10B981)
                                  : const Color(0xFF94A3B8),
                            ),
                          ),
                          const SizedBox(width: 5),
                          Text(
                            widget.isOnline ? 'GPS RADAR ACTIVE' : 'LOCATION PAUSED',
                            style: TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.w800,
                              letterSpacing: 0.5,
                              color: widget.isOnline
                                  ? const Color(0xFF065F46)
                                  : const Color(0xFF475569),
                            ),
                          ),
                        ],
                      ),
                    ),
                    if (widget.accuracy != null) ...[
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 4),
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.92),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: AppColors.border),
                        ),
                        child: Text(
                          '±${widget.accuracy!.round()}m Fix',
                          style: const TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                            fontFamily: 'monospace',
                            color: Color(0xFF004E89),
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              ),

              // ── Bottom Action Button: Locate / Refresh GPS ────────────────
              Positioned(
                bottom: 10,
                right: 10,
                child: Material(
                  color: Colors.white,
                  elevation: 2,
                  borderRadius: BorderRadius.circular(8),
                  child: InkWell(
                    onTap: widget.isGpsLoading ? null : widget.onRefreshLocation,
                    borderRadius: BorderRadius.circular(8),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          if (widget.isGpsLoading) ...[
                            const SizedBox(
                              width: 13,
                              height: 13,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            ),
                            const SizedBox(width: 6),
                          ] else ...[
                            const Icon(
                              Icons.my_location_rounded,
                              size: 14,
                              color: Color(0xFF004E89),
                            ),
                            const SizedBox(width: 5),
                          ],
                          const Text(
                            'Locate Me',
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w700,
                              color: Color(0xFF004E89),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
