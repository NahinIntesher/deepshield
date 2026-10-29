import 'package:flutter/material.dart';
import 'package:lottie/lottie.dart';

enum StatusMotion { loading, scan, empty, success }

/// Bundled original artwork; no network request and no text inside the art.
/// Only waiting states loop. Respect the device's reduced-motion preference.
class StatusArt extends StatelessWidget {
  final StatusMotion kind;
  final double size;
  const StatusArt(this.kind, {super.key, this.size = 100});

  @override
  Widget build(BuildContext context) {
    final reduce = MediaQuery.disableAnimationsOf(context);
    final color = Theme.of(context).colorScheme.primary;
    return ExcludeSemantics(
      child: SizedBox.square(
        dimension: size,
        child: ColorFiltered(
          colorFilter: ColorFilter.mode(color, BlendMode.srcIn),
          child: Lottie.asset(
            'assets/motion/${kind.name}.json',
            animate: !reduce,
            repeat:
                (kind == StatusMotion.loading || kind == StatusMotion.scan) &&
                !reduce,
            controller: reduce ? const AlwaysStoppedAnimation(1.0) : null,
            fit: BoxFit.contain,
            errorBuilder: (context, error, stack) => Icon(switch (kind) {
              StatusMotion.scan => Icons.hourglass_top_rounded,
              StatusMotion.loading => Icons.hourglass_top_rounded,
              StatusMotion.empty => Icons.inbox_outlined,
              StatusMotion.success => Icons.check_circle_outline,
            }, size: size * .55),
          ),
        ),
      ),
    );
  }
}
