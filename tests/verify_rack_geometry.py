# =============================================================================
# HYDRA-UMC-SUITE - Rack STL dimensional and material regression tests
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hydra_suite.racks import rack_geometry, rack_parts, valid_dimension
from hydra_suite.render.module_rig import rack_segments, module_segment_mesh


def main():
    for value in (float("nan"), float("inf"), 39, 1001, 1.5, "160", True, None):
        assert not valid_dimension(value)
    assert rack_geometry({"type":"Output"}) == dict(width=160, depth=160, capacity=24, color="#10b981")
    assert not rack_segments({"type":"None"})
    count = 0
    for n in (1, 6, 24):
        for w,d in ((40,40), (161,201), (1000,500)):
            rack = dict(type="Input", capacity=n, width=w, depth=d, color="#abcdef", usableSlots=[True]*n)
            segs = rack_segments(rack)
            assert len(segs) == 3+3*n
            assert len(rack_parts(rack)) == 3+2*n
            vertices=[]
            for s in segs:
                mesh=module_segment_mesh(s)
                assert np.isfinite(mesh.vertices).all() and np.isfinite(mesh.normals).all()
                assert np.allclose(np.linalg.norm(mesh.normals,axis=1),1,atol=1e-5)
                vertices.append(mesh.vertices+np.array(s.pos))
            v=np.vstack(vertices)
            assert np.allclose(v.min(axis=0),[-(w+20)/2000,0,-(d+20)/2000],atol=1e-6)
            assert np.allclose(v.max(axis=0),[(w+20)/2000,(n*10+40)/1000,(d+20)/2000],atol=1e-6)
            assert segs[0].color == tuple(int("abcdef"[i:i+2],16)/255 for i in (0,2,4))
            count+=1
    print(f"VERIFY_RACK_GEOMETRY=PASS configurations={count} pitch=10mm color=PASS")


if __name__ == "__main__":
    main()
