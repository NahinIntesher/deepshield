// Visual review helper: flutter test tool/status_art_preview_test.dart --update-goldens
import 'package:deepshield_mobile/ui/kit.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lottie/lottie.dart';

void main() {
  testWidgets('Render bundled motion artwork in both themes', (tester) async {
    tester.view.physicalSize = const Size(390, 660);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.runAsync(() async {
      for (final name in ['Quicksand', 'BalooDa2']) {
        await (FontLoader(
          name,
        )..addFont(rootBundle.load('assets/fonts/$name.ttf'))).load();
      }
      for (final kind in StatusMotion.values) {
        await AssetLottie('assets/motion/${kind.name}.json').load();
      }
    });
    for (final dark in [false, true]) {
      await tester.pumpWidget(
        MaterialApp(
          theme: shieldTheme(dark, false),
          home: MediaQuery(
            data: const MediaQueryData(disableAnimations: true),
            child: Scaffold(
              body: Padding(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SizedBox(height: 12),
                    const Brand(),
                    const SizedBox(height: 20),
                    const Panel(
                      child: Row(
                        children: [
                          StatusArt(StatusMotion.scan, size: 110),
                          SizedBox(width: 16),
                          Expanded(child: Text('Analyzing video…')),
                        ],
                      ),
                    ),
                    const SizedBox(height: 16),
                    const EmptyState(
                      'No scans yet',
                      detail: 'Your scans will appear here.',
                    ),
                    const SizedBox(height: 16),
                    const Panel(
                      child: Row(
                        children: [
                          StatusArt(StatusMotion.success, size: 88),
                          SizedBox(width: 16),
                          Expanded(child: Text('Challenge complete')),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
      await expectLater(
        find.byType(Scaffold),
        matchesGoldenFile('goldens/motion-${dark ? 'dark' : 'light'}.png'),
      );
    }
  });
}
