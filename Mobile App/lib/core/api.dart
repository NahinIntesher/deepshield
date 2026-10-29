import 'dart:convert';

import 'package:dio/dio.dart';

const apiBase = String.fromEnvironment(
  'API_BASE',
  defaultValue: 'https://api.deepshield.nahin.com.bd',
);
const webBase = 'https://deepshield.nahin.com.bd';
typedef Json = Map<String, dynamic>;
Json object(dynamic value) =>
    value is Map ? Map<String, dynamic>.from(value) : <String, dynamic>{};
List<Json> objects(dynamic value) =>
    value is List ? value.map(object).toList() : <Json>[];
double number(dynamic value) =>
    value is num ? value.toDouble() : double.tryParse('$value') ?? 0;

class ApiFailure implements Exception {
  final String message;
  final int? status;
  const ApiFailure(this.message, [this.status]);
  @override
  String toString() => message;
}

class Api {
  final Dio dio;
  String? token;
  void Function()? onExpired;
  Api({Dio? client})
    : dio =
          client ??
          Dio(
            BaseOptions(
              baseUrl: '$apiBase/api',
              connectTimeout: const Duration(seconds: 45),
              receiveTimeout: const Duration(minutes: 4),
              sendTimeout: const Duration(minutes: 3),
            ),
          );
  Map<String, String> get headers =>
      token == null ? {} : {'Authorization': 'Bearer $token'};
  Future<dynamic> get(String path, {Duration? timeout}) =>
      request(path, timeout: timeout);
  Future<dynamic> post(String path, [dynamic body]) =>
      request(path, method: 'POST', body: body ?? {});
  Future<dynamic> patch(String path, dynamic body) =>
      request(path, method: 'PATCH', body: body);
  Future<dynamic> put(String path, dynamic body) =>
      request(path, method: 'PUT', body: body);
  Future<dynamic> delete(String path, [dynamic body]) =>
      request(path, method: 'DELETE', body: body ?? {});
  Future<dynamic> request(
    String path, {
    String method = 'GET',
    dynamic body,
    ProgressCallback? onSendProgress,
    CancelToken? cancelToken,
    ResponseType? responseType,
    Duration? timeout,
  }) async {
    final timedCancel = timeout == null ? null : CancelToken();
    try {
      final pending = dio.request(
        path,
        data: body,
        options: Options(
          method: method,
          headers: headers,
          responseType: responseType,
        ),
        onSendProgress: onSendProgress,
        cancelToken: cancelToken ?? timedCancel,
      );
      final response = timeout == null
          ? await pending
          : await pending.timeout(
              timeout,
              onTimeout: () {
                timedCancel?.cancel('Session check timed out');
                throw const ApiFailure(
                  'The server is taking longer than usual. Please reconnect.',
                );
              },
            );
      return response.data;
    } on DioException catch (error) {
      if (error.response?.statusCode == 401 && !path.contains('/login')) {
        onExpired?.call();
      }
      final detail = object(error.response?.data)['detail'];
      if (detail is String) {
        throw ApiFailure(detail, error.response?.statusCode);
      }
      if (detail is List) {
        throw ApiFailure(
          detail.map((e) => object(e)['msg'] ?? '').join('\n'),
          422,
        );
      }
      if (CancelToken.isCancel(error)) {
        throw const ApiFailure('Upload cancelled.');
      }
      throw ApiFailure(
        error.response == null
            ? 'Could not connect to DeepShield. Please try again.'
            : 'Could not complete the request. Try again.',
        error.response?.statusCode,
      );
    }
  }

  String media(String value) {
    if (value.startsWith('/')) return '$apiBase$value';
    final uri = Uri.tryParse(value);
    if (uri?.scheme == 'https' && uri?.host == Uri.parse(apiBase).host) {
      return value;
    }
    throw const ApiFailure('This media address is not supported.');
  }

  Future<Json> upload(
    String path,
    MultipartFile file, {
    Json fields = const {},
    ProgressCallback? progress,
    CancelToken? cancelToken,
  }) async => object(
    await request(
      path,
      method: 'POST',
      body: FormData.fromMap({...fields, 'file': file}),
      onSendProgress: progress,
      cancelToken: cancelToken,
    ),
  );
  static String normalizeImage(String value) =>
      value.startsWith('data:') ? value.split(',').last : value;
  static String errorText(Object error) => error is ApiFailure
      ? error.message
      : 'Something went wrong. Please try again.';
  static String pretty(dynamic value) =>
      const JsonEncoder.withIndent('  ').convert(value);
}
