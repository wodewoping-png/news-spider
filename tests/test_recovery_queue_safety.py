from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.recovery import load_queue, save_queue


class RecoveryQueueSafetyTests(unittest.TestCase):
    def test_invalid_existing_queue_is_not_silently_reset(self):
        with tempfile.TemporaryDirectory() as temp:
            queue = Path(temp) / "recovery-queue.json"
            queue.write_text("{broken", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "避免覆盖"):
                load_queue(queue)

            self.assertEqual(queue.read_text(encoding="utf-8"), "{broken")

    def test_queue_save_leaves_no_temporary_file(self):
        with tempfile.TemporaryDirectory() as temp:
            queue = Path(temp) / "recovery-queue.json"
            save_queue(queue, {"incidents": []})

            self.assertTrue(queue.exists())
            self.assertFalse(queue.with_suffix(".json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
