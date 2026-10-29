import 'dart:async';

import 'package:deepshield_mobile/core/api.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

class SlowAdapter implements HttpClientAdapter {
  bool cancelled = false;
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<List<int>>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    cancelFuture?.then((_) => cancelled = true);
    await Completer<void>().future;
    return ResponseBody.fromString('{}', 200);
  }

  @override
  void close({bool force = false}) {}
}

void main() {
  test('A stalled session check is cancelled without treating the user as authenticated', () async {
    final adapter = SlowAdapter();
    final dio = Dio()..httpClientAdapter = adapter;
    final api = Api(client: dio)..token = 'dsm_test_session';
    await expectLater(
      api.get('/auth/me', timeout: const Duration(milliseconds: 30)),
      throwsA(isA<ApiFailure>()),
    );
    await Future<void>.delayed(Duration.zero);
    expect(adapter.cancelled, isTrue);
    expect(
      api.token,
      'dsm_test_session',
    ); // A timeout is not an expired credential.
  });
}
