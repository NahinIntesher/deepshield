import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

import 'api.dart';

class NativeGuard {
  static const channel = MethodChannel('deepshield/live_guard');
  static bool get supported =>
      !kIsWeb && defaultTargetPlatform == TargetPlatform.android;
  static Future<Json> status() async => supported
      ? object(await channel.invokeMethod('status'))
      : {
          'running': false,
          'overlayAllowed': false,
          'notificationsAllowed': false,
        };
  static Future<void> stop() async {
    if (supported) {
      try {
        await channel.invokeMethod('stop');
      } on MissingPluginException {
        /* Unit tests have no Android service. */
      }
    }
  }

  static Future<bool> permission(String kind) async =>
      await channel.invokeMethod<bool>(kind) ?? false;
  static Future<bool> start(Json settings) async =>
      await channel.invokeMethod<bool>('start', settings) ?? false;
  static Future<void> command(String action) async {
    await channel.invokeMethod(action);
  }
}
