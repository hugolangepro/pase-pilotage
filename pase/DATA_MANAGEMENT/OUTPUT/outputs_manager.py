#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Copyright (c) 2020-2024 - University of Liège - Digital Energy and Agriculture Lab (DEAL)
Author : Arnaud Bouvry <abouvry@uliege.be>
This file is part of the PASE software, and is distributed under the MIT license.

Simulation output and data management utilities for PASE.

This module provides the OutputsManager class, which centralizes the
creation, organization, and persistence of simulation outputs. Each
simulation run is associated with a deterministic *variant* directory
whose identity is derived from a hash of the simulation inputs. This
mechanism enables automatic reuse of existing runs, reproducible
experiment tracking, and systematic comparison between variants.

The manager also records simulation metadata (including configuration
parameters and Git commit hashes), maintains a project-level registry
of variants, supports caching of external data sources (e.g. PVGIS
weather data), and provides helper methods for standardized file
persistence within the simulation output structure.

Typical directory structure:

    OUTPUTS/<project>/
        variant_01/
            1-inputs/
            2-data/
            3-interm_results/
            4-results/

This module is designed to ensure reproducibility, traceability, and
efficient data reuse across simulation workflows.
"""

import datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Optional

from pase.DATA_MANAGEMENT.benchmarking import (get_git_revision_hash,
                                               parse_crop_model_inputs,
                                               save_simulation_metadata)
from pase.user_support_tools import PASE_Logger


def deep_diff(old: dict, new: dict):
    """
    Compute a structured diff between two dictionaries.
    Returns a dict describing only the changes.
    """
    diff = {}

    old_keys = set(old.keys())
    new_keys = set(new.keys())

    # Deletions
    for key in old_keys - new_keys:
        diff[key] = {
            "Former": old[key],
            "New": None
        }

    # Additions
    for key in new_keys - old_keys:
        diff[key] = {
            "Former": None,
            "New": new[key]
        }

    # Possible modifications
    for key in old_keys & new_keys:
        old_val = old[key]
        new_val = new[key]

        # Nested dict recursion
        if isinstance(old_val, dict) and isinstance(new_val, dict):
            nested = deep_diff(old_val, new_val)
            if nested:        # Only record if real changes
                diff[key] = nested

        # Values changed (including type change)
        elif old_val != new_val:
            diff[key] = {
                "Former": old_val,
                "New": new_val
            }

    return diff


class OutputsManager:
    SUBDIRS = {
        "inputs": "1-inputs",
        "data": "2-data",
        "intermediate": "3-interm_results",
        "results": "4-results",
    }

    REGISTRY_FILE = "variants.json"
    LATEST_LINK = "latest"

    def __init__(self, location_name: str,
                 sim_start_year: int,
                 sim_end_year: int):
        self.root = self.set_pase_root()

        self.project = self.get_project_name(location_name,
                                             sim_start_year, sim_end_year)

        self.project_root = self.root / "OUTPUTS" / self.project
        self.project_root.mkdir(parents=True, exist_ok=True)

        # load registry
        self.registry_path = self.project_root / self.REGISTRY_FILE
        if self.registry_path.exists():
            self.registry = json.loads(self.registry_path.read_text())
        else:
            self.registry = {}

        self.variant_root: Optional[Path] = None
        self.variant: Optional[str] = None

    # ---------------------------------------------------------------------
    # Input hashing
    # ---------------------------------------------------------------------
    @staticmethod
    def _hash_inputs(inputs: dict) -> str:
        """Stable, deterministic JSON hashing."""
        payload = json.dumps(inputs, sort_keys=True).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    # ---------------------------------------------------------------------
    # Variant discovery utilities
    # ---------------------------------------------------------------------
    def _discover_existing_variants(self):
        """Return dict: variant_name -> stored_input_hash."""
        variants = {}
        for vdir in self.project_root.iterdir():
            if vdir.is_dir():
                hash_file = vdir / self.SUBDIRS["inputs"] / "input_hash.txt"
                if hash_file.exists():
                    variants[vdir.name] = hash_file.read_text().strip()
        return variants

    def _find_or_create_variant_name(self, input_hash: str, user_variant: Optional[str]):
        """
        Variant selection logic:
            1) If user provided variant → use it.
            2) Else if hash exists → reuse corresponding variant.
            3) Else → create new variant_XX.
        """
        # User override always wins
        if user_variant:
            return user_variant

        variants = self._discover_existing_variants()

        # Check for identical hash
        for variant_name, saved_hash in variants.items():
            if saved_hash == input_hash:
                return variant_name

        # New hash → create next incremented variant name
        idx = len(variants) + 1
        return f"variant_{idx:02d}"

      # ---------------------------------------------------------------------
    # Registry update
    # ---------------------------------------------------------------------
    def _update_registry(self, variant_name: str, input_hash: str):
        now = datetime.datetime.now().isoformat()

        self.registry[variant_name] = {
            "hash": input_hash,
            "timestamp": now,
        }

        self.registry_path.write_text(json.dumps(self.registry, indent=2))

    # ---------------------------------------------------------------------
    # Variant setup (hash must be computed before creating dirs)
    # ---------------------------------------------------------------------
    def setup_variant(self,
                      loc: dict,
                      av: dict,
                      pv_module: dict,
                      structure: dict,
                      crop_config: dict,
                      variant: Optional[str] = None,
                      source: Optional[str] = None,
                      ):
        """
        Compute input-hash *before* touching disk.
        Then pick correct variant (reuse or new).
        Then create folders *only if needed*.
        """
        # 0) Parse the source to get only the file name
        source_file = Path(source).parts[-1]

        # 1) Compute hash early, before any disk modifications.
        crop_model_inputs = parse_crop_model_inputs(crop_config)
        git_hash = get_git_revision_hash()
        inputs = {**loc, **av, **pv_module, **structure, **crop_config,
                  **crop_model_inputs,
                  'source': source_file, 'git commit': git_hash}
        input_hash = self._hash_inputs(inputs)

        # 2) Determine variant name based on hash existence.
        chosen_variant = self._find_or_create_variant_name(input_hash, variant)
        self.variant = chosen_variant
        self.variant_root = self.project_root / chosen_variant

        # 3) Only create directories if they do not already exist.
        for sub in self.SUBDIRS.values():
            (self.variant_root / sub).mkdir(parents=True, exist_ok=True)

        # 4) Write input hash (ensures reproducibility)
        hash_file = self.variant_root / self.SUBDIRS["inputs"] / "input_hash.txt"
        hash_file.write_text(input_hash)

        # 5) Save simulation metadata
        metadata_file = self.variant_root / self.SUBDIRS["inputs"] / "simulation_metadata.yaml"
        save_simulation_metadata(loc=loc, av=av, pv_module=pv_module,
                                 structure=structure, crop_config=crop_config,
                                 source=source_file, output_path=metadata_file)

        # 6) If not the first variant: compute diff vs previous
        # Identify previous variant
        if self.variant.startswith("variant_"):
            try:
                idx = int(self.variant.split("_")[1])
            except ValueError:
                idx = 1

            if idx > 1:
                prev_variant = f"variant_{idx-1:02d}"
                prev_root = self.project_root / prev_variant
                prev_meta = prev_root / self.SUBDIRS["inputs"] / "simulation_metadata.yaml"

                if prev_meta.exists():
                    import yaml

                    # Load old and new metadata
                    old_data = yaml.safe_load(prev_meta.read_text())
                    new_data = yaml.safe_load(metadata_file.read_text())

                    # Compute diff
                    changes = deep_diff(old_data, new_data)

                    # Save diff only if non-empty
                    if changes:
                        diff_path = self.variant_root / self.SUBDIRS["inputs"] / "diff.yaml"
                        diff_path.write_text(yaml.dump(changes, allow_unicode=True))

        # update registry
        self._update_registry(chosen_variant, input_hash)

        return self.variant_root

    # ---------------------------------------------------------------------
    # Path resolution helpers
    # ---------------------------------------------------------------------
    def _path(self, sub: str, filename: str) -> Path:
        return (self.variant_root / self.SUBDIRS[sub] / filename).resolve()

    @property
    def CACHE_DIR(self) -> Path:
        return self.root / 'OUTPUTS' / '_cache'

    def _cache_path(self, filename: str) -> Path:
        return (self.CACHE_DIR / filename).resolve()

    def set_pase_root(self):
        # Outputs and cache follow the caller's working directory, never the
        # package directory, which is read-only or shared once pip-installed.
        return Path.cwd()

    def get_project_name(self, location_name, sim_start_year, sim_end_year):
        return (location_name
                + '_' + str(sim_start_year)
                + '-' + str(sim_end_year))


    # ---------------------------------------------------------------------
    # Persistence API
    # ---------------------------------------------------------------------
    def save_json(self, sub: str, name: str, data: Any):
        self._path(sub, name).write_text(json.dumps(data, indent=2))

    def load_json(self, sub: str, name: str, default=None):
        path = self._path(sub, name)
        if path.exists():
            return json.loads(path.read_text())
        else:
            return default

    def save_json_to_cache(self, name: str, data: Any):
        path = self._cache_path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2))

    def load_json_from_cache(self, name: str, default=None):
        path = self._cache_path(name)
        if path.exists():
            return json.loads(path.read_text())
        else:
            return default
    def save_bytes(self, sub: str, name: str, blob: bytes):
        self._path(sub, name).write_bytes(blob)

    def load_bytes(self, sub: str, name: str, default=None):
        path = self._path(sub, name)
        return path.read_bytes() if path.exists() else default

    # ---------------------------------------------------------------------
    # Caching example for external data
    # ---------------------------------------------------------------------
    def load_or_fetch_weather(self, key: str, fetch_fn):
        """
        Load or cache weather data from PVGIS API.
        key = "lat_lon_year_resolution" or similar.
        """
        fname = f"wd_{key}.json"
        cached = self.load_json_from_cache(fname)
        if cached is not None:
            PASE_Logger('Found cached weather data ; '
                        'loading from cached json file.',
                        level='INFO')

            # Save to <project>/<variant> for traceability
            self.save_json("data", fname, cached)

            return cached  # cached is a dict

        PASE_Logger('No cached data, fetching from PVGIS API ...',
                    level='INFO')

        data = fetch_fn()  # fetch data with the passthrough function fetch_fn

        # Save to <project>/<variant> for traceability
        self.save_json("data", fname, data)

        # Save to cache for efficiency
        self.save_json_to_cache(fname, data)

        return data
