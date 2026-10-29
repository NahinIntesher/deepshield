import 'package:deepshield_mobile/ui/kit.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lottie/lottie.dart';

void main() {
  test(
    'Every bundled animation decodes with vector layers and no remote images',
    () async {
      TestWidgetsFlutterBinding.ensureInitialized();
      for (final kind in StatusMotion.values) {
        final composition = await AssetLottie('assets/motion/${kind.name}.json')
            .load();
        expect(composition.layers, isNotEmpty);
        expect(composition.images, isEmpty);
        expect(composition.duration.inSeconds, inInclusiveRange(1, 4));
      }
    },
  );

  testWidgets('Reduced motion is static and only waiting states repeat', (
    tester,
  ) async {
    for (final reduced in [false, true]) {
      for (final dark in [false, true]) {
        await tester.pumpWidget(
          MaterialApp(
            theme: shieldTheme(dark, false),
            home: MediaQuery(
              data: MediaQueryData(disableAnimations: reduced),
              child: const Scaffold(
                body: Column(
                  children: [
                    StatusArt(StatusMotion.loading),
                    StatusArt(StatusMotion.scan),
                    StatusArt(StatusMotion.empty),
                    StatusArt(StatusMotion.success),
                  ],
                ),
              ),
            ),
          ),
        );
        final animations = tester
            .widgetList<LottieBuilder>(find.byType(LottieBuilder))
            .toList();
        expect(animations.length, 4);
        expect(animations.first.repeat, !reduced);
        expect(animations[1].repeat, !reduced);
        expect(animations.skip(2).every((a) => a.repeat == false), isTrue);
        for (final animation in animations) {
          expect(animation.animate, !reduced);
          if (reduced) expect(animation.controller!.value, 1.0);
        }
        await tester.pump(const Duration(milliseconds: 100));
        expect(tester.takeException(), isNull);
      }
    }
    await tester.pumpWidget(const SizedBox.shrink());
  });
}
