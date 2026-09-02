import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// Maps a real service/category name (from [CatalogService.name] or
/// [CatalogCategory.name]) to a representative icon and a peacock-palette
/// accent color, for the Services & Skills visual pass.
///
/// The backend also sends an `icon` field (a Lucide icon-name string, e.g.
/// `'Wrench'`) but it's effectively always the same default value in
/// practice — matching by the service/category *name* instead produces far
/// more visual variety from data that's actually differentiated. Falls back
/// to a generic tools icon for anything unrecognised, so a new backend
/// category never renders blank.
class ServiceVisual {
  const ServiceVisual(this.icon, this.color);

  final IconData icon;
  final Color color;
}

ServiceVisual serviceVisualFor(String name) {
  final key = name.toLowerCase();
  for (final (keywords, visual) in _matchers) {
    if (keywords.any(key.contains)) return visual;
  }
  return ServiceVisual(Icons.handyman_rounded, AppColors.textMuted);
}

final List<(List<String>, ServiceVisual)> _matchers = [
  (['plumb', 'pipe', 'drain', 'sanitat'], ServiceVisual(Icons.plumbing_rounded, const Color(0xFF2563EB))),
  (['electric', 'wiring'], ServiceVisual(Icons.electrical_services_rounded, const Color(0xFFD97706))),
  (
    ['ac ', 'a/c', 'hvac', 'air condition', 'refrigerat', 'cooling'],
    ServiceVisual(Icons.ac_unit_rounded, const Color(0xFF0D9488)),
  ),
  (['clean'], ServiceVisual(Icons.cleaning_services_rounded, const Color(0xFF059669))),
  (['paint', 'wall'], ServiceVisual(Icons.format_paint_rounded, const Color(0xFF7C3AED))),
  (['carpent', 'wood', 'furniture'], ServiceVisual(Icons.carpenter_rounded, const Color(0xFF92400E))),
  (['appliance', 'kitchen'], ServiceVisual(Icons.kitchen_rounded, const Color(0xFF2563EB))),
  (['pest'], ServiceVisual(Icons.pest_control_rounded, const Color(0xFF65A30D))),
  (
    ['security', 'cctv', 'camera', 'surveillance'],
    ServiceVisual(Icons.security_rounded, const Color(0xFF1E293B)),
  ),
  (['garden', 'landscap', 'lawn'], ServiceVisual(Icons.yard_rounded, const Color(0xFF059669))),
  (['roof'], ServiceVisual(Icons.roofing_rounded, const Color(0xFFB91C1C))),
  (['solar'], ServiceVisual(Icons.solar_power_rounded, const Color(0xFFD97706))),
  (['generator', 'power backup'], ServiceVisual(Icons.bolt_rounded, const Color(0xFFD97706))),
];
