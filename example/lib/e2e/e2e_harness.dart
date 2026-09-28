import 'dart:async';
import 'dart:convert';
import 'dart:io';

/// One RPC invocation from the Python (or other) driver.
class E2eRequest {
  E2eRequest({required this.method, required this.params});

  final String method;
  final Map<String, dynamic> params;

  T? optional<T>(String key) {
    final value = params[key];
    if (value == null) return null;
    return value as T;
  }

  T require<T>(String key) {
    final value = params[key];
    if (value == null) {
      throw ArgumentError('Missing required param "$key" for method "$method"');
    }
    return value as T;
  }
}

/// Handler for a single RPC method. Logic lives outside the server.
typedef E2eHandler = FutureOr<Object?> Function(E2eRequest request);

/// Optional surface-layer harness: HTTP JSON RPC, handlers injected by the app.
///
/// Not part of `multiview_desktop` core. Enable only from example / test entry.
class E2eHarness {
  E2eHarness({
    required Map<String, E2eHandler> handlers,
    this.port = 9876,
    InternetAddress? host,
    void Function(String message)? onLog,
  }) : host = host ?? InternetAddress.loopbackIPv4,
       _handlers = Map<String, E2eHandler>.unmodifiable(handlers),
       _log = onLog ?? ((m) => stdout.writeln('[MVD-E2E] $m'));

  final Map<String, E2eHandler> _handlers;
  final int port;
  final InternetAddress host;
  final void Function(String message) _log;

  HttpServer? _server;

  /// Registered method names (for `list_methods` / debugging).
  List<String> get methods => _handlers.keys.toList()..sort();

  Future<void> start() async {
    if (_server != null) return;
    _server = await HttpServer.bind(host, port);
    _log('listening on http://${host.address}:$port');
    _server!.listen(_onRequest);
  }

  Future<void> stop() async {
    await _server?.close(force: true);
    _server = null;
  }

  Future<void> _onRequest(HttpRequest request) async {
    // CORS-friendly for local tooling.
    request.response.headers
      ..set('Access-Control-Allow-Origin', '*')
      ..set('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
      ..set('Access-Control-Allow-Headers', 'Content-Type');

    if (request.method == 'OPTIONS') {
      request.response.statusCode = HttpStatus.noContent;
      await request.response.close();
      return;
    }

    try {
      if (request.method == 'GET' && request.uri.path == '/health') {
        await _writeJson(request.response, {
          'ok': true,
          'methods': methods,
        });
        return;
      }

      if (request.method != 'POST' || request.uri.path != '/rpc') {
        request.response.statusCode = HttpStatus.notFound;
        await _writeJson(request.response, {
          'ok': false,
          'error': 'Use POST /rpc or GET /health',
        });
        return;
      }

      final body = await utf8.decoder.bind(request).join();
      final decoded = body.isEmpty
          ? <String, dynamic>{}
          : jsonDecode(body) as Map<String, dynamic>;
      final method = decoded['method'] as String?;
      if (method == null || method.isEmpty) {
        throw ArgumentError('JSON body must include "method"');
      }
      final params = Map<String, dynamic>.from(
        (decoded['params'] as Map?)?.cast<String, dynamic>() ?? const {},
      );

      if (method == 'list_methods') {
        await _writeJson(request.response, {'ok': true, 'result': methods});
        return;
      }

      final handler = _handlers[method];
      if (handler == null) {
        throw StateError('Unknown method "$method". Known: $methods');
      }

      _log('← $method $params');
      final result = await handler(E2eRequest(method: method, params: params));
      _log('→ $method ok');
      await _writeJson(request.response, {'ok': true, 'result': result});
    } catch (e, st) {
      _log('error: $e\n$st');
      request.response.statusCode = HttpStatus.internalServerError;
      await _writeJson(request.response, {
        'ok': false,
        'error': e.toString(),
      });
    }
  }

  Future<void> _writeJson(HttpResponse response, Map<String, Object?> body) async {
    response.headers.contentType = ContentType.json;
    response.write(jsonEncode(body));
    await response.close();
  }
}

/// Reads `--dart-define=MVD_E2E=true` and optional `MVD_E2E_PORT`.
bool e2eEnabledFromEnvironment() {
  const flag = bool.fromEnvironment('MVD_E2E', defaultValue: false);
  return flag;
}

int e2ePortFromEnvironment({int fallback = 9876}) {
  const raw = String.fromEnvironment('MVD_E2E_PORT', defaultValue: '');
  if (raw.isEmpty) return fallback;
  return int.tryParse(raw) ?? fallback;
}

/// Starts harness when enabled; returns `null` if disabled.
///
/// [handlers] are supplied by the app (surface layer), not hard-coded here.
Future<E2eHarness?> maybeStartE2eHarness({
  required Map<String, E2eHandler> handlers,
  int? port,
  void Function(String message)? onLog,
}) async {
  if (!e2eEnabledFromEnvironment()) return null;
  final harness = E2eHarness(
    handlers: handlers,
    port: port ?? e2ePortFromEnvironment(),
    onLog: onLog,
  );
  await harness.start();
  return harness;
}
