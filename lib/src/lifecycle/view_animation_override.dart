import 'package:multiview_desktop/src/view_animation_config.dart';

// ignore: depend_on_referenced_packages
import 'package:meta/meta.dart';

/// One-shot animation parameters for a view, consumed by [ViewAnimator].
@internal
class ViewAnimationOverride {
  const ViewAnimationOverride({required this.type, this.settings});

  final ViewAnimationType type;
  final AnimationSettings? settings;

  bool get isEmpty => settings == null || settings!.isEmpty;

  @override
  int get hashCode => type.hashCode;

  @override
  bool operator ==(Object other) {
    return other is ViewAnimationOverride && other.type == type;
  }
}
