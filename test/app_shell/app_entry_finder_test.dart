import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:multiview_desktop/src/app_shell/app_shell_registry.dart';
import 'package:multiview_desktop/src/shared_entry_app.dart';

void main() {
  group('AppEntryPointFinder', () {
    testWidgets('findOutermostUpstream reads MaterialApp theme and locale', (tester) async {
      final registry = AppShellRegistry();
      addTearDown(registry.dispose);

      late BuildContext innerContext;

      await tester.pumpWidget(
        MainAppShellCapture(
          registry: registry,
          child: MaterialApp(
            themeMode: ThemeMode.dark,
            locale: const Locale('es'),
            home: Builder(
              builder: (context) {
                innerContext = context;
                return const SizedBox();
              },
            ),
          ),
        ),
      );
      await tester.pump();
      await tester.pump();

      final upstream = AppEntryPointFinder.findOutermostUpstream(innerContext);
      expect(upstream?.themeMode, ThemeMode.dark);
      expect(upstream?.locale, const Locale('es'));
    });

    testWidgets('findShallowestInSubtree finds nested MaterialApp', (tester) async {
      final registry = AppShellRegistry();
      addTearDown(registry.dispose);

      late Element rootElement;

      await tester.pumpWidget(
        MainAppShellCapture(
          registry: registry,
          child: Builder(
            builder: (context) {
              rootElement = context as Element;
              return MaterialApp(
                themeMode: ThemeMode.light,
                home: const SizedBox(),
              );
            },
          ),
        ),
      );
      await tester.pump();
      await tester.pump();

      final snapshot = AppEntryPointFinder.findShallowestInSubtree(rootElement);
      expect(snapshot?.themeMode, ThemeMode.light);
    });

    testWidgets('MainAppShellCapture syncs registry when themeMode changes', (tester) async {
      final registry = AppShellRegistry();
      addTearDown(registry.dispose);

      await tester.pumpWidget(
        _ThemeToggleHost(
          registry: registry,
          initialMode: ThemeMode.light,
        ),
      );
      await tester.pump();
      await tester.pump();

      expect(registry.snapshot?.themeMode, ThemeMode.light);

      await tester.tap(find.byType(ElevatedButton));
      await tester.pump();
      await tester.pump();

      expect(registry.snapshot?.themeMode, ThemeMode.dark);
    });

    testWidgets('MainAppShellCapture does not walk the subtree on every frame', (tester) async {
      final registry = AppShellRegistry();
      addTearDown(registry.dispose);
      final visits = ValueNotifier<int>(0);
      addTearDown(visits.dispose);
      final ticks = ValueNotifier<int>(0);
      addTearDown(ticks.dispose);

      await tester.pumpWidget(
        MainAppShellCapture(
          registry: registry,
          child: _VisitCounter(
            visits: visits,
            child: MaterialApp(
              home: ValueListenableBuilder<int>(
                valueListenable: ticks,
                builder: (context, value, _) => Text('$value', textDirection: TextDirection.ltr),
              ),
            ),
          ),
        ),
      );
      await tester.pump();
      final visitsAfterCapture = visits.value;

      for (var frame = 0; frame < 10; frame++) {
        ticks.value++;
        await tester.pump();
      }

      expect(registry.snapshot, isNotNull);
      expect(visits.value, visitsAfterCapture);
    });

    testWidgets('MainAppShellCapture finds an entry widget that replaced the previous one', (tester) async {
      final registry = AppShellRegistry();
      addTearDown(registry.dispose);
      final mode = ValueNotifier<ThemeMode>(ThemeMode.light);
      addTearDown(mode.dispose);

      await tester.pumpWidget(
        MainAppShellCapture(
          registry: registry,
          child: ValueListenableBuilder<ThemeMode>(
            valueListenable: mode,
            // A new key mounts a new entry element instead of updating the old one.
            builder: (context, value, _) => MaterialApp(
              key: ValueKey(value),
              themeMode: value,
              home: const SizedBox(),
            ),
          ),
        ),
      );
      await tester.pump();
      expect(registry.snapshot?.themeMode, ThemeMode.light);

      mode.value = ThemeMode.dark;
      await tester.pump();
      await tester.pump();

      expect(registry.snapshot?.themeMode, ThemeMode.dark);
    });
  });
}

/// Counts how often a subtree walk passes through this widget.
class _VisitCounter extends StatelessWidget {
  const _VisitCounter({required this.visits, required this.child});

  final ValueNotifier<int> visits;
  final Widget child;

  @override
  StatelessElement createElement() => _VisitCounterElement(this);

  @override
  Widget build(BuildContext context) => child;
}

class _VisitCounterElement extends StatelessElement {
  _VisitCounterElement(_VisitCounter super.widget);

  @override
  void visitChildren(ElementVisitor visitor) {
    (widget as _VisitCounter).visits.value++;
    super.visitChildren(visitor);
  }
}

class _ThemeToggleHost extends StatefulWidget {
  const _ThemeToggleHost({required this.registry, required this.initialMode});

  final AppShellRegistry registry;
  final ThemeMode initialMode;

  @override
  State<_ThemeToggleHost> createState() => _ThemeToggleHostState();
}

class _ThemeToggleHostState extends State<_ThemeToggleHost> {
  late ThemeMode _mode;

  @override
  void initState() {
    super.initState();
    _mode = widget.initialMode;
  }

  @override
  Widget build(BuildContext context) {
    return MainAppShellCapture(
      registry: widget.registry,
      child: MaterialApp(
        themeMode: _mode,
        home: Scaffold(
          body: ElevatedButton(
            onPressed: () => setState(() => _mode = ThemeMode.dark),
            child: const Text('toggle'),
          ),
        ),
      ),
    );
  }
}
