import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ImportSafetyTests(unittest.TestCase):
    def test_import_does_not_process_command_line_files(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            environment = os.environ.copy()
            environment["PYTHONPATH"] = str(PROJECT_ROOT)
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "import sys; sys.argv = ['smi2ass.py', 'missing.smi']; "
                    "import smi2ass; print('import-safe')",
                ],
                cwd=temporary_directory,
                env=environment,
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "import-safe")


if __name__ == "__main__":
    unittest.main()
