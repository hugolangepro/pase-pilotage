# Synthese des resultats de comparaison de pilotage

*Synthese des 16 runs de comparaison de pilotage menes en juillet 2026. La section 2 est extraite automatiquement des runs encore presents dans `OUTPUTS/COMPARAISONS_PILOTAGE/` ; la section 3 archive les chiffres des runs supprimes le 2026-07-31 lors du nettoyage du disque (~816 Mo liberes). Ce document condense a lui seul la valeur scientifique de l'ensemble.*

*Regenerable avec `python NOTES/extract_synthese.py`.*

> **Attention environnement** : tous les runs n'ont pas tourne sur la meme pile logicielle. Python **3.12** = env `pase20` (PASE 2.0, resultats de reference) ; Python **3.10** = ancien env `pase3`. D'apres `NOTES/MIGRATION_PASE_2.0.md`, la 2.0 corrige plusieurs bugs d'irradiance : **les biomasses ne sont pas comparables entre les deux piles** (l'energie PV, elle, est identique).

## 1. Vue d'ensemble

| # | Date | Lieu | Annees | Pan. | Culture | Pts zone | Python | Conserve |
|---|---|---|---|---|---|---|---|---|
| 2 | ? | Gembloux | 2020 | 4 | simple | 81 | - | **oui** |
| 5 | 2026-07-21 00:17 | Gembloux | 2020 | 12 | simple | 81 | 3.10.20 | **oui** |
| 10 | 2026-07-23 09:50 | Lampernisse | 2020 | 12 | simple | 1701 | 3.10.20 | **oui** |
| 11 | 2026-07-27 11:50 | Gembloux | 2020 | 4 | simple | 42 | 3.12.13 | **oui** |
| 14 | 2026-07-27 15:35 | Werbomont | 2005 à 2006 | 4 | pystics | 6 | 3.12.13 | **oui** |
| 16 | 2026-07-31 09:49 | Werbomont | 2005 à 2006 | 4 | simple | 6 | 3.10.20 | **oui** |

## 2. Resultats par run

### SIMU_2 — Gembloux 2020, 4 panneaux, culture `simple`

`SIMU_2_Gembloux_2020_4pan_simple_4pilotages_maxtilt90`

- Config : azimut 90°, GCR(X) 0.530, MaxTiltAngle 90°, puissance 1.60 kWc
- Zone : 81 points — precision position solaire : 2
- Execution : ?, python ?, total ?

| Pilotage | Energie [MWh] | Biomasse fin |
|---|---|---|
| tracking_pur | 2.25 | 1452.6 |
| antitrack_pur | 0.60 | 1611.1 |
| antitrack_printemps | 1.89 | 1464.1 |
| antitrack_printemps_et_track_midi_ete | 1.51 | 1541.5 |

*Amplitude entre pilotages : energie **-73 %** au pire, biomasse **+10 %** au mieux.*

**Avis redige :**
> je voulais voir si en reduisant la zone d'interet l'impact de l'ombre des panneaux sur la biomass etait plus visible (en gros plus gros ratio entre tracking et an-tracking par exmeple)
> Energie : toujours des résultats coherent
> Agricole (biomasse/rendement) : aussi
> Il faut tester avec plus de panneaux, pour simuler un vrai parc agrivoltaique

### SIMU_5 — Gembloux 2020, 12 panneaux, culture `simple`

`SIMU_5_Gembloux_2020_12pan_simple_4pilotages_maxtilt90`

- Config : azimut 90°, GCR(X) 0.530, MaxTiltAngle 90°, puissance 4.80 kWc
- Zone : 81 points — precision position solaire : 2
- Execution : MULTIPROCESSING (4 worker(s)), python 3.10.20, total 20.0 s

| Pilotage | Energie [MWh] | Biomasse fin |
|---|---|---|
| tracking_pur | 6.76 | 1313.4 |
| antitrack_pur | 1.80 | 1606.2 |
| antitrack_printemps | 5.67 | 1333.4 |
| antitrack_printemps_et_track_midi_ete | 4.52 | 1480.9 |

