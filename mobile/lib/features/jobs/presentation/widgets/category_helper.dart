import 'package:flutter/material.dart';

class CategoryInfo {
  const CategoryInfo({
    required this.name,
    required this.icon,
  });

  final String name;
  final IconData icon;
}

/// Standard categories mapped to clean Material icons.
const List<CategoryInfo> kStandardServiceCategories = [
  CategoryInfo(name: 'Electrical', icon: Icons.bolt_rounded),
  CategoryInfo(name: 'AC & Appliances', icon: Icons.ac_unit_rounded),
  CategoryInfo(name: 'Plumbing', icon: Icons.water_drop_rounded),
  CategoryInfo(name: 'Locks & Carpentry', icon: Icons.handyman_rounded),
  CategoryInfo(name: 'Cleaning', icon: Icons.cleaning_services_rounded),
  CategoryInfo(name: 'Painting', icon: Icons.format_paint_rounded),
  CategoryInfo(name: 'Automotive', icon: Icons.directions_car_rounded),
  CategoryInfo(name: 'Pest Control', icon: Icons.pest_control_rounded),
];

/// Resolves a clean Material icon based on category or service name string.
IconData iconForCategory(String? category) {
  if (category == null || category.trim().isEmpty) {
    return Icons.handyman_rounded;
  }
  final lower = category.toLowerCase();
  if (lower.contains('electr') || lower.contains('wiring') || lower.contains('circuit')) {
    return Icons.bolt_rounded;
  }
  if (lower.contains('ac') ||
      lower.contains('air condition') ||
      lower.contains('appliance') ||
      lower.contains('hvac') ||
      lower.contains('refrigerat') ||
      lower.contains('cooling')) {
    return Icons.ac_unit_rounded;
  }
  if (lower.contains('plumb') ||
      lower.contains('pipe') ||
      lower.contains('drain') ||
      lower.contains('water') ||
      lower.contains('leak') ||
      lower.contains('faucet')) {
    return Icons.water_drop_rounded;
  }
  if (lower.contains('lock') ||
      lower.contains('carpent') ||
      lower.contains('door') ||
      lower.contains('wood') ||
      lower.contains('furniture') ||
      lower.contains('handyman')) {
    return Icons.handyman_rounded;
  }
  if (lower.contains('clean') ||
      lower.contains('wash') ||
      lower.contains('sanit') ||
      lower.contains('maid') ||
      lower.contains('housekeep')) {
    return Icons.cleaning_services_rounded;
  }
  if (lower.contains('paint') || lower.contains('wall') || lower.contains('polish')) {
    return Icons.format_paint_rounded;
  }
  if (lower.contains('auto') ||
      lower.contains('car') ||
      lower.contains('vehicle') ||
      lower.contains('mechanic')) {
    return Icons.directions_car_rounded;
  }
  if (lower.contains('pest') || lower.contains('termite') || lower.contains('insect')) {
    return Icons.pest_control_rounded;
  }
  if (lower.contains('roof') ||
      lower.contains('construct') ||
      lower.contains('mason') ||
      lower.contains('renovat')) {
    return Icons.home_repair_service_rounded;
  }
  if (lower.contains('logistic') || lower.contains('deliver') || lower.contains('courier')) {
    return Icons.local_shipping_rounded;
  }
  return Icons.handyman_rounded;
}
