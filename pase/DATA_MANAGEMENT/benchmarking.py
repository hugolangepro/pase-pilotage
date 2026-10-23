import csv
from datetime import datetime
import os
import pandas as pd
import subprocess
from typing import Optional
import yaml

from pase.user_support_tools import PASE_Logger
from pase.DATA_MANAGEMENT.yaml_inputs_provider import YAML_Inputs_provider
from pase.DATA_MANAGEMENT.helpers import _to_native

def export_benchmark(df, fname_prefix='diffuse_benchmark_', mode='x', fpath=None):
    if mode == 'x':
        behavior = '(creating new file)'
    elif mode == 'a':
        behavior = '(append to existing file)'
    else :
        raise ValueError('Unexpected mode.')

    PASE_Logger('Saving result ' + behavior, level='INFO')

    exact_fpath_provided = True if fpath is not None else False

    date_str = datetime.today().strftime('%Y-%m-%d')

    written = False
    counter = 0
    while written == False:
        suffix = f'_{counter:02}'
        if exact_fpath_provided == False:
            fname = fname_prefix + date_str + suffix + '.csv'
            fpath = os.path.join('OUTPUTS', fname)

        try:

            if mode == 'a':
                # append blank line before appending the new content
                with open(fpath, 'a',
                          newline='') as outfile:
                    writer = csv.writer(outfile)
                    writer.writerow('')


            df.to_csv(fpath, mode=mode, float_format="%.3e", sep=';')
            written = True
            PASE_Logger(f'Result saved in {fpath}', level='INFO')
            return fpath

        except FileExistsError as e:
            PASE_Logger(str(e) + ' Increment suffix counter.', level='WARNING')

            counter += 1
            if counter > 10:
                raise ValueError('Too many attempts')

def get_git_revision_hash() -> str:
    """
    Get git revision hash (long form)
    source: https://stackoverflow.com/a/21901260
    :return: git rev hash (str)
    """
    try:
        return (subprocess.check_output(['git', 'rev-parse', 'HEAD'])
                .decode('ascii').strip())
    except Exception as e:
        return f"Could not retrieve commit: {e}"


def get_git_revision_short_hash() -> str:
    """
    Get git revision hash (short form)
    source: https://stackoverflow.com/a/21901260
    :return: git rev hash (str)
    """
    return subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode('ascii').strip()

def sign_commit_hash(fpath):
    commit_hash = get_git_revision_hash()
    date_str = datetime.today().strftime('%Y-%m-%d')
    signature = (f'This benchmarking was generated on {date_str} with code '
                 f'version {commit_hash}')

    with open(fpath, 'a', newline='') as outfile:
        writer = csv.writer(outfile)
        writer.writerow('')
        writer.writerow([signature])

def save_simulation_metadata(loc: Optional[dict], av: Optional[dict] = None,
                             pv_module: Optional[dict] = None,
                             structure: Optional[dict] = None,
                             crop_config: Optional[dict] = None,
                             source: Optional[str] = None,
                             output_path=os.path.join("OUTPUTS",
                                                      "simulation_metadata.yaml")):
    # Creating dictionary
    metadata = {}

    # Adding date and hour of simulation
    metadata['date'] = datetime.now().isoformat()

    # Finding Git commit hash
    metadata['git_commit'] = get_git_revision_hash()

    # Adding parameters from YAML and csv files contents
    metadata = {**metadata, **parse_crop_model_inputs(crop_config)}

    # Adding others useful parameters
    metadata['scenario_config'] = loc
    metadata['av_config'] = av
    metadata['pv_module_config'] = pv_module
    metadata['structure_config'] = structure
    metadata['crop_config'] = crop_config
    if source is not None:
        metadata['source'] = source

    metadata = _to_native(metadata)

    # Saving metadata dictionary into YAML file
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(metadata, f, allow_unicode=True)

    print(f"Simulation metadata saved to {output_path}")

def parse_crop_model_inputs(crop_config_dict):
    if crop_config_dict is not None:
        overall_dict = dict()
        if crop_config_dict['CropModel'].lower() == 'grassim':
            # Parse GRASSIM inputs
            try:
                overall_dict['crop_init'] = YAML_Inputs_provider(
                    file=os.path.join("CROPS", "GRASSIM", "crop",
                                      crop_config_dict['CropInit'])).inputs

                overall_dict['soil_init'] = YAML_Inputs_provider(
                    file=os.path.join("CROPS", "GRASSIM", "soil",
                                      crop_config_dict['SoilInit'])).inputs

                overall_dict['pft_composition'] = YAML_Inputs_provider(
                    file=os.path.join("CROPS", "GRASSIM", "crop",
                                      crop_config_dict['PFT_composition'])).inputs

                overall_dict['pft_values'] = pd.read_csv(
                    os.path.join("INPUTS", "CROPS", "GRASSIM", "crop",
                                 crop_config_dict['PFT_values']), sep=";",
                    decimal='.').to_dict(orient='list')

                overall_dict['kc_values'] = YAML_Inputs_provider(
                    file=os.path.join("CROPS", "GRASSIM", "crop",
                                      crop_config_dict['Kc_values'])).inputs

                overall_dict['management'] = YAML_Inputs_provider(
                    file=os.path.join("CROPS", "GRASSIM", "management",
                                      crop_config_dict['Management'])).inputs

                # Variables to save is a yaml file not in the "PASE format",
                # hence it's loaded differently.
                with open(os.path.join('INPUTS', 'CROPS', 'GRASSIM',
                                       'variables_to_save.yml'), 'r') as f:
                    overall_dict['variables_to_save'] = yaml.safe_load(f)

                overall_dict['soil_hydraulic_properties'] = pd.read_csv(
                    os.path.join("INPUTS", "CROPS", "GRASSIM", "soil",
                                 crop_config_dict['SoilHydraulicProperties']),
                    sep=';',
                    decimal='.').to_dict(orient='list')

                overall_dict['soil_parameters'] = YAML_Inputs_provider(
                    file=os.path.join("CROPS", "GRASSIM", "soil",
                                      crop_config_dict['SoilParameters'])).inputs
            except Exception as e:
                overall_dict['error_loading_yaml_inputs'] = str(e)
        elif crop_config_dict['CropModel'].lower() == 'simple':
            # Parse SIMPLE inputs
            try:
                overall_dict['crop_init'] = YAML_Inputs_provider(
                    file=os.path.join("CROPS", "SIMPLE",
                                      crop_config_dict['CropInit'])).inputs

                overall_dict['soil_init'] = YAML_Inputs_provider(
                    file=os.path.join("CROPS", "SIMPLE",
                                      crop_config_dict['SoilInit'])).inputs

            except Exception as e:
                overall_dict['error_loading_yaml_inputs'] = str(e)
        elif crop_config_dict['CropModel'].lower() == 'stics':  # TODO : stics
            pass
        return overall_dict
    else:
        return {}