*Amplitude entre pilotages : energie **-73 %** au pire, biomasse **+18 %** au mieux.*

**Avis redige :**
> tester avec plus de panneaux pour voir la dif sur la biomass et du coup forcement le ratio et meilleur et on a des plus grosse diff&érence entre biomass !

### SIMU_10 — Lampernisse 2020, 12 panneaux, culture `simple`

`SIMU_10_Lampernisse_2020_12pan_simple_4pilotages_maxtilt90`

- Config : azimut 90°, GCR(X) 0.530, MaxTiltAngle 90°, puissance 4.80 kWc
- Zone : 1701 points — precision position solaire : 1
- Execution : MULTIPROCESSING (4 worker(s)), python 3.10.20, total 127.3 s (2.1 min)

| Pilotage | Energie [MWh] | Biomasse fin |
|---|---|---|
| tracking_pur | 6.78 | 1581.6 |
| antitrack_pur | 1.76 | 1659.4 |
| antitrack_printemps | 5.69 | 1601.5 |
| antitrack_printemps_et_track_midi_ete | 4.51 | 1641.0 |

*Amplitude entre pilotages : energie **-74 %** au pire, biomasse **+5 %** au mieux.*

### SIMU_11 — Gembloux 2020, 4 panneaux, culture `simple`

`SIMU_11_Gembloux_2020_4pan_simple_4pilotages_maxtilt90`

- Config : azimut 90°, GCR(X) 0.530, MaxTiltAngle 90°, puissance 1.60 kWc
- Zone : 42 points — precision position solaire : 1
- Execution : MULTIPROCESSING (4 worker(s)), python 3.12.13, total 25.7 s

| Pilotage | Energie [MWh] | Biomasse fin |
|---|---|---|
| tracking_pur | 2.25 | 1190.6 |
| antitrack_pur | 0.60 | 1557.8 |
| antitrack_printemps | 1.89 | 1283.2 |
| antitrack_printemps_et_track_midi_ete | 1.51 | 1474.4 |

*Amplitude entre pilotages : energie **-73 %** au pire, biomasse **+24 %** au mieux.*

### SIMU_14 — Werbomont 2005 à 2006, 4 panneaux, culture `pystics`

`SIMU_14_Werbomont_2005-2006_4pan_pystics_4pilotages_maxtilt90`

- Config : azimut 90°, GCR(X) 0.530, MaxTiltAngle 90°, puissance 1.60 kWc
- Zone : 6 points — precision position solaire : 1
- Execution : SEQUENTIELLE (1 worker(s)), python 3.12.13, total 233.5 s (3.9 min)

| Pilotage | Energie [MWh] | Biomasse fin |
|---|---|---|
| tracking_pur | 3.81 | 5.9 |
| antitrack_pur | 1.24 | 8.0 |
| antitrack_printemps | 3.43 | 6.2 |
| antitrack_printemps_et_track_midi_ete | 2.74 | 7.6 |

*Amplitude entre pilotages : energie **-67 %** au pire, biomasse **+26 %** au mieux.*

### SIMU_16 — Werbomont 2005 à 2006, 4 panneaux, culture `simple`

`SIMU_16_Werbomont_2005-2006_4pan_simple_4pilotages_maxtilt90`

- Config : azimut 90°, GCR(X) 0.530, MaxTiltAngle 90°, puissance 1.60 kWc
- Zone : 6 points — precision position solaire : 1
- Execution : SEQUENTIELLE (1 worker(s)), python 3.10.20, total 30.9 s

| Pilotage | Energie [MWh] | Biomasse fin |
|---|---|---|
| tracking_pur | 3.81 | 435.0 |
| antitrack_pur | 1.24 | 577.1 |
| antitrack_printemps | 3.43 | 444.6 |
| antitrack_printemps_et_track_midi_ete | 2.74 | 537.5 |

