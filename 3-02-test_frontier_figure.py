import base64
import copy
from fractions import Fraction as F
import importlib.util
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET
import zlib
from privacylab import frontier_demo
ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('frontier_figure',ROOT/'examples/render_frontier.py')
FIG=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(FIG)


class FrontierFigureTests(unittest.TestCase):
    def test_all_ten_query_cells_and_all_curve_vertices(self):
        report=frontier_demo();root=ET.fromstring(FIG.render(report));ids={e.get('id'):e for e in root.iter() if e.get('id')}
        for i,(name,value,_) in enumerate(FIG.query_cells(report)):
            for j,(xx,v) in enumerate(zip([58,360],[name,value])):
                e=ids[f'frontier-query-{i}-{j}'];self.assertEqual(e.text,v);self.assertEqual(float(e.get('x')),xx);self.assertEqual(float(e.get('y')),744+42*i)
        p=report['controls'][2]['profile'];points=[]
        for i,k in enumerate(p['knots']):
            t=F(k['factor']);d=F(k['point']['delta']);x=150+216*(float(t)-1);y=510-768*float(d);points.append((x,y))
            e=ids[f'frontier-knot-{i}'];self.assertEqual(float(e.get('cx')),x);self.assertEqual(float(e.get('cy')),y);self.assertEqual(e.get('r'),'5')
        self.assertEqual(ids['global-frontier'].get('points'),' '.join(f'{x:.3f},{y:.3f}' for x,y in points))
        for i,pair in enumerate(p['pair_curves']):
            ts=sorted({F(1),F(5)}|{F(s['lower']) for s in pair['segments'] if 1<=F(s['lower'])<=5});xy=[]
            rows=p['channel']['probabilities'];a=[F(v) for v in rows[pair['from_index']]];b=[F(v) for v in rows[pair['to_index']]]
            for t in ts:
                d=sum((max(F(0),u-t*v) for u,v in zip(a,b)),F(0));xy.append((150+216*(float(t)-1),510-768*float(d)))
            self.assertEqual(ids[f'directed-curve-{i}'].get('points'),' '.join(f'{x:.3f},{y:.3f}' for x,y in xy))

    def test_complete_metadata_and_hidden_domination_tamper(self):
        report=frontier_demo();svg=FIG.render(report);root=ET.fromstring(svg);e=next(e for e in root.iter() if e.get('id')=='full-frontier-report')
        self.assertEqual(json.loads(zlib.decompress(base64.b64decode(e.text))),report)
        changed=copy.deepcopy(report);changed['controls'][2]['profile']['segments'][0]['dominance'][0]['overlaps'][0]['start_slack']='999/7'
        self.assertNotEqual(FIG.render(changed),svg)

    def test_committed_svg_byte_exact(self):
        self.assertEqual((ROOT/'assets/factor-frontier.svg').read_text(),FIG.render(frontier_demo()))
