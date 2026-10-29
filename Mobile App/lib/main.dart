import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter/services.dart' show rootBundle;

import 'core/session.dart';
import 'ui/kit.dart';
import 'features/auth.dart';
import 'features/shell.dart';

SemanticsHandle? webSemanticsHandle;

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  LicenseRegistry.addLicense(() async* {
    for (final font in ['Quicksand', 'BalooDa2']) {
      yield LicenseEntryWithLineBreaks([
        font,
      ], await rootBundle.loadString('assets/fonts/OFL-$font.txt'));
    }
  });
  if (kIsWeb) webSemanticsHandle = SemanticsBinding.instance.ensureSemantics();
  final state = AppState();
  runApp(DeepShieldApp(state: state));
  await state.initialize();
}

class DeepShieldApp extends StatefulWidget {
  final AppState state;
  const DeepShieldApp({super.key, required this.state});
  @override
  State<DeepShieldApp> createState() => _DeepShieldAppState();
}

class _DeepShieldAppState extends State<DeepShieldApp> {
  final navigatorKey = GlobalKey<NavigatorState>();
  AppState get state => widget.state;
  bool hadSession = false;
  @override
  void initState() {
    super.initState();
    hadSession = state.user != null;
    state.addListener(sessionChanged);
  }

  void sessionChanged() {
    final signedIn = state.user != null;
    if (hadSession && !signedIn) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) {
          navigatorKey.currentState?.popUntil((route) => route.isFirst);
        }
      });
    }
    hadSession = signedIn;
  }

  @override
  void dispose() {
    state.removeListener(sessionChanged);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AppScope(
    state: state,
    child: AnimatedBuilder(
      animation: state,
      builder: (context, _) => MaterialApp(
        title: 'DeepShield',
        navigatorKey: navigatorKey,
        debugShowCheckedModeBanner: false,
        theme: shieldTheme(false, state.bengali),
        darkTheme: shieldTheme(true, state.bengali),
        themeMode: state.theme,
        home: state.restoring
            ? const Scaffold(
                body: Center(child: StatusArt(StatusMotion.loading, size: 64)),
              )
            : state.restoreError != null && state.api.token != null
            ? Scaffold(
                body: PageBody(
                  children: [
                    const Brand(),
                    Notice(state.t(state.restoreError!), error: true),
                    BusyButton(
                      state.t('Reconnect', 'আবার সংযোগ করুন'),
                      onPressed: state.retrySession,
                    ),
                    TextButton(
                      onPressed: state.forgetSession,
                      child: Text(
                        state.t('Return to sign in', 'লগইন পেজে ফিরুন'),
                      ),
                    ),
                  ],
                ),
              )
            : state.user == null
            ? const AuthPage()
            : state.user?['needs_profile'] == true
            ? const AuthPage(onboarding: true)
            : const AppShell(),
      ),
    ),
  );
}
