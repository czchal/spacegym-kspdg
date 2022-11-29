# Copyright (c) 2022, MASSACHUSETTS INSTITUTE OF TECHNOLOGY
# Subject to FAR 52.227-11 – Patent Rights – Ownership by the Contractor (May 2014).
# SPDX-License-Identifier: MIT

'''
Test that require:
1. KSP to be running
2. Play Mission mode
3. kRPC server to be running
'''
import pytest
import time
import numpy as np

import kspdg.utils.utils as U
from kspdg.pe20220516.pursuit_v20220516 import PursuitEnvV20220516

@pytest.fixture
def pursuit_v20220516_env():
    '''setup and teardown of the PursuitEnvV20220516 object connected to kRPC server'''
    env = PursuitEnvV20220516()
    yield env
    env.close()

def test_convert_rhntw_to_rhpbody_0(pursuit_v20220516_env):
    '''check along-track vec in right-hand NTW frame transforms to forward in right-hand pursuer body coords'''

    # rename for ease of use
    env = pursuit_v20220516_env
    env.conn.space_center.target_vessel = None
    env.vesPursue.control.rcs = False
    time.sleep(0.5)
    v_exp__rhpbody = [1, 0, 0]

    # vector pointing along track
    v__rhntw = [0, 1, 0]
    env.vesPursue.control.sas_mode = env.vesPursue.control.sas_mode.prograde
    time.sleep(0.5)   # give time to re-orient
    v__rhpbody = pursuit_v20220516_env.convert_rhntw_to_rhpbody(v__rhntw)
    assert np.allclose(v__rhpbody, v_exp__rhpbody, atol=1e-2)

    # vector pointing radial out
    v__rhntw = [1, 0, 0]
    env.vesPursue.control.sas_mode = env.vesPursue.control.sas_mode.radial
    time.sleep(2.0)   # give time to re-orient
    v__rhpbody = pursuit_v20220516_env.convert_rhntw_to_rhpbody(v__rhntw)
    assert np.allclose(v__rhpbody, v_exp__rhpbody, atol=1e-2)

    # vector pointing normal
    v__rhntw = [0, 0, 1]
    env.vesPursue.control.sas_mode = env.vesPursue.control.sas_mode.normal
    time.sleep(2.0)   # give time to re-orient
    v__rhpbody = pursuit_v20220516_env.convert_rhntw_to_rhpbody(v__rhntw)
    assert np.allclose(v__rhpbody, v_exp__rhpbody, atol=1e-2)

    # vector pointing retrograde
    v__rhntw = [0, -1, 0]
    env.vesPursue.control.sas_mode = env.vesPursue.control.sas_mode.retrograde
    time.sleep(2.0)   # give time to re-orient
    v__rhpbody = pursuit_v20220516_env.convert_rhntw_to_rhpbody(v__rhntw)
    assert np.allclose(v__rhpbody, v_exp__rhpbody, atol=1e-2)

    # vector pointing in-radial
    v__rhntw = [-1, 0, 0]
    env.vesPursue.control.sas_mode = env.vesPursue.control.sas_mode.anti_radial
    time.sleep(2.0)   # give time to re-orient
    v__rhpbody = pursuit_v20220516_env.convert_rhntw_to_rhpbody(v__rhntw)
    assert np.allclose(v__rhpbody, v_exp__rhpbody, atol=1e-2)

    # vector pointing retrograde
    v__rhntw = [0, 0, -1]
    env.vesPursue.control.sas_mode = env.vesPursue.control.sas_mode.anti_normal
    time.sleep(2.0)   # give time to re-orient
    v__rhpbody = pursuit_v20220516_env.convert_rhntw_to_rhpbody(v__rhntw)
    assert np.allclose(v__rhpbody, v_exp__rhpbody, atol=1e-2)

def test_get_combined_rcs_properties_0(pursuit_v20220516_env):
    '''check thrust maneuvers results in expected deltaV and fuel depletion'''
    # ~~ ARRANGE ~~
    env = pursuit_v20220516_env

    # set burn time and body-relative burn vector for test
    delta_t = 10.0
    burn_vec__rhbody = [1,0,0]

    # get information about celestial body for ease of use
    cb = env.vesPursue.orbit.body

    # orient craft in prograde direction
    env.conn.space_center.target_vessel = None
    env.vesPursue.control.sas = True
    time.sleep(0.1)
    env.vesPursue.control.sas_mode = env.vesPursue.control.sas_mode.prograde
    time.sleep(2.0) # give time for craft to settle

    # ~~ ACT ~~ 
    # get initial mass and speed of pursuer with respect to inertial (non-rotating) 
    # celestial body frame (not expressed in any coords because not a vector)
    m0_pur = env.vesPursue.mass
    s0_pur_cbci = env.vesPursue.flight(cb.non_rotating_reference_frame).speed

    # activate rcs and 
    # apply max thrust in forward body direction (prograde because of sas mode) for one second
    env.vesPursue.control.rcs = True
    env.vesPursue.control.forward = burn_vec__rhbody[0]
    env.vesPursue.control.right = burn_vec__rhbody[1]
    env.vesPursue.control.up = -burn_vec__rhbody[2]
    time.sleep(delta_t)
    env.vesPursue.control.forward = 0.0
    env.vesPursue.control.right = 0.0
    env.vesPursue.control.up = 0.0

    # measure new mass and speed of pursuer 
    m1_pur = env.vesPursue.mass
    s1_pur_cbci = env.vesPursue.flight(cb.non_rotating_reference_frame).speed

    # ~~ ASSERT ~~

    # check mass delta aligns with fuel consumption
    delta_m = m0_pur - m1_pur
    delta_m_exp = env.PARAMS.PURSUER.RCS.VACUUM_MAX_FUEL_CONSUMPTION_FORWARD * delta_t
    assert np.isclose(delta_m, delta_m_exp, rtol=5e-2)

    # check speed change aligns with expected delta_v
    delta_v = s1_pur_cbci - s0_pur_cbci
    delta_v_exp = env.PARAMS.PURSUER.RCS.VACUUM_SPECIFIC_IMPULSE * U._G0 * np.log(m0_pur/m1_pur)
    assert np.isclose(delta_v, delta_v_exp, rtol=1e-2)
