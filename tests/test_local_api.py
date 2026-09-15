import json
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.utils.local_api import (
    LocalApiError,
    LocalApiUnauthorized,
    _dechunk,
    _read_response,
    _status_payload,
)


def feeder(*chunks):
    """Fake blocking read(): yields the supplied chunks, then b'' (EOF)."""
    queue = list(chunks)

    def read(_n):
        return queue.pop(0) if queue else b""

    return read


class TestResponseFraming(unittest.TestCase):
    """A body split across reads must still be assembled (real Local API behaviour)."""

    def test_headers_then_body_separately(self):
        head = b"HTTP/1.1 401 Unauthorized\r\nContent-Length: 5\r\n\r\n"
        status, reason, body = _read_response(feeder(head, b"nope!"), time.monotonic() + 2)
        self.assertEqual((status, reason, body), (401, "Unauthorized", b"nope!"))

    def test_content_length_body_split_in_pieces(self):
        # body is exactly b'{"a":1}' (7 bytes); a surplus chunk must be discarded
        head = b"HTTP/1.1 200 OK\r\nContent-Length: 7\r\n\r\n"
        status, _, body = _read_response(feeder(head + b'{"a"', b":1}", b"surplus"), time.monotonic() + 2)
        self.assertEqual(status, 200)
        self.assertEqual(body, b'{"a":1}')
        self.assertEqual(json.loads(body.decode()), {"a": 1})

    def test_chunked_body_split_across_reads(self):
        head = b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n"
        # chunk data is exactly b'{"a":1}' (7 bytes), then the terminating 0-chunk
        chunks = [head + b'7\r\n{"a', b'":1}\r\n', b"0\r\n\r\n"]
        status, _, body = _read_response(feeder(*chunks), time.monotonic() + 2)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body.decode()), {"a": 1})

    def test_dechunk_handles_multiple_chunks_and_extension(self):
        encoded = b"5\r\nhello\r\n6;ext=1\r\n world\r\n0\r\n\r\n"
        decoded, complete = _dechunk(encoded)
        self.assertTrue(complete)
        self.assertEqual(decoded, b"hello world")

    def test_dechunk_reports_incomplete(self):
        decoded, complete = _dechunk(b"5\r\nhel")
        self.assertFalse(complete)
        self.assertEqual(decoded, b"")

    def test_no_response_raises(self):
        with self.assertRaises(LocalApiError):
            _read_response(feeder(), time.monotonic() + 1)


class TestStatusHandling(unittest.TestCase):
    def test_200_returns_parsed_json(self):
        payload = _status_payload(200, "OK", b'{"BackendState": "Running"}', "test")
        self.assertEqual(payload["BackendState"], "Running")

    def test_401_raises_unauthorized_with_honest_message(self):
        with self.assertRaises(LocalApiUnauthorized) as ctx:
            _status_payload(
                401, "Unauthorized",
                b"authentication failed: Unable to impersonate using a named pipe",
                "Named Pipe",
            )
        msg = str(ctx.exception)
        self.assertIn("401", msg)
        self.assertIn("administrators-only", msg)
        self.assertIn("Unable to impersonate", msg)

    def test_403_also_unauthorized(self):
        with self.assertRaises(LocalApiUnauthorized):
            _status_payload(403, "Forbidden", b"", "test")

    def test_other_status_is_plain_error(self):
        with self.assertRaises(LocalApiError) as ctx:
            _status_payload(500, "Internal Server Error", b"", "test")
        self.assertNotIsInstance(ctx.exception, LocalApiUnauthorized)

    def test_unparseable_200_body_is_error_not_crash(self):
        with self.assertRaises(LocalApiError):
            _status_payload(200, "OK", b"", "test")

    def test_error_types_are_runtime_errors_for_existing_callers(self):
        """executor.run_status catches RuntimeError; these must stay compatible."""
        self.assertTrue(issubclass(LocalApiError, RuntimeError))
        self.assertTrue(issubclass(LocalApiUnauthorized, LocalApiError))


class TestBoundedExecution(unittest.TestCase):
    """A stuck pipe call must be shed at the deadline, not block the caller."""

    def test_slow_operation_is_abandoned_at_deadline(self):
        from src.utils.local_api import _run_bounded

        started = time.monotonic()
        with self.assertRaises(LocalApiError):
            _run_bounded(lambda: time.sleep(5), 0.2, "test operation")
        self.assertLess(time.monotonic() - started, 1.0, "deadline was not enforced")

    def test_result_is_returned_when_fast_enough(self):
        from src.utils.local_api import _run_bounded

        self.assertEqual(_run_bounded(lambda: "value", 1.0, "test operation"), "value")

    def test_oserror_propagates_instead_of_being_swallowed(self):
        from src.utils.local_api import _run_bounded

        def boom():
            raise FileNotFoundError("no such pipe")

        with self.assertRaises(FileNotFoundError):
            _run_bounded(boom, 1.0, "test operation")

    def test_pipe_request_to_missing_pipe_fails_fast(self):
        from src.utils.local_api import _pipe_request_bounded

        started = time.monotonic()
        with self.assertRaises((OSError, LocalApiError)):
            _pipe_request_bounded(r"\\.\pipe\definitely-not-there-98765", b"GET / HTTP/1.1\r\n\r\n", 2.0)
        self.assertLess(time.monotonic() - started, 2.5)


if __name__ == "__main__":
    unittest.main()
