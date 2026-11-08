import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from privacylab import audit,demo
ROOT=Path(__file__).resolve().parents[1]


class CLITests(unittest.TestCase):
    def test_committed_demo_and_full_json_cli(self):
        expected=(ROOT/'examples/demo.json').read_bytes()
        result=subprocess.check_output([sys.executable,'-m','privacylab','demo'],cwd=ROOT)
        self.assertEqual(result,expected);self.assertEqual(json.loads(result),demo())

    def test_caller_input_and_api_match_exact(self):
        path=ROOT/'examples/input.json';obj=json.loads(path.read_text())
        out=subprocess.check_output([sys.executable,'-m','privacylab','audit',str(path)],cwd=ROOT)
        self.assertEqual(json.loads(out),audit(obj['channel'],obj['factor']))
        self.assertEqual(json.loads(out)['delta'],'0');self.assertEqual(json.loads(out)['pure_factor'],'3')

    def test_strict_errors_empty_stdout(self):
        original=json.loads((ROOT/'examples/input.json').read_text())
        missing=dict(original);del missing['factor']
        bad=[dict(original,extra=1),dict(original,schema_version=True),dict(original,factor=3.0),missing,
             dict(original,channel=dict(original['channel'],probabilities=[[.75,.25],[.25,.75]]))]
        bodies=[json.dumps(v).encode()for v in bad]+[b'{"schema_version":1,"schema_version":1}',b'NaN',b'\xff',b' '*100001]
        with tempfile.TemporaryDirectory()as d:
            path=Path(d)/'input.json'
            for body in bodies:
                path.write_bytes(body)
                r=subprocess.run([sys.executable,'-m','privacylab','audit',str(path)],capture_output=True,cwd=ROOT)
                self.assertEqual(r.returncode,2);self.assertFalse(r.stdout);self.assertTrue(r.stderr)
        r=subprocess.run([sys.executable,'-m','privacylab','audit','/nonexistent/finite-channel.json'],capture_output=True,cwd=ROOT)
        self.assertEqual(r.returncode,2);self.assertFalse(r.stdout)
