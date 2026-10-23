#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 23 11:20:22 2025

@author: roxane
"""

import numpy as np
import pytest

# Both tests use the session-scoped light_fixture, which fetches from PVGIS.
pytestmark = pytest.mark.network


def test_get_anisotropy_index(light_fixture):
    rad_top_atm = np.array([0, 0, 0, 52.01, 215.54, 453.69, 273.43, 127.08, 0, 0, 0])
    BHI = np.array([0, 0, 0, 1.123, 1.18, 138.43, 250.21, 126.54, 0, 0, 0])

    assert (
        light_fixture.get_anisotropy_index(rad_top_atm, BHI)
        == np.array(
            [
                0,
                0,
                0,
                1.123 / 52.01,
                1.18 / 215.54,
                138.43 / 453.69,
                250.21 / 273.43,
                126.54 / 127.08,
                0,
                0,
                0,
            ]
        )
    ).all()


@pytest.mark.parametrize(
    "kc_in, cle_in, expected_sky_types",
    [
        (0.01, 0.0, 1),  # Overcast sky
        (0.01, 0.15, 1),
        (0.40, 0.00, 1),
        (0.4001, 0.0001, 1),
        (0.01, 0.2, 4),  # Intermediate overcast sky
        (0.25, 0.25, 4),
        (0.45, 0.00, 4),
        (0.4501, 0.0001, 4),
        (0.25, 0.30, 7),  # Intermediate sky
        (0.40, 0.15, 7),
        (0.40, 0.30, 7),
        (0.70, 0.15, 7),
        (0.7001, 0.1501, 7),
        (0.75, 1.05, 11),  # Intermediate clear sky
        (1.0, 0.65, 11),
        (1.15, 1.0, 11),
        (1.1501, 1.001, 11),
        (1.0, 1.0, 13),  # Clear sky
        (1.10, 0.90, 13),
        (1.10001, 0.90001, 13),
        (0.1, 0.7, 5),  # undefined sky (low Kc, high Cle)
        (0.101, 0.701, 5),
        (1.0, 0.15, 5),  # undefined sky (high Kc, low Cle)
        (1.001, 0.1501, 5),
        (1.25, 1.05, 5),  # undefined sky (high Kc, high Cle)
        (1.2501, 1.0501, 5),
    ],
)
def test_get_sky_type(light_fixture, kc_in, cle_in, expected_sky_types):
    """

    Parameters
    ----------
    kc_in list
    cle_in list
    expected_sky_type list
    """
    assert light_fixture.get_sky_type(np.array([kc_in]), np.array([cle_in])) == [
        expected_sky_types
    ]
