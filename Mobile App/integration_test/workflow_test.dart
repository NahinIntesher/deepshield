import 'package:dio/dio.dart';
import 'package:deepshield_mobile/core/api.dart';
import 'package:deepshield_mobile/features/scans.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:deepshield_mobile/core/session.dart';
import 'package:deepshield_mobile/main.dart';
import 'package:deepshield_mobile/features/admin.dart';
import 'package:deepshield_mobile/ui/kit.dart';

void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  testWidgets(
    'Isolated Android login, learning, session and admin boundaries',
    (tester) async {
      final app = AppState();
      await app.initialize();
      await app.forgetSession();
      await tester.pumpWidget(DeepShieldApp(state: app));
      await tester.pumpAndSettle();
      await tester.enterText(
        find.byKey(const Key('username')),
        'ui-participant',
      );
      await tester.enterText(
        find.byKey(const Key('password')),
        const String.fromEnvironment('TEST_PASSWORD'),
      );
      await tester.ensureVisible(find.widgetWithText(FilledButton, 'Sign in'));
      await tester.tap(find.widgetWithText(FilledButton, 'Sign in'));
      for (int i = 0; i < 30 && app.user == null; i++) {
        await tester.pump(const Duration(seconds: 1));
      }
      expect(app.user?['username'], 'ui-participant');
      expect(app.admin, false);
      await tester.pumpAndSettle();
      expect(find.text('DeepShield'), findsOneWidget);
      expect(tester.takeException(), isNull);
      await binding.convertFlutterSurfaceToImage();
      await tester.pumpAndSettle();
      await binding.takeScreenshot('android-member-home');
      await tester.tap(find.text('Learn').last);
      await tester.pumpAndSettle(const Duration(seconds: 1));
      expect(tester.takeException(), isNull);
      await app.api.get('/profile/lessons');
      await app.api.get('/scans');
      await app.api.get('/billing');
      try {
        await app.api.get('/admin/users');
        fail('Participant accessed admin users');
      } catch (e) {
        expect('$e', contains('Administrator access required'));
      }
      app.toggleLanguage();
      app.toggleTheme();
      await tester.pumpAndSettle();
      await binding.takeScreenshot('android-learning-bn-dark');
      await app.logout();
      await tester.pumpAndSettle();
      expect(app.user, isNull);
      await app.login(
        'ui-admin',
        const String.fromEnvironment('TEST_PASSWORD'),
        admin: true,
      );
      await tester.pumpAndSettle();
      expect(app.admin, true);
      await tester.pumpWidget(
        AppScope(
          state: app,
          child: MaterialApp(
            theme: shieldTheme(true, true),
            home: const Scaffold(body: UsersPage()),
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      await binding.takeScreenshot('android-admin-users');
      await app.logout();
      await app.login('ui-signup',const String.fromEnvironment('TEST_PASSWORD'));
      final saved = object(await app.api.get('/profile/detections/1'));
      expect(objects(saved['frame_details']),isNotEmpty);
      await tester.pumpWidget(AppScope(state:app,child:MaterialApp(theme:shieldTheme(true,true),home:Scaffold(body:ResultPage(saved)))));
      await tester.pumpAndSettle();expect(tester.takeException(),isNull);
      await binding.takeScreenshot('android-recorded-model-result');
      await tester.drag(find.byType(SingleChildScrollView).first,const Offset(0,-650));await tester.pumpAndSettle();
      await binding.takeScreenshot('android-recorded-heatmap');
      // Exercise upload -> queue -> original model -> saved result using a provided library video.
      final presets=objects(await app.api.get('/detector/presets'));expect(presets,isNotEmpty);
      final media=presets.first['thumbnail'].toString().replaceFirst('/api','');
      final bytes=await app.api.request(media,responseType:ResponseType.bytes);
      final scan=await app.api.upload('/scans/upload',MultipartFile.fromBytes(List<int>.from(bytes),filename:'android-workflow.mp4'));
      Json job={};
      for(int i=0;i<120;i++){
        job=object(await app.api.get('/scans/${scan['id']}'));
        if(['completed','failed'].contains(job['state']))break;
        await Future<void>.delayed(const Duration(seconds:3));
      }
      expect(job['state'],'completed',reason:'${job['message']}');
      expect(object(job['result'])['model_id'],isNotNull);
      await app.api.delete('/scans/${scan['id']}');
      await app.logout();
      await tester.pumpWidget(const SizedBox());
      app.dispose();
    },
  );
}
