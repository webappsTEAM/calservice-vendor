import 'package:flutter/material.dart';

import '../../../../core/theme/app_theme.dart';

class JobCardSkeleton extends StatefulWidget {
  const JobCardSkeleton({super.key});

  @override
  State<JobCardSkeleton> createState() => _JobCardSkeletonState();
}

class _JobCardSkeletonState extends State<JobCardSkeleton>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _opacity;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    )..repeat(reverse: true);
    _opacity = Tween<double>(begin: 0.35, end: 0.8).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _opacity,
      builder: (context, child) {
        return Opacity(
          opacity: _opacity.value,
          child: Container(
            margin: const EdgeInsets.only(bottom: AppSpacing.md),
            padding: const EdgeInsets.all(AppSpacing.md),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(AppRadius.cardStandard),
              border: Border.all(color: AppColors.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Top row: category & status
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    _box(width: 110, height: 16),
                    _box(width: 75, height: 20),
                  ],
                ),
                const SizedBox(height: AppSpacing.md),
                // Second row: ID & amount
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    _box(width: 80, height: 18),
                    _box(width: 70, height: 22),
                  ],
                ),
                const SizedBox(height: AppSpacing.sm),
                // Title
                _box(width: double.infinity, height: 16),
                const SizedBox(height: 6),
                _box(width: 180, height: 14),
                const SizedBox(height: AppSpacing.md),
                // Date & location
                _box(width: 140, height: 13),
                const SizedBox(height: 6),
                _box(width: 220, height: 13),
                const SizedBox(height: AppSpacing.md),
                const Divider(height: 1),
                const SizedBox(height: AppSpacing.sm),
                // Customer row
                Row(
                  children: [
                    Container(
                      width: 28,
                      height: 28,
                      decoration: const BoxDecoration(
                        color: Color(0xFFE2E8F0),
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: AppSpacing.sm),
                    _box(width: 100, height: 14),
                    const Spacer(),
                    _box(width: 28, height: 28, radius: 14),
                    const SizedBox(width: 6),
                    _box(width: 28, height: 28, radius: 14),
                  ],
                ),
                const SizedBox(height: AppSpacing.sm),
                // Action buttons
                Row(
                  children: [
                    Expanded(child: _box(width: double.infinity, height: 38)),
                    const SizedBox(width: AppSpacing.sm),
                    Expanded(child: _box(width: double.infinity, height: 38)),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _box({
    required double width,
    required double height,
    double radius = 6,
  }) {
    return Container(
      width: width,
      height: height,
      decoration: BoxDecoration(
        color: const Color(0xFFE2E8F0),
        borderRadius: BorderRadius.circular(radius),
      ),
    );
  }
}
