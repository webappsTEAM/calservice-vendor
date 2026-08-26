import 'package:flutter/material.dart';

import '../../core/theme/app_motion.dart';

/// A restrained entrance: a short fade paired with a small upward settle.
///
/// Exists so that section entrances (Employee Home, Admin dashboard) cannot
/// be hand-rolled with an ungated `AnimationController` and silently bypass
/// the user's "Reduce Animations & Transitions" preference. When reduced
/// motion is on, this renders its child immediately with no animation at
/// all — not a faster animation.
///
/// Movement is intentionally tiny (8px) and there is no bounce, scale or
/// overshoot, per the Classic Enterprise motion rules.
class AppFadeIn extends StatelessWidget {
  const AppFadeIn({
    super.key,
    required this.child,
    this.index = 0,
    this.duration,
  });

  final Widget child;

  /// Position in a staggered group. Later items start slightly later.
  final int index;

  final Duration? duration;

  @override
  Widget build(BuildContext context) {
    if (AppMotion.isReduced) {
      return child;
    }

    final effective = duration ?? AppMotion.normal;
    final delay = AppMotion.staggerFor(index);

    return _DelayedFadeIn(
      delay: delay,
      duration: effective,
      child: child,
    );
  }
}

class _DelayedFadeIn extends StatefulWidget {
  const _DelayedFadeIn({
    required this.delay,
    required this.duration,
    required this.child,
  });

  final Duration delay;
  final Duration duration;
  final Widget child;

  @override
  State<_DelayedFadeIn> createState() => _DelayedFadeInState();
}

class _DelayedFadeInState extends State<_DelayedFadeIn> {
  bool _visible = false;

  @override
  void initState() {
    super.initState();
    if (widget.delay == Duration.zero) {
      // Still needs one frame so the implicit animation has a starting
      // value to animate away from.
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) setState(() => _visible = true);
      });
    } else {
      Future<void>.delayed(widget.delay, () {
        if (mounted) setState(() => _visible = true);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedSlide(
      offset: _visible ? Offset.zero : const Offset(0, 0.02),
      duration: widget.duration,
      curve: AppMotion.curve,
      child: AnimatedOpacity(
        opacity: _visible ? 1 : 0,
        duration: widget.duration,
        curve: AppMotion.curve,
        child: widget.child,
      ),
    );
  }
}
