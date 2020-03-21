# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Tests for L{twisted.internet.asyncioreactor}.
"""
import gc

from twisted.trial.unittest import SynchronousTestCase
from .reactormixins import ReactorBuilder

try:
    from twisted.internet.asyncioreactor import AsyncioSelectorReactor
    import asyncio
except ImportError:
    AsyncioSelectorReactor = None
    skipReason = "Requires asyncio."



class AsyncioSelectorReactorTests(ReactorBuilder, SynchronousTestCase):
    """
    L{AsyncioSelectorReactor} tests.
    """
    if AsyncioSelectorReactor is None:
        skip = skipReason


    def test_defaultEventLoopFromGlobalPolicy(self):
        """
        L{AsyncioSelectorReactor} wraps the global policy's event loop
        by default.  This ensures that L{asyncio.Future}s and
        coroutines created by library code that uses
        L{asyncio.get_event_loop} are bound to the same loop.
        """
        reactor = AsyncioSelectorReactor()
        future = asyncio.Future()
        result = []

        def completed(future):
            result.append(future.result())
            reactor.stop()

        future.add_done_callback(completed)
        future.set_result(True)

        self.assertEqual(result, [])
        self.runReactor(reactor, timeout=1)
        self.assertEqual(result, [True])


    def test_delayedCallResetToLater(self):
        """
        L{DelayedCall.reset()} properly reschedules timer to later time
        """
        reactor = AsyncioSelectorReactor()

        timer_called_at = [None]

        def on_timer():
            timer_called_at[0] = reactor.seconds()

        start_time = reactor.seconds()
        dc = reactor.callLater(0, on_timer)
        dc.reset(0.5)
        reactor.callLater(1, reactor.stop)
        reactor.run()

        self.assertIsNotNone(timer_called_at[0])
        self.assertGreater(timer_called_at[0] - start_time, 0.4)


    def test_delayedCallResetToEarlier(self):
        """
        L{DelayedCall.reset()} properly reschedules timer to earlier time
        """
        reactor = AsyncioSelectorReactor()

        timer_called_at = [None]

        def on_timer():
            timer_called_at[0] = reactor.seconds()

        start_time = reactor.seconds()
        dc = reactor.callLater(0.5, on_timer)
        dc.reset(0)
        reactor.callLater(1, reactor.stop)

        import io
        from contextlib import redirect_stderr
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            reactor.run()

        self.assertEqual(stderr.getvalue(), '')
        self.assertIsNotNone(timer_called_at[0])
        self.assertLess(timer_called_at[0] - start_time, 0.4)


    def test_noCycleReferencesInCallLater(self):
        """
        L{AsyncioSelectorReactor.callLater()} doesn't leave cyclic references
        """
        gc_was_enabled = gc.isenabled()
        gc.disable()
        try:
            objects_before = len(gc.get_objects())
            timer_count = 1000

            reactor = AsyncioSelectorReactor()
            for _ in range(timer_count):
                reactor.callLater(0, lambda: None)
            reactor.runUntilCurrent()

            objects_after = len(gc.get_objects())
            self.assertLess((objects_after - objects_before) / timer_count, 1)
        finally:
            if gc_was_enabled:
                gc.enable()
