import 'dart:async';
import 'dart:convert';
import 'dart:math';

import 'package:app_links/app_links.dart';
import 'package:crypto/crypto.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:url_launcher/url_launcher.dart';

import 'api.dart';
import 'guard.dart';

class AppState extends ChangeNotifier {
  final Api api;
  final FlutterSecureStorage storage;
  SharedPreferences? preferences;
  Json? user;
  String language = 'en';
  ThemeMode theme = ThemeMode.light;
  Map<String, dynamic> translations = {};
  bool restoring = true;
  String? restoreError;
  StreamSubscription<Uri>? _links;
  AppState({Api? api, FlutterSecureStorage? storage})
    : api = api ?? Api(),
      storage = storage ?? const FlutterSecureStorage();
  bool get admin => user?['role'] == 'admin';
  bool get bengali => language == 'bn';
  String t(String en, [String? bn]) {
    if (!bengali) return en;
    if (bn != null) return polish(bn);
    if (translations[en] is String) return polish(translations[en]);
    if (translations[en.toLowerCase()] is String) {
      return polish(translations[en.toLowerCase()]);
    }
    final pattern = RegExp(r'^(.+) — (Real|Fake) \(model prediction\)$')
        .firstMatch(en);
    if (pattern != null) {
      return '${pattern[1]} — ${pattern[2] == 'Real' ? 'আসল' : 'নকল'} (মডেলের ফলাফল)';
    }
    return polish(en);
  }

  String polish(String text) {
    for (final entry in object(translations['__professionalCopy']).entries) {
      text = text.replaceAll(entry.key, '${entry.value}');
    }
    return text;
  }

  Future<void> initialize() async {
    try {
      await restoreSettingsAndSession();
    } catch (error) {
      restoreError = Api.errorText(error);
    } finally {
      restoring = false;
      notifyListeners();
    }
  }

  Future<void> restoreSettingsAndSession() async {
    preferences = await SharedPreferences.getInstance();
    language = preferences!.getString('language') ?? 'en';
    theme = preferences!.getBool('dark') == true
        ? ThemeMode.dark
        : ThemeMode.light;
    translations = object(
      jsonDecode(await rootBundle.loadString('assets/copy/bn.json')),
    );
    api.onExpired = () {
      unawaited(NativeGuard.stop());
      api.token = null;
      user = null;
      restoreError = null;
      unawaited(storage.delete(key: 'session'));
      notifyListeners();
    };
    if (!kIsWeb) {
      final links = AppLinks();
      _links = links.uriLinkStream.listen((uri) => unawaited(handleLink(uri)));
      final initial = await links.getInitialLink();
      if (initial != null) await handleLink(initial);
    }
    try {
      api.token = await storage.read(key: 'session');
      if (api.token != null) await refresh();
    } catch (error) {
      restoreError = Api.errorText(error);
    }
    restoring = false;
    notifyListeners();
  }

  Future<void> refresh() async {
    user = object(await api.get('/auth/me'));
    restoreError = null;
    notifyListeners();
  }

  Future<void> retrySession() async {
    restoring = true;
    notifyListeners();
    try {
      await refresh();
    } catch (e) {
      restoreError = Api.errorText(e);
    } finally {
      restoring = false;
      notifyListeners();
    }
  }

  Future<void> login(String name, String password, {bool admin = false}) async {
    final response = object(
      await api.post(
        admin ? '/auth/mobile/admin/login' : '/auth/mobile/login',
        {'username': name.trim(), 'password': password},
      ),
    );
    await acceptSession(response);
  }

  Future<void> acceptSession(Json response) async {
    final token = response['token'];
    if (token is! String || !token.startsWith('dsm_')) {
      throw const ApiFailure('Invalid sign-in response.');
    }
    await storage.write(key: 'session', value: token);
    api.token = token;
    user = object(response['user']);
    restoreError = null;
    notifyListeners();
  }

  Future<bool> signup(Json fields) async {
    final result = object(
      await api.post('/auth/mobile/signup', {...fields, 'language': language}),
    );
    if (result['verification_required'] == true) return true;
    await login(fields['username'], fields['password']);
    return false;
  }

  Future<void> forgetSession() async {
    await NativeGuard.stop();
    await storage.delete(key: 'session');
    api.token = null;
    user = null;
    restoreError = null;
    notifyListeners();
  }

  Future<void> logout() async {
    await NativeGuard.stop();
    await api.post('/auth/mobile/logout');
    await storage.delete(key: 'session');
    api.token = null;
    user = null;
    restoreError = null;
    notifyListeners();
  }

  void toggleLanguage() {
    language = bengali ? 'en' : 'bn';
    preferences?.setString('language', language);
    notifyListeners();
  }

  void toggleTheme() {
    theme = theme == ThemeMode.dark ? ThemeMode.light : ThemeMode.dark;
    preferences?.setBool('dark', theme == ThemeMode.dark);
    notifyListeners();
  }

  String _random() => base64UrlEncode(
    List<int>.generate(32, (_) => Random.secure().nextInt(256)),
  ).replaceAll('=', '');
  Future<void> google() async {
    if (kIsWeb) {
      throw ApiFailure(
        t(
          'Google sign-in is available in the Android app. Use your username in this browser preview.',
          'Google দিয়ে লগইন Android অ্যাপে পাওয়া যাবে। এই browser preview-তে ইউজারনেম দিয়ে লগইন করুন।',
        ),
      );
    }
    final verifier = _random(), state = _random();
    await storage.write(key: 'google-verifier', value: verifier);
    await storage.write(key: 'google-state', value: state);
    final challenge = base64UrlEncode(
      sha256.convert(utf8.encode(verifier)).bytes,
    ).replaceAll('=', '');
    final url = Uri.parse('$webBase/mobile-connect')
        .replace(queryParameters: {'challenge': challenge, 'state': state});
    if (!await launchUrl(url, mode: LaunchMode.externalApplication)) {
      throw const ApiFailure('Could not open your browser.');
    }
  }

  Future<void> handleLink(Uri uri) async {
    if (uri.scheme != 'deepshield' || uri.host != 'auth') return;
    try {
      final verifier = await storage.read(key: 'google-verifier'),
          state = await storage.read(key: 'google-state');
      if (verifier == null ||
          state == null ||
          uri.queryParameters['state'] != state) {
        throw const ApiFailure('Sign-in expired. Please try again.');
      }
      final code = uri.queryParameters['code'];
      if (code == null) {
        throw const ApiFailure('Sign-in expired. Please try again.');
      }
      final result = object(
        await api.post('/auth/mobile/exchange', {
          'code': code,
          'verifier': verifier,
        }),
      );
      await acceptSession(result);
      await storage.delete(key: 'google-verifier');
      await storage.delete(key: 'google-state');
    } catch (error) {
      restoreError = Api.errorText(error);
      notifyListeners();
    }
  }

  @override
  void dispose() {
    _links?.cancel();
    super.dispose();
  }
}

class AppScope extends InheritedNotifier<AppState> {
  const AppScope({super.key, required AppState state, required super.child})
    : super(notifier: state);
  static AppState of(BuildContext context) =>
      context.dependOnInheritedWidgetOfExactType<AppScope>()!.notifier!;
}
