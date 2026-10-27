import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:deepshield_mobile/core/api.dart';
import 'package:deepshield_mobile/core/session.dart';
import 'package:deepshield_mobile/features/auth.dart';
import 'package:deepshield_mobile/features/admin.dart';
import 'package:deepshield_mobile/features/member.dart';
import 'package:deepshield_mobile/features/scans.dart';
import 'package:deepshield_mobile/features/play.dart';
import 'package:deepshield_mobile/features/live_guard.dart';
import 'package:deepshield_mobile/features/shell.dart';
import 'package:deepshield_mobile/ui/kit.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  final user = {
    'id': 1,
    'username': 'fixture',
    'display_name': 'Long display name for a small phone screen',
    'role': 'participant',
    'score': 0,
    'accuracy': 0,
    'games_played': 0,
    'total_correct': 0,
    'total_rounds_played': 0,
    'qualified_for_research': false,
  };
  final fixtures = <String, dynamic>{
    '/admin/users': [
      user,
      {...user, 'id': 2, 'role': 'admin', 'username': 'admin'},
    ],
    '/profile': {
      'user': {...user, 'rounds': 0, 'games': 0, 'qualified': false},
      'totals': {'detections': 0, 'lessons': 0, 'lesson_count': 1},
      'requirements': {'score': 5000, 'accuracy': 90},
      'detections': [],
      'rounds': [],
    },
    '/scans': [],
    '/support': [],
    '/notifications': [],
    '/extension/tokens': [],
    '/billing': {
      'plan': 'free',
      'limit': 10,
      'used': 0,
      'price_bdt': 299,
      'payment': {'number': '01815808291'},
      'requests': [],
    },
    '/profile/lessons': [],
    '/profile/course': [],
    '/game/leaderboard': [],
    '/admin/analytics': {
      'summary': {
        'members': 0,
        'active': 0,
        'detections': 0,
        'pending_reviews': 0,
      },
      'daily': [],
      'roles': [],
      'accuracy_bands': [],
      'top_members': [],
    },
    '/operations': {'subscriptions': [], 'tickets': [], 'queue': []},
    '/admin/learning': {
      'training': {
        'ready': false,
        'message': 'Replay memory is not configured.',
      },
      'samples': [],
    },
    '/admin/audit': [],
    '/dashboard/metrics': {
      'total_evaluations': 0,
      'human_accuracy': 0,
      'ai_accuracy': 0,
      'hybrid_accuracy': 0,
    },
    '/admin/records/scans': {'rows': [], 'total': 0},
    '/assessment': null,
  };
  AppState state() {
    final dio = Dio(BaseOptions(baseUrl: 'https://test.invalid/api'));
    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (r, h) {
          final key = r.path.split('?').first;
          h.resolve(
            Response(requestOptions: r, data: fixtures[key], statusCode: 200),
          );
        },
      ),
    );
    return AppState(api: Api(client: dio))
      ..user = user
      ..restoring = false;
  }

  Widget host(AppState app, Widget child) => AppScope(
    state: app,
    child: MaterialApp(
      theme: shieldTheme(app.theme == ThemeMode.dark, app.bengali),
      home: Scaffold(body: child),
    ),
  );
  test('Only trusted API media addresses can carry session headers', () {
    final api = Api();
    expect(api.media('/api/media/example'), '$apiBase/api/media/example');
    expect(
      () => api.media('https://other.example/video.mp4'),
      throwsA(isA<ApiFailure>()),
    );
    expect(() => api.media('http://evil.example'), throwsA(isA<ApiFailure>()));
  });
  testWidgets(
    'Sign-in validates input and password visibility stays under user control',
    (tester) async {
      final app = state();
      await tester.pumpWidget(host(app, const AuthPage()));
      await tester.tap(find.widgetWithText(FilledButton, 'Sign in'));
      await tester.pump();
      expect(find.textContaining('Use 2–50'), findsOneWidget);
      expect(find.text('Use at least 8 characters.'), findsOneWidget);
      await tester.enterText(
        find.byKey(const Key('password')),
        'correct horse',
      );
      expect(
        tester
            .widget<TextField>(
              find.descendant(
                of: find.byKey(const Key('password')),
                matching: find.byType(TextField),
              ),
            )
            .obscureText,
        true,
      );
      await tester.tap(find.byTooltip('Show password'));
      await tester.pump();
      expect(
        tester
            .widget<TextField>(
              find.descendant(
                of: find.byKey(const Key('password')),
                matching: find.byType(TextField),
              ),
            )
            .obscureText,
        false,
      );
    },
  );
  testWidgets(
    'Users cards preserve owner protection and remain usable at 320px',
    (tester) async {
      tester.view.physicalSize = const Size(320, 850);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final app = state()..user = {...user, 'role': 'admin'};
      await tester.pumpWidget(host(app, const UsersPage()));
      await tester.pumpAndSettle();
      expect(find.text('Owner account is protected.'), findsOneWidget);
      expect(tester.takeException(), isNull);
      await tester.enterText(find.byType(TextField), 'not-found');
      await tester.pump();
      expect(find.text('No matching accounts'), findsOneWidget);
    },
  );
  final screens = <String, Widget>{
    'home': const HomePage(),
    'guard': const LiveGuardPage(),
    'upload': const ScanPage(),
    'history': const HistoryPage(),
    'learn': const LearnPage(),
    'play': const PlayPage(),
    'leaderboard': const LeaderboardPage(),
    'support': const SupportPage(),
    'notifications': const NotificationsPage(),
    'plan': const SubscriptionPage(),
    'profile': const ProfilePage(),
    'companion': const CompanionPage(),
    'admin': const AdminOverview(),
    'operations': const OperationsPage(),
    'training': const TrainingPage(),
    'audit': const AuditPage(),
    'insights': const InsightsPage(),
    'assessment': const AssessmentPage(),
    'records': const RecordsPage(),
  };
  for (final width in [320.0, 768.0]) {
    for (final dark in [false, true]) {
      for (final bn in [false, true]) {
        testWidgets('All screens render: width=$width dark=$dark bn=$bn', (
          tester,
        ) async {
          tester.view.physicalSize = Size(width, 900);
          tester.view.devicePixelRatio = 1;
          addTearDown(tester.view.resetPhysicalSize);
          addTearDown(tester.view.resetDevicePixelRatio);
          final app = state();
          app.theme = dark ? ThemeMode.dark : ThemeMode.light;
          app.language = bn ? 'bn' : 'en';
          app.translations = object(
            jsonDecode(File('assets/copy/bn.json').readAsStringSync()),
          );
          for (final page in screens.entries) {
            await tester.pumpWidget(
              host(
                app,
                KeyedSubtree(key: ValueKey(page.key), child: page.value),
              ),
            );
            await tester.pumpAndSettle();
            expect(tester.takeException(), isNull, reason: page.key);
          }
        });
      }
    }
  }
  testWidgets(
    'Member navigation keeps every feature including Live Guard and More',
    (tester) async {
      tester.view.physicalSize = const Size(320, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final app = state();
      await tester.pumpWidget(host(app, const AppShell()));
      await tester.pumpAndSettle();
      expect(find.byType(NavigationDestination), findsNWidgets(5));
      await tester.tap(find.text('Live Guard').last);
      await tester.pumpAndSettle();
      expect(find.text('You control screen sharing'), findsOneWidget);
      final button = tester.widget<BusyButton>(find.byType(BusyButton));
      expect(button.onPressed, isNull);
      await tester.tap(find.text('More').last);
      await tester.pumpAndSettle();
      expect(find.text('Scan history'), findsOneWidget);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
    },
  );
  testWidgets('Server errors offer retry instead of an empty screen', (
    tester,
  ) async {
    final app = state();
    app.api.dio.interceptors.clear();
    app.api.dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (r, h) => h.reject(
          DioException(
            requestOptions: r,
            type: DioExceptionType.connectionError,
          ),
        ),
      ),
    );
    await tester.pumpWidget(host(app, const HistoryPage()));
    await tester.pumpAndSettle();
    expect(find.text('Try again'), findsOneWidget);
    expect(
      find.text('Could not connect to DeepShield. Please try again.'),
      findsOneWidget,
    );
  });
  testWidgets(
    'Research keeps the model hidden until the independent answer is submitted',
    (tester) async {
      final app = state();
      app.api.dio.interceptors.clear();
      app.api.dio.interceptors.add(
        InterceptorsWrapper(
          onRequest: (r, h) {
            expect(r.path, '/research/submit');
            expect(r.data['human_prediction'], 'Fake');
            h.resolve(
              Response(
                requestOptions: r,
                statusCode: 200,
                data: {
                  'human_prediction': 'Fake',
                  'ai_prediction': 'Fake',
                  'ground_truth': 'Fake',
                  'analysis': {
                    'verdict': 'Fake',
                    'confidence_percentage': 90.0,
                  },
                },
              ),
            );
          },
        ),
      );
      await tester.pumpWidget(
        host(
          app,
          const ResearchEvaluation({
            'id': 1,
            'media_url': '/api/media/fixture',
          }),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text('What does this result mean?'), findsNothing);
      await tester.tap(find.widgetWithText(FilledButton, 'Fake'));
      await tester.pump();
      final submit = find.widgetWithText(FilledButton, 'Submit evaluation');
      await tester.ensureVisible(submit);
      await tester.tap(submit);
      await tester.pumpAndSettle();
      expect(find.text('What does this result mean?'), findsOneWidget);
      expect(find.text('Back to research samples'), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );
  testWidgets(
    'Admin research reviews open the review queue rather than analytics',
    (tester) async {
      final app = state()..user = {...user, 'role': 'admin'};
      await tester.pumpWidget(host(app, const MorePage()));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Research reviews'));
      await tester.pumpAndSettle();
      expect(find.text('No samples awaiting review'), findsOneWidget);
      expect(find.text('Train & evaluate candidate'), findsNothing);
      expect(tester.takeException(), isNull);
    },
  );
}