*Amplitude entre pilotages : energie **-67 %** au pire, biomasse **+25 %** au mieux.*

## 3. Runs supprimes (archive)

*Ces 10 runs ont ete supprimes du disque le 2026-07-31 pour liberer ~816 Mo. Les chiffres ci-dessous sont tout ce qui en subsiste. La plupart sont des doublons de runs conserves ; les configurations reellement uniques sont signalees.*

| # | Date | Lieu | Annees | Pan. | Culture | Pts | Python | Energie / Biomasse |
|---|---|---|---|---|---|---|---|---|
| 1 | 2026-07-20 11:25 | Gembloux | 2020 | 4 | simple | 255 | - | -73 % / +3 % |
| 3 | 2026-07-20 16:31 | Gembloux | 2020 | 4 | simple | 81 | 3.10.20 | -73 % / +10 % |
| 4 | 2026-07-20 23:55 | Gembloux | 2020 | 4 | simple | 81 | 3.10.20 | -73 % / +10 % |
| 6 | 2026-07-21 00:29 | Gembloux | 2020 | 12 | simple | 81 | 3.10.20 | -73 % / +18 % |
| 7 | 2026-07-21 10:06 | Chanco | 2021 | 12 | simple | 289 | 3.10.20 | -76 % / +26 % |
| 8 | 2026-07-21 11:33 | Chamonix_Mont_Blanc | 2020 | 12 | simple | 1701 | 3.10.20 | -70 % / +4 % |
| 9 | 2026-07-21 16:02 | Lampernisse | 2020 | 12 | simple | 1701 | 3.10.20 | -74 % / +5 % |
| 12 | 2026-07-27 11:59 | Gembloux | 2020 | 4 | simple | 42 | 3.10.20 | -73 % / +24 % |
| 13 | 2026-07-27 15:00 | Werbomont | 2005 a 2006 | 4 | pystics | 6 | 3.12.13 | - |
| 15 | 2026-07-31 09:48 | Werbomont | 2005 a 2006 | 4 | pystics | - | - | - |

**SIMU_1** — Premier run, 3 pilotages seulement (pas de strategie mixte).

| Pilotage | Energie [MWh] | Biomasse fin |
|---|---|---|
| tracking_pur | 2.25 | 1574.0 |
| antitrack_pur | 0.60 | 1624.6 |
| antitrack_printemps | 1.89 | 1577.7 |

**SIMU_3** — Zone d'interet reduite a 81 points (test de sensibilite).

| Pilotage | Energie [MWh] | Biomasse fin |
|---|---|---|
| tracking_pur | 2.25 | 1452.6 |
| antitrack_pur | 0.60 | 1611.1 |
| antitrack_printemps | 1.89 | 1464.1 |
| antitrack_printemps_et_track_midi_ete | 1.51 | 1541.5 |

**SIMU_4** — Test du multiprocessing — resultats identiques a SIMU_3.

**SIMU_6** — Resultats identiques a SIMU_5 (conserve).

**SIMU_7** — **Seule perte reelle** : configuration unique (Chanco 2021), table chiffree non recuperee avant suppression.

**SIMU_8** — Climat montagnard : le gain de biomasse de l'anti-tracking s'effondre (+4 %).

| Pilotage | Energie [MWh] | Biomasse fin |
|---|---|---|
| tracking_pur | 6.69 | 774.7 |
| antitrack_pur | 2.00 | 802.3 |
| antitrack_printemps | 5.84 | 771.5 |
| antitrack_printemps_et_track_midi_ete | 4.85 | 785.0 |

**SIMU_9** — Resultats identiques a SIMU_10 (conserve).

**SIMU_12** — Meme config que SIMU_11 mais relance en python 3.10 (ancienne pile).

**SIMU_13** — Table de resultats deja illisible avant suppression. Meme config que SIMU_14 (conserve), lance 35 min plus tot.

**SIMU_15** — Run avorte (dossier vide, 0 octet).

