import 'package:flutter_test/flutter_test.dart';
import 'package:multiview_desktop/src/impl/cascade_close_service_impl.dart';

void main() {
  group('CascadeCloseService', () {
    late CascadeCloseService service;

    setUp(() => service = CascadeCloseService());

    test('waitWindow returns true when window completes', () async {
      service.attachWindow(1);
      service.completeWindow(1);

      expect(await service.waitWindow(1), isTrue);
    });

    test('waitWindow returns true when id was never attached', () async {
      expect(await service.waitWindow(42), isTrue);
    });

    test('abort only affects the given id — parallel waits stay pending', () async {
      service.attachWindow(1);
      service.attachWindow(2);

      final wait1 = service.waitWindow(1);
      final wait2 = service.waitWindow(2);
      service.abort(1);

      expect(await wait1, isFalse);
      service.completeWindow(2);
      expect(await wait2, isTrue);
    });

    test('abort is no-op for missing or already completed id', () async {
      service.attachWindow(1);
      service.completeWindow(1);
      service.abort(1);
      service.abort(99);

      expect(await service.waitWindow(1), isTrue);
    });

    test('abortIds completes only the listed ids', () async {
      service.attachWindow(10);
      service.attachWindow(11);
      service.attachWindow(20);
      final wait10 = service.waitWindow(10);
      final wait11 = service.waitWindow(11);
      final wait20 = service.waitWindow(20);

      service.abortIds([10, 11]);

      expect(await wait10, isFalse);
      expect(await wait11, isFalse);
      service.completeWindow(20);
      expect(await wait20, isTrue);
    });

    test('detachWindow removes completer without completing', () async {
      service.attachWindow(5);
      service.detachWindow(5);

      expect(await service.waitWindow(5), isTrue);
    });

    test('attachWindow is idempotent for the same id', () async {
      service.attachWindow(1);
      service.attachWindow(1);
      service.completeWindow(1);
      expect(await service.waitWindow(1), isTrue);
    });

    test('clear completes pending waits with false then drops them', () async {
      service.attachWindow(1);
      final wait = service.waitWindow(1);
      service.clear();
      expect(await wait, isFalse);
      expect(await service.waitWindow(1), isTrue);
    });

    test('completeWindow is a no-op for unattached ids', () async {
      service.completeWindow(99);
      expect(await service.waitWindow(99), isTrue);
    });

    test('waitWindow detaches after completion so a later wait is fresh', () async {
      service.attachWindow(1);
      service.completeWindow(1);
      expect(await service.waitWindow(1), isTrue);

      // Completer was detached; without re-attach, wait returns true immediately.
      expect(await service.waitWindow(1), isTrue);

      service.attachWindow(1);
      final pending = service.waitWindow(1);
      service.completeWindow(1);
      expect(await pending, isTrue);
    });
  });
}
