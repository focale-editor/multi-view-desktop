import 'package:flutter/widgets.dart';

/// Maps public view ids to a [BuildContext] from that view's widget tree.
///
/// Populated by [E2eHost]; consumed by injectable E2E handlers (dialogs, etc.).
class E2eContextStore {
  final Map<int, BuildContext> _contexts = {};

  void register(int viewId, BuildContext context) {
    _contexts[viewId] = context;
  }

  void unregister(int viewId, BuildContext context) {
    if (_contexts[viewId] == context) {
      _contexts.remove(viewId);
    }
  }

  BuildContext? operator [](int viewId) => _contexts[viewId];

  BuildContext require(int viewId) {
    final ctx = _contexts[viewId];
    if (ctx == null || !ctx.mounted) {
      throw StateError('No mounted BuildContext for viewId=$viewId');
    }
    return ctx;
  }

  List<int> get registeredViewIds => _contexts.keys.toList(growable: false);
}
