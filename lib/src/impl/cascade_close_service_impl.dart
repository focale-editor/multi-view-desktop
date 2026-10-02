// Soft/force cascade waits per view id.
// Parallel trees: abort/clear for one root must not complete another root's waits.
import 'dart:async';

import 'package:multiview_desktop/src/log/mvd_log.dart';

/// Completer per view: `true` on close, `false` on `cancelCascadeClose`.
class CascadeCloseService {
  CascadeCloseService();

  // viewId -> completer: true = closed, false = cancelled (preventClose).
  final Map<int, Completer<bool>> _closeCompleters = {};

  /// Drops all pending entries. Completes them with `false` so waiters do not hang.
  void clear() {
    for (final c in _closeCompleters.values) {
      if (!c.isCompleted) c.complete(false);
    }
    _closeCompleters.clear();
  }

  /// Completes only [id] with `false`. Other cascades keep waiting.
  void abort(int id) {
    MvdLog.instance.info('close', 'CascadeCloseService.abort', {
      'realId': id,
      'pending': _closeCompleters.keys.join(','),
    });
    final completer = _closeCompleters.remove(id);
    if (completer != null && !completer.isCompleted) {
      completer.complete(false);
    }
  }

  /// Completes every id in [ids] with `false` (one subtree / parent chain).
  void abortIds(Iterable<int> ids) {
    for (final id in ids) {
      abort(id);
    }
  }

  /// Registers `id` as the next window in a cascade close sequence.
  void attachWindow(int id) {
    MvdLog.instance.info('close', 'CascadeCloseService.attach', {'realId': id});
    _closeCompleters.putIfAbsent(id, () => Completer<bool>());
  }

  /// Signals that `id` finished its soft-close cycle successfully.
  void completeWindow(int id) {
    MvdLog.instance.info('close', 'CascadeCloseService.complete', {'realId': id});
    _closeCompleters[id]?.complete(true);
  }

  /// Waits until `id` closes or the cascade is aborted; then removes its completer.
  Future<bool> waitWindow(int id) async {
    final res = await _closeCompleters[id]?.future ?? true;
    detachWindow(id);

    return res;
  }

  void detachWindow(int id) => _closeCompleters.remove(id);
}
