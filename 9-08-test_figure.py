import base64
import copy
import importlib.util
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET
import zlib
from privacylab import demo
ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('privacy_figure',ROOT/'examples/render_figure.py')
FIG=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(FIG)


class FigureTests(unittest.TestCase):
    def test_all_36_exact_cells_and_coordinates(self):
        report=demo();root=ET.fromstring(FIG.render(report));ids={e.get('id'):e for e in root.iter()if e.get('id')}
        for i,row in enumerate(report['controls']):
            values=[row['audits'][0]['pure_factor']or'infinite']+[r['delta']for r in row['audits']]
            for j,(xx,value)in enumerate(zip([468,655,805,955],values)):
                e=ids[f'privacy-cell-{i}-{j}'];self.assertEqual(e.text,value);self.assertEqual(float(e.get('x')),xx);self.assertEqual(float(e.get('y')),222+42*i)
        for i,row in enumerate(report['controls'][-1]['audits'][0]['channel']['probabilities']):
            for j,(xx,value)in enumerate(zip([470,620,770,920],row)):
                e=ids[f'joint-cell-{i}-{j}'];self.assertEqual(e.text,value);self.assertEqual(float(e.get('x')),xx);self.assertEqual(float(e.get('y')),683+45*i)

    def test_complete_metadata_and_hidden_event_tamper(self):
        report=demo();svg=FIG.render(report);root=ET.fromstring(svg)
        e=next(e for e in root.iter()if e.get('id')=='full-privacy-report')
        self.assertEqual(json.loads(zlib.decompress(base64.b64decode(e.text))),report)
        bad=copy.deepcopy(report);bad['controls'][0]['audits'][0]['pairs'][0]['event_p']='999/7'
        self.assertNotEqual(FIG.render(bad),svg)

    def test_committed_figure_byte_exact(self):
        self.assertEqual((ROOT/'assets/privacy-audit.svg').read_text(),FIG.render(demo()))
