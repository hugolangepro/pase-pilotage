#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Tests for Light.get_daily_sky_type
#
# The method does not use any instance attributes, so we create a bare
# Light object (skipping __init__) to avoid needing weather files or PVGIS.

from calendar import isleap
import numpy as np
import pandas as pd

from pase.ENVIRONMENT.light import Light, SKY_CATEGORY_LABELS

light = Light.__new__(Light)


# ── Helpers ──────────────────────────────────────────────────────────────────

def one_day(sky_types, ghi_values, date='2020-06-01'):
    """Build a single-day hourly DataFrame with CIE Sky Type and GHI."""
    index = pd.date_range(date, periods=len(sky_types), freq='h')
    return pd.DataFrame({'CIE Sky Type': sky_types, 'GHI': ghi_values},
                        index=index, dtype=float)


def full_year(sky_type_value, year=2020):
    """Build a full-year hourly DataFrame filled with one constant sky type."""
    n_hours = (366 if isleap(year) else 365) * 24
    index = pd.date_range(f'{year}-01-01', periods=n_hours, freq='h')
    return pd.DataFrame({'CIE Sky Type': float(sky_type_value), 'GHI': 100.0},
                        index=index)


def run(sky_types, ghi_values, date='2020-06-01'):
    """Run get_daily_sky_type for one day and return (sky_type, category)."""
    result = light.get_daily_sky_type(one_day(sky_types, ghi_values, date))
    return result['CIE Sky Type'].iloc[0], result['Sky Category'].iloc[0]


# ── Mode: most frequent sky type wins ────────────────────────────────────────

def test_most_frequent_type_is_chosen():
    # type 4 appears 7 times, type 1 appears 3 times → 4 wins
    sky_type, _ = run([1, 1, 1, 4, 4, 4, 4, 4, 4, 4], [50] * 10)
    assert sky_type == 4


def test_single_type_all_day():
    # Only one type present → returned as-is
    sky_type, _ = run([7, 7, 7, 7], [200, 300, 300, 200])
    assert sky_type == 7


def test_three_types_one_dominant():
    # type 1: 2 h, type 4: 5 h, type 13: 2 h → 4 wins
    sky_type, _ = run([1, 1, 4, 4, 4, 4, 4, 13, 13],
                      [10, 20, 100, 200, 300, 200, 100, 20, 10])
    assert sky_type == 4


# ── Tiebreak: when counts are equal, highest total GHI wins ──────────────────

def test_tiebreak_higher_ghi_wins():
    # type 1: 3 h at low GHI, type 4: 3 h at high GHI → 4 wins
    sky_type, _ = run([1,  1,  1,  4,   4,   4],
                      [50, 60, 70, 400, 500, 600])
    assert sky_type == 4


def test_tiebreak_lower_ghi_loses():
    # type 13: 4 h at very low GHI, type 1: 4 h at high GHI → 1 wins
    sky_type, _ = run([13, 13, 13, 13,  1,   1,   1,   1],
                      [10, 10, 10, 10, 500, 600, 700, 800])
    assert sky_type == 1


def test_tiebreak_equal_ghi_lower_type_wins():
    # type 4 and type 7 tied on both count and GHI → lower type (4) wins
    sky_type, _ = run([4,   4,   4,   7,   7,   7],
                      [100, 200, 300, 100, 200, 300])
    assert sky_type == 4


def test_tiebreak_all_zero_ghi_lower_type_wins():
    # GHI = 0 for all hours (polar edge case) → lower type wins
    sky_type, _ = run([7, 7, 11, 11], [0, 0, 0, 0])
    assert sky_type == 7


# ── NaN handling: nighttime hours must not affect the result ──────────────────

def test_all_nighttime_returns_nan():
    sky_type, _ = run([np.nan, np.nan, np.nan], [0, 0, 0])
    assert np.isnan(sky_type)


def test_nighttime_nans_excluded_from_count():
    # night: NaN, daytime: type 4 x 3, type 1 x 1 → mode = 4
    sky_type, _ = run([np.nan, 1, 4, 4, 4, np.nan, np.nan, np.nan, np.nan, np.nan],
                      [0,     50, 200, 300, 200, 0, 0, 0, 0, 0])
    assert sky_type == 4


# ── Sky category labels ───────────────────────────────────────────────────────

def test_category_labels_are_correct():
    expected = {1: 'overcast', 4: 'intermediate overcast', 7: 'intermediate',
                11: 'intermediate clear', 13: 'clear'}
    for cie_type, label in expected.items():
        _, category = run([cie_type] * 6, [100] * 6)
        assert category == label


def test_type_5_is_undefined():
    _, category = run([5] * 6, [100] * 6)
    assert category == 'undefined'


def test_all_nighttime_category_is_undefined():
    _, category = run([np.nan, np.nan], [0, 0])
    assert category == 'undefined'


def test_sky_category_labels_has_exactly_5_entries():
    assert set(SKY_CATEGORY_LABELS.keys()) == {1, 4, 7, 11, 13}


# ── Output shape and structure ────────────────────────────────────────────────

def test_output_is_a_dataframe_with_two_columns():
    result = light.get_daily_sky_type(one_day([1] * 6, [100] * 6))
    assert isinstance(result, pd.DataFrame)
    assert list(result.columns) == ['CIE Sky Type', 'Sky Category']


def test_regular_year_gives_365_rows():
    assert len(light.get_daily_sky_type(full_year(5, year=2019))) == 365


def test_leap_year_gives_366_rows():
    assert len(light.get_daily_sky_type(full_year(5, year=2020))) == 366


# ── Multi-day: each day is computed independently ─────────────────────────────

def test_two_days_computed_independently():
    day1 = one_day([1]  * 8, [100] * 8, date='2020-06-01')
    day2 = one_day([13] * 8, [500] * 8, date='2020-06-02')
    result = light.get_daily_sky_type(pd.concat([day1, day2]))
    assert result['CIE Sky Type'].iloc[0] == 1  and result['Sky Category'].iloc[0] == 'overcast'
    assert result['CIE Sky Type'].iloc[1] == 13 and result['Sky Category'].iloc[1] == 'clear'


def test_all_pase_sky_types_round_trip():
    # Feed each PASE sky type as the only value for a day → must come back unchanged
    pase_types = [1, 4, 5, 7, 11, 13]
    days = pd.concat([one_day([t] * 8, [200] * 8, date=f'2020-01-{i+1:02d}')
                      for i, t in enumerate(pase_types)])
    result = light.get_daily_sky_type(days)
    for i, expected in enumerate(pase_types):
        assert result['CIE Sky Type'].iloc[i] == expected
