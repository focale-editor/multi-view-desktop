import 'package:flutter/widgets.dart';
import 'package:multiview_desktop/multiview_desktop.dart';

import 'e2e_context_store.dart';

/// Registers this subtree's [BuildContext] in [store] under the current view id.
///
/// Wrap window/dialog roots only when the E2E harness is enabled.
class E2eHost extends StatefulWidget {
  const E2eHost({super.key, required this.store, required this.child});

  final E2eContextStore store;
  final Widget child;

  @override
  State<E2eHost> createState() => _E2eHostState();
}

class _E2eHostState extends State<E2eHost> {
  int? _viewId;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final id = MultiViewDesktop.of(context).id;
    if (_viewId != null && _viewId != id) {
      widget.store.unregister(_viewId!, context);
    }
    _viewId = id;
    widget.store.register(id, context);
  }

  @override
  void dispose() {
    if (_viewId != null) {
      widget.store.unregister(_viewId!, context);
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => widget.child;
}
