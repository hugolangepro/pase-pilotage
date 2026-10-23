import math
import numpy as np
import pytest

from pase.ENVIRONMENT.sky_model import ReinhartSky, CIEStandardSky

sky = ReinhartSky()

@pytest.mark.parametrize(
    "mf, expected_mf, expected_f",
    [
        (1, 1, 0),
        (2, 2, 1),
        (4, 4, 2),
        (8, 8, 3),
        (16, 16, 4),
        (4.0, 4, 2),               # float entier accepté
        (np.int64(8), 8, 3),       # numpy int accepté
        (np.float64(32.0), 32, 5), # numpy float accepté
        ("4", 4, 2),               # chaîne numérique acceptée
    ],
)
def test_validate_mf_f_valid_values(mf, expected_mf, expected_f):
    got_mf, got_f = sky.validate_MF_F(mf)
    assert got_mf == expected_mf
    assert got_f == expected_f
    assert (2 ** got_f) == got_mf

@pytest.mark.parametrize("mf", [0, -1, -2, 3.5, "four", None])
def test_validate_mf_f_invalid_values(mf):
    with pytest.raises((TypeError, ValueError)):
        sky.validate_MF_F(mf)

def test_validate_mf_f_boolean_behavior():
    got_mf, got_f = sky.validate_MF_F(True)
    assert got_mf == 1 and got_f == 0

def test_validate_mf_f_large_values():
    mf = 2 ** 30
    got_mf, got_f = sky.validate_MF_F(mf)
    assert got_mf == mf
    assert got_f == 30
    assert (2 ** got_f) == got_mf

def test_validate_mf_f_string_equivalence():
    got_mf, got_f = sky.validate_MF_F("16")
    assert got_mf == 16 and got_f == 4

@pytest.mark.parametrize(
    'mf',
    np.arange(1, 32+1)
)
def test_num_sky_patches_matches_reference(mf):
    # Reference is Ivanova et al. formula:
    # Ivanova_num_total = 144 * (MF**2) + 1
    # Check for MF values 1 to 16

    # Compute reference:
    Ivanova_num_total = 144 * (mf**2) + 1

    sky = ReinhartSky(MF=mf)
    _, reinhart_num_total = sky.get_reinhart()
    assert len(sky.reinhart_patches) == Ivanova_num_total

@pytest.mark.parametrize(
    'mf',
    np.arange(1, 32+1)
)
def test_patches_sum_surf_areas(mf):
    """
    Sum of normalized surface areas of all patches should amount to 1
    :param mf:
    """
    sky = ReinhartSky(MF=mf)
    sum_surf_areas = sky.reinhart_patches['Normalized surf area'].sum()
    assert math.isclose(sum_surf_areas, 1, rel_tol=5e-3)

@pytest.mark.parametrize(
    'mf',
    np.arange(1, 32+1)
)
def test_patches_sum_solid_angles(mf):
    sky = ReinhartSky(MF=mf)
    sum_solid_angles = sky.reinhart_patches['solid_angle_sr'].sum()
    assert math.isclose(sum_solid_angles, 2*np.pi, rel_tol=5e-3)

def test_compute_solid_angle_elev_azim():
    assert sky.compute_solid_angle_from_elev_azim(45, 2)

def test_compute_solid_angle_cone():
    assert math.isclose(sky.compute_solid_angle_cone(5),
                        0.024,
                        rel_tol=1e-2)


# ---------------------------------------------------------------------------
# compute_rel_radiance normalization
# ---------------------------------------------------------------------------

def test_uniform_sky_rel_radiance_sums_to_N():
    """
    For sky type 5 (uniform), rel_radiance_distribution must equal 1 for every
    patch (f_P = 1, not f_P/N).
    """
    sky_MF1 = ReinhartSky(MF=1)
    N = len(sky_MF1.reinhart_patches)
    cie = CIEStandardSky(sky_MF1.reinhart_patches, sun_az=180, sun_el=45, sky_type=5)
    assert np.isclose(cie.rel_radiance_distribution.sum(), N, rtol=1e-6), (
        f"Expected sum={N} (f_P=1 for all patches); "
        f"got {cie.rel_radiance_distribution.sum():.4f}. "
        f"Possible /N normalization bug."
    )


# ---------------------------------------------------------------------------
# TestCIEStandardSky
# ---------------------------------------------------------------------------

class TestCIEStandardSky:

    SUN_AZ = 180.0
    SUN_EL = 45.0
    ALL_SKY_TYPES = list(range(1, 16))

    @pytest.fixture(scope='class')
    def patches(self):
        return ReinhartSky(MF=1).reinhart_patches

    @pytest.mark.parametrize('sky_type', ALL_SKY_TYPES)
    def test_rel_radiance_non_negative(self, patches, sky_type):
        """Relative radiance must be non-negative for all sky types and all patches."""
        cie = CIEStandardSky(patches, sun_az=self.SUN_AZ, sun_el=self.SUN_EL,
                             sky_type=sky_type)
        assert (cie.rel_radiance_distribution >= 0).all(), (
            f"sky_type={sky_type}: negative values found in rel_radiance_distribution"
        )

    @pytest.mark.parametrize('sky_type', ALL_SKY_TYPES)
    def test_rel_radiance_not_divided_by_N(self, patches, sky_type):
        """
        rel_radiance_distribution must not be divided by N (number of sky patches).
        By construction of the CIE model, the zenith patch always has f_P = 1, so
        max(rel_radiance_distribution) >= 1. If the /N bug were present, the max
        would be <= 1/N << 1.
        """
        N = len(patches)
        cie = CIEStandardSky(patches, sun_az=self.SUN_AZ, sun_el=self.SUN_EL,
                             sky_type=sky_type)
        assert cie.rel_radiance_distribution.max() >= 1.0 - 1e-6, (
            f"sky_type={sky_type}: max={cie.rel_radiance_distribution.max():.6f}. "
            f"Suspicion of /N normalization bug (1/N = {1/N:.5f})"
        )

    def test_uniform_sky_constant_radiance(self, patches):
        """For sky type 5 (uniform), all patches must have identical radiance f_P = 1."""
        cie = CIEStandardSky(patches, sun_az=self.SUN_AZ, sun_el=self.SUN_EL,
                             sky_type=5)
        assert np.allclose(cie.rel_radiance_distribution, 1.0), (
            "Uniform sky (type 5): expected f_P=1 for all patches, "
            f"got min={cie.rel_radiance_distribution.min():.6f}, "
            f"max={cie.rel_radiance_distribution.max():.6f}"
        )

    @pytest.mark.parametrize('sky_type', ALL_SKY_TYPES)
    def test_sky_integral_finite_positive(self, patches, sky_type):
        """
        sky_integral = Σ_P(f_P * norm_P) must be finite and positive for all sky
        types. This is the per-timestep normalization factor used in
        get_shaded_radiance_contrib() to ensure energy conservation.
        """
        norm = patches['cos(z)'].values * patches['Normalized surf area'].values
        norm = norm / norm.sum()
        cie = CIEStandardSky(patches, sun_az=self.SUN_AZ, sun_el=self.SUN_EL,
                             sky_type=sky_type)
        sky_integral = float((cie.rel_radiance_distribution * norm).sum())
        assert np.isfinite(sky_integral), (
            f"sky_type={sky_type}: sky_integral is not finite"
        )
        assert sky_integral > 0, (
            f"sky_type={sky_type}: sky_integral={sky_integral:.4f} is not positive"
        )