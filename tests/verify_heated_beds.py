# =============================================================================
# HYDRA-UMC-SUITE - Heated bed STL, dimensions and configuration verifier
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from hydra_suite.heated_beds import HEATED_BED_MODELS, heated_bed_model, heated_bed_size, select_heated_bed, resize_heated_bed
from hydra_suite.render.module_rig import module_segments, module_segment_mesh

assert [m['id'] for m in HEATED_BED_MODELS] == ['100x100x5','200x100x5','200x200x5','255x255x5']
source = {'size': {'width': 500, 'length': 500}, 'targetTemp': 80, 'ssrActive': True,
          'currentTemp1': 76, 'currentTemp2': 74, 'worldPos': {'x': 12, 'y': 34}}
assert heated_bed_size(source) == source['size']
for model in HEATED_BED_MODELS:
    selected = select_heated_bed(source, model['id'])
    assert selected['size'] == {'width': model['width'], 'length': model['length']}
    for key in ('targetTemp','ssrActive','currentTemp1','currentTemp2','worldPos'):
        assert selected[key] == source[key]
    for w, length in [(model['width'], model['length']), (75, 300), (500, 150)]:
        mesh = module_segment_mesh(module_segments('heatedBed', w, length, model['id'])[0])
        assert np.isfinite(mesh.vertices).all() and np.isfinite(mesh.normals).all()
        assert np.allclose(np.ptp(mesh.vertices, axis=0), [w/1000, .005, length/1000], atol=1e-6)
        assert np.allclose((mesh.vertices.min(0)+mesh.vertices.max(0))[[0,2]], [0,0], atol=1e-6)
        assert abs(mesh.vertices[:,1].min()) < 1e-6
    resized = resize_heated_bed(selected, 'width', model['width']+5)
    assert resized['size']['width'] == model['width']+5 and resized['ssrActive']
for bad in (True, float('nan'), float('inf'), 0, 24, 5001, 25.5):
    assert resize_heated_bed(source, 'length', bad) == source
assert select_heated_bed(source, '../../outside') == source
assert heated_bed_model('unknown')['id'] == '200x200x5'
assert source['size'] == {'width':500,'length':500}
print('VERIFY_HEATED_BEDS=PASS models=4 height=5mm custom-footprint=8 controls-preserved')
