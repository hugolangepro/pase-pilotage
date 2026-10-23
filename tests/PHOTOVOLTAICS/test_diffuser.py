from pase.PHOTOVOLTAICS.diffuser import LenticularDiffuser, rotation_coordinate
from pase.ENVIRONMENT.sky_model import ReinhartSky
import numpy as np

az = [0, 45, 90, 135, 180, 225, 270, 315] # some azimuth angles
ti = [-90, -45, 0, 45, 90] # some elevation angles
Diffusers = [LenticularDiffuser(azi, tii, omega = 30) for azi in az for tii in ti] # some diffusers with different orientations
def test_LenticularDiffuser_configuration():
    """test orthogonality between diffuser normal and diffuser lens direction"""
    for D in Diffusers:
            assert np.isclose(np.sum(D.len_vector*D.normal), 0, rtol=1e-08)

suns  = [np.array([i, j, 1]).reshape((1,3))/np.sqrt(i**2+j**2+1) for i in range(-1, 2, 1) for j in range(-1, 2, 1)] # some sun positions
def test_LenticularDiffuser_beta_gamma():
    """Test the values of the beta and gamma angles (i.e., angles defining the direction of the transmitted rays).
    Compare the standard method with an alternative one."""
    for D in Diffusers:
        for sun in suns:
            print(sun)
            beta = D.get_beta_angle(sun, 0.1) # beta angle to validate
            gamma = D.get_gamma_angle(sun, 0.1) # gamma angle to validate
            dot_gl = np.sum(sun*D.len_vector) # inner product between sun vector and len vector
            cross_gl = np.array([sun[0,1]*D.len_vector[2] - sun[0,2]*D.len_vector[1], # cross product between sun vector
                                 sun[0,2]*D.len_vector[0] - sun[0,0]*D.len_vector[2], # and len vector
                                 sun[0,0]*D.len_vector[1] - sun[0,1]*D.len_vector[0]])
            dot_cgl_n = np.sum(cross_gl*D.normal)#inner prod. between the previous cross product and the diffuser normal
            div = np.sqrt(np.sum(cross_gl*cross_gl)) if np.sqrt(np.sum(cross_gl*cross_gl)) !=0 else 1 # norm of cross_gl
            cos_b = max(min(dot_cgl_n/div, 1), -1) # cos angle generate by the inner product cross_gl and the normal
            b =np.arccos(cos_b)
            beta_comp = b + np.arange(-D.omega+0.1/2, D.omega + 0.1/2, 0.1) # rays repartition within the diffuser aperture
            cos_gamma = max(min(dot_gl, 1), -1) # beta ground truth
            g = np.arccos(cos_gamma)
            gamma_comp = np.tile(g, (1, int((2 * D.omega + 0.1) // 0.1))) # gamma ground truth
            assert np.isclose(gamma, gamma_comp, rtol = 1e-5).all()
            assert np.isclose(beta, beta_comp, rtol=1e-5).all()

sky = ReinhartSky(MF=1).reinhart_patches
pTarget = np.column_stack([sky.x,sky.y,sky.z])


def test_discretized_BSDF():
    """Check energy conservation in the BSDF discretization."""
    res = 0.1
    beta = np.deg2rad(np.arange(-15, 15, 1)) # creation of the diffuser rays
    gamma = np.deg2rad([45])
    x = -np.sin(gamma) * (np.sin(beta - res / 2) - np.sin(beta + res / 2)) / res
    y = np.cos(gamma)*np.ones(beta.shape)
    z = -np.sin(gamma) * (np.cos(beta + res / 2) - np.cos(beta - res / 2)) / res
    ds = np.sin(gamma) * res * np.ones(beta.shape)
    L = ds.sum()
    rho = 1 / L * np.ones(beta.shape)
    for D in Diffusers:
        D.x_sr = x.reshape((1,len(beta)))
        D.y_sr = y.reshape((1,len(beta)))
        D.z_sr = z.reshape((1,len(beta)))
        D.ds = ds.reshape((1,len(beta)))
        D.rho = rho.reshape((1,len(beta)))  # uniform repartition the energy within
        # the rays
        D.get_discretized_BSDF(pTarget, sky['Normalized surf area'])
        W = D.W
        assert np.isclose(W.sum(), 1, rtol=1e-5)  # energy conservation if sum(W) == 1




