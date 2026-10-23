# Diffuse irradiance benchmark

## 1 m² square panel at 1 m height

Diffuse irradiance benchmarking is handled in `diffuse_benchmark.py`.

The benchmarking case is built with a 1x1 m square at a height of 1 m.

Nine (9) sensors are placed under the square at ground level : 
- 1 at each of the four corners (4 corners)
- 1 at each middle point of the sides (4 midpoints)
- 1 at the center

The test consists in computing the diffuse light map (or view factor map) under 
a Reinhart discrete sky, with varying Multiplying Factors 
(respectively MF:1, MF:2, MF:4 and MF:8).

The diffuse light map represents the fraction of sky patches of the discrete 
sky that a sensor sees, relative to the total number of sky patches. 
A sensor that sees all the sky patches (i.e. unobstructed view) has a value of 
1, while conversely a totally obstructed sensor (e.g. inside an opaque box) has
a value of 0.

Considering the situation, a central symmetry is expected in the computed 
signal, aka all midpoints should present the same value and all corners as well.

To reflect this, the benchmarking result is based on the coefficient of 
variation (cov = std/mean) of both corners and midpoints and marked as : 
- cov = 0: pass
- 0 < cov <= tolerance : borderline
- tolerance < cov : FAIL

## 1 m² round panel at 1 m height

Diffuse irradiance benchmarking is handled in `diffuse_benchmark_disc.py`.

The benchmarking case is built with a horizontal disc of 1 m² area at a height of 1 m.
The radius of the disc is derived from the 1 m² area and computes to 1/sqrt(pi).

Nine (9) sensors are placed under the disc at ground level : 
- 1 at each of the four corners of the tangential square of the projected disc (4 corners)
- 1 at each middle point of the sides  of the tangential square of the projected disc (4 midpoints)
- 1 at the center of the projected disc

The test consists in computing the diffuse light map (or view factor map) under 
a Reinhart discrete sky, with varying Multiplying Factors 
(respectively MF:1, MF:2, MF:4 and MF:8).

The diffuse light map represents the fraction of sky patches of the discrete 
sky that a sensor sees, relative to the total number of sky patches. 
A sensor that sees all the sky patches (i.e. unobstructed view) has a value of 
1, while conversely a totally obstructed sensor (e.g. inside an opaque box) has
a value of 0.

Considering the situation, a central symmetry is expected in the computed 
signal, aka all midpoints should present the same value and all corners as well.

To reflect this, the benchmarking result is based on the coefficient of 
variation (cov = std/mean) of both corners and midpoints and marked as: 
- cov = 0 : pass
- 0 < cov <= tolerance : borderline
- tolerance < cov : FAIL

The tolerance is set to 1%.

Furthermore, the value at the center can be derived analytically (see Sources, 
SYMBIOSYST deliverable):

$f = 1 - (sin(theta_{0}))^2$

With $theta_{0}$ the half-opening angle of the disc:

theta_{0} = atan(R/h)

With:
- R: radius of the disc
- h: height of the disc

Thus the value at the center is computed and compared to the analytical expected 
value in the form of the relative error. 
rel_error = 1 - (computed_value/analytical_value)

Similaryly to the cov test, the result is marked as :
- rel_error = 0 : pass
- 0 < rel_error <= tolerance : borderline
- tolerance < rel_error : FAIL

The tolerance is set to 1%.

## 1 m² round panel at varying heights 

In BENCHMARKING/diffuse_benchmark_disc_height.py

The benchmarking case is built with a horizontal disc of 1 m² area at heights varying between 0.1 and 5 m.
The radius of the disc is derived from the 1 m² area and computes to 1/sqrt(pi).

One sensor is placed at ground level under the center of the disc.

The view factor value f at the sensor location can be derived analytically (see Sources, SYMBIOSYST deliverable):

$f = 1 - (sin(theta_{0}))^2$

With $theta_{0}$ the half-opening angle of the disc:

theta_{0} = atan(R/h)

With:
- R: radius of the disc
- h: height of the disc

Thus the f value at the center is computed and compared to the analytical value in the form of the relative error:

rel_error = 1 - (computed_value/analytical_value)

Similaryly to the tests in other cases, the result is marked as :
- rel_error = 0 : pass
- 0 < rel_error <= tolerance : borderline
- tolerance < rel_error : FAIL

The tolerance is set to 1%.

## Sources 
https://www.symbiosyst.eu/wp-content/uploads/2025/01/SYMBIOSYST_DELIVERABLE_D2.2_Final_Submitted.pdf, p. 47

