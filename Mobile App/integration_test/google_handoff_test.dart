import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:path_provider/path_provider.dart';
import 'package:deepshield_mobile/core/api.dart';
import 'package:deepshield_mobile/core/session.dart';
import 'package:deepshield_mobile/main.dart';

void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  testWidgets(
    'Google browser handoff returns an authenticated Android session',
    (tester) async {
      final app = AppState();
      await app.initialize();
      await app.forgetSession();
      app.language = 'en';
      await tester.pumpWidget(DeepShieldApp(state: app));
      await tester.pumpAndSettle();
      final google = find.widgetWithText(
        OutlinedButton,
        'Continue with Google',
      );
      await tester.ensureVisible(google);
      await tester.tap(google);
      await tester.runAsync(() async {
        final folder = await getExternalStorageDirectory();
        expect(folder, isNotNull);
        final verifier = await app.storage.read(key: 'google-verifier');
        final state = await app.storage.read(key: 'google-state');
        expect(verifier, isNotNull);
        expect(state, isNotNull);
        final challenge = base64UrlEncode(
          sha256.convert(utf8.encode(verifier!)).bytes,
        ).replaceAll('=', '');
        final url = Uri.parse(
          '$webBase/mobile-connect',
        ).replace(queryParameters: {'challenge': challenge, 'state': state!});
        // Public PKCE challenge/state only. Never export the verifier or session token.
        await File('${folder!.path}/google-authorize.json')
            .writeAsString(jsonEncode({'authorize_url': '$url'}));
        final deadline = DateTime.now().add(const Duration(minutes: 8));
        while (app.user == null && DateTime.now().isBefore(deadline)) {
          await Future<void>.delayed(const Duration(milliseconds: 500));
        }
        expect(
          app.user,
          isNotNull,
          reason:
              app.restoreError ??
              'Complete the real provider login and app-opening callback.',
        );
        final me = object(await app.api.get('/auth/me'));
        expect(me['id'], app.user!['id']);
        expect(app.api.token?.startsWith('dsm_'), true);
        expect(await app.storage.read(key: 'google-verifier'), isNull);
        expect(await app.storage.read(key: 'google-state'), isNull);
        await File('${folder.path}/google-session-proof.json').writeAsString(
          jsonEncode({
            'authenticated': true,
            'user_id': me['id'],
            'role': me['role'],
            'needs_profile': me['needs_profile'],
            'pkce_state_cleared': true,
            'api_origin': apiBase,
          }),
        );
      });
      await tester.pumpAndSettle();
      await binding.convertFlutterSurfaceToImage();
      await tester.pumpAndSettle();
      await binding.takeScreenshot('android-google-session');
    },
    timeout: const Timeout(Duration(minutes: 10)),
  );
}
