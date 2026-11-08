import base64
import copy
import importlib.util
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET
import zlib
from privacylab import adaptive_demo
ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('adaptive_figure',ROOT/'examples/render_adaptive.py')
FIG=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(FIG)


class AdaptiveFigureTests(unittest.TestCase):
    def test_all_36_cells_positions_and_tree_edges(self):
        r=adaptive_demo();root=ET.fromstring(FIG.render(r));ids={e.get('id'):e for e in root.iter() if e.get('id')}
        for i,c in enumerate(r['controls']):
            v=c['report'];values=[v['product_factor'],v['joint_audit']['delta'],v['clipped_delta_bound'],v['uniform_survival_bound'],v['additive_bound']]
            for j,(xx,value) in enumerate(zip([485,610,745,875,995],values)):
                e=ids[f'adaptive-cell-{i}-{j}'];self.assertEqual(e.text,value);self.assertEqual(float(e.get('x')),xx);self.assertEqual(float(e.get('y')),224+44*i)
        for i,(cx,rec) in enumerate(zip([290,830],r['controls'][3]['report']['pairs'][0]['flow'][1:])):
            for j,value in enumerate([rec['good_mass_in'],rec['conditional_delta'],rec['removed_mass']]):
                e=ids[f'branch-value-{i}-{j}'];self.assertEqual(e.text,value);self.assertEqual(float(e.get('x')),cx+64);self.assertEqual(float(e.get('y')),810+32*j)
        for name,d in [('branch-left','M 548 673 L 290 747'),('branch-right','M 572 673 L 830 747')]:
            self.assertEqual(ids[name].get('d'),d);self.assertEqual(ids[name].get('stroke-width'),'3')

    def test_complete_metadata_and_hidden_flow_tamper(self):
        report=adaptive_demo();svg=FIG.render(report);root=ET.fromstring(svg)
        e=next(e for e in root.iter() if e.get('id')=='full-adaptive-report')
        self.assertEqual(json.loads(zlib.decompress(base64.b64decode(e.text))),report)
        changed=copy.deepcopy(report);changed['controls'][4]['report']['pairs'][0]['leaves'][0]['scaled_q_slack']='999/7'
        self.assertNotEqual(FIG.render(changed),svg)

    def test_committed_svg_byte_exact(self):
        self.assertEqual((ROOT/'assets/adaptive-transcripts.svg').read_text(),FIG.render(adaptive_demo()))
