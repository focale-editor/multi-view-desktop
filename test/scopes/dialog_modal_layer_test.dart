import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:multiview_desktop/multiview_desktop.dart';
import 'package:multiview_desktop/src/view_root.dart';
import 'package:multiview_desktop/src/ffi/ffi_bridge.dart';

void main() {
  FfiBridge.instanceForTesting = RecordingFfiBridge();
  group('DialogModalLayer', () {
    testWidgets('modal barrier blocks input until the dialog closes', (
      tester,
    ) async {
      final ValueNotifier<List<DialogInfo>> notifier = ValueNotifier([]);
      addTearDown(notifier.dispose);
      int taps = 0;
      await tester.pumpWidget(
        MaterialApp(
          home: DialogScope(
            notifier: notifier,
            child: DialogModalLayer(
              child: TextButton(
                onPressed: () => taps++,
                child: const Text('Parent action'),
              ),
            ),
          ),
        ),
      );
      await tester.tap(find.text('Parent action'));
      await tester.pumpAndSettle();
      expect(taps, 1);
      notifier.value = [(id: 1, isModal: true)];
      await tester.pumpAndSettle();
      await tester.tap(find.text('Parent action'), warnIfMissed: false);
      await tester.pumpAndSettle();
      expect(taps, 1);
      notifier.value = [];
      await tester.pumpAndSettle();
      await tester.tap(find.text('Parent action'));
      await tester.pumpAndSettle();
      expect(taps, 2);
    });
    testWidgets('shows scrim when modal dialog is open', (tester) async {
      final notifier = ValueNotifier<List<DialogInfo>>([]);
      addTearDown(notifier.dispose);

      await tester.pumpWidget(
        MaterialApp(
          home: DialogScope(
            notifier: notifier,
            child: const DialogModalLayer(child: Text('content')),
          ),
        ),
      );
      await tester.pump();

      final barrier = find.descendant(
        of: find.byType(DialogModalLayer),
        matching: find.byType(AnimatedOpacity),
      );
      expect(tester.widget<AnimatedOpacity>(barrier).opacity, 0.0);

      notifier.value = [(id: 1, isModal: true)];
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 150));

      expect(tester.widget<AnimatedOpacity>(barrier).opacity, 1.0);
    });

    testWidgets('does not show scrim for non-modal dialog by default', (
      tester,
    ) async {
      final notifier = ValueNotifier<List<DialogInfo>>([
        (id: 1, isModal: false),
      ]);
      addTearDown(notifier.dispose);

      await tester.pumpWidget(
        MaterialApp(
          home: DialogScope(
            notifier: notifier,
            child: const DialogModalLayer(child: Text('content')),
          ),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 150));

      final barrier = find.descendant(
        of: find.byType(DialogModalLayer),
        matching: find.byType(AnimatedOpacity),
      );
      expect(tester.widget<AnimatedOpacity>(barrier).opacity, 0.0);
    });

    testWidgets(
      'shows scrim for non-modal dialog when showBarrierForNotModalDialog is true',
      (tester) async {
        final notifier = ValueNotifier<List<DialogInfo>>([
          (id: 1, isModal: false),
        ]);
        addTearDown(notifier.dispose);

        await tester.pumpWidget(
          createMultiViewRoot(
            (context, id) => MaterialApp(
              home: DialogScope(
                notifier: notifier,
                child: const DialogModalLayer(
                  showBarrierForNotModalDialog: true,
                  child: Text('content'),
                ),
              ),
            ),
            null,
            MultiAppConfig(),
          ),
          wrapWithView: false,
        );
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 150));

        final barrier = find.descendant(
          of: find.byType(DialogModalLayer),
          matching: find.byType(AnimatedOpacity),
        );
        expect(tester.widget<AnimatedOpacity>(barrier).opacity, 1.0);
      },
    );
  });
}
