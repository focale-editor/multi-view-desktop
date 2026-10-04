import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:multiview_desktop_example/l10n/example_localizations.dart';
import 'package:multiview_desktop_example/routing/go_router_config.dart';

/// Checks the example's localized secondary-window navigation.
void main() {
  for (final Locale locale in ExampleLocalizations.supportedLocales) {
    testWidgets(
      'GoRouter opens and returns from an item in ${locale.languageCode}',
      (tester) async {
        final GoRouter router = createDemoGoRouter();
        addTearDown(router.dispose);
        final ExampleLocalizations strings = ExampleLocalizations(locale);
        await tester.pumpWidget(
          MaterialApp.router(
            routerConfig: router,
            locale: locale,
            localizationsDelegates: exampleLocalizationDelegates(),
            supportedLocales: ExampleLocalizations.supportedLocales,
          ),
        );
        await tester.pumpAndSettle();
        expect(find.text(strings.goBrowseTitle), findsOneWidget);
        await tester.tap(find.text(strings.nextRoute));
        await tester.pumpAndSettle();
        expect(find.text(strings.goItemTitle), findsOneWidget);
        await tester.tap(find.text(strings.backRoute));
        await tester.pumpAndSettle();
        expect(find.text(strings.goBrowseTitle), findsOneWidget);
        expect(tester.takeException(), isNull);
      },
    );
  }
}
