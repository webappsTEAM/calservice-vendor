import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../../core/location/navigation_launcher.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../shared/widgets/workforce_avatar.dart';
import '../../domain/job.dart';

/// Customer row inside a job card featuring the circular avatar/initial,
/// customer name, and quick Call and Directions icon buttons.
class JobCustomerRow extends StatelessWidget {
  const JobCustomerRow({
    super.key,
    required this.job,
  });

  final Job job;

  Future<void> _callCustomer(BuildContext context) async {
    final phone = job.phone;
    if (phone == null || phone.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Customer phone number not available.')),
      );
      return;
    }
    final uri = Uri(scheme: 'tel', path: phone.trim());
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri);
    } else if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not initiate call to $phone')),
      );
    }
  }

  Future<void> _navigateCustomer(BuildContext context) async {
    if (job.hasCoordinates) {
      final launched = await launchNavigation(
        destinationLat: job.latitude!,
        destinationLon: job.longitude!,
      );
      if (!launched && context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not open navigation application.')),
        );
      }
    } else if (job.address != null && job.address!.trim().isNotEmpty) {
      final query = Uri.encodeComponent(job.address!.trim());
      final uri = Uri.parse('https://www.google.com/maps/search/?api=1&query=$query');
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri, mode: LaunchMode.externalApplication);
      } else if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not open map search for address.')),
        );
      }
    } else if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Location coordinates or address not available.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final name = (job.customerName != null && job.customerName!.trim().isNotEmpty)
        ? job.customerName!.trim()
        : 'Customer';
    final initial = name.isNotEmpty ? name[0].toUpperCase() : 'C';

    final hasPhone = job.phone != null && job.phone!.trim().isNotEmpty;
    final hasLocation = job.hasCoordinates || (job.address != null && job.address!.trim().isNotEmpty);

    return Row(
      children: [
        WorkforceAvatar(
          imageUrl: null,
          name: name,
          initial: initial,
          radius: 14,
          fontSize: 12,
          backgroundColor: const Color(0xFFF1F5F9),
          foregroundColor: const Color(0xFF1E293B),
          borderColor: const Color(0xFFCBD5E1),
          borderWidth: 1,
        ),
        const SizedBox(width: AppSpacing.sm),
        Expanded(
          child: Text(
            name,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              fontSize: 12.5,
              fontWeight: FontWeight.w700,
              color: Color(0xFF1E293B),
            ),
          ),
        ),
        // Quick Action Icon Buttons
        if (hasPhone) ...[
          _QuickIconButton(
            icon: Icons.phone_rounded,
            color: AppColors.peacockBlue,
            tooltip: 'Call customer',
            onTap: () => _callCustomer(context),
          ),
          const SizedBox(width: 6),
        ],
        if (hasLocation)
          _QuickIconButton(
            icon: Icons.directions_rounded,
            color: const Color(0xFF059669),
            tooltip: 'Navigate',
            onTap: () => _navigateCustomer(context),
          ),
      ],
    );
  }
}

class _QuickIconButton extends StatelessWidget {
  const _QuickIconButton({
    required this.icon,
    required this.color,
    required this.tooltip,
    required this.onTap,
  });

  final IconData icon;
  final Color color;
  final String tooltip;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppRadius.pill),
        child: Container(
          width: 32,
          height: 32,
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.1),
            shape: BoxShape.circle,
            border: Border.all(color: color.withValues(alpha: 0.25), width: 0.8),
          ),
          alignment: Alignment.center,
          child: Icon(icon, size: 16, color: color),
        ),
      ),
    );
  }
}
