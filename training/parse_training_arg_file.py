from mmseg.apis import init_model, inference_model, show_result_pyplot
from PIL import Image
from mmengine.config import Config, DictAction
import mmcv
import numpy as np
import utils
import csv
import argparse
import os
import datetime
import re
import json


def replace_pattern_with_config(template, config, pattern=r'\*{3}(.*?)\*{3}'):
    """
    Replaces the pattern in the template with the corresponding value in the config dictionary.
    :param template: String containing the template
    :param config: Dictionary containing the configuration parameters
    :param pattern: Regular expression pattern to match the values in the template
    :return: The template with the values replaced
    """
    match = re.search(pattern, template)
    while match:
        to_replace = match.group()
        key = match.group(1).lower()
        value = config[key]
        template = template.replace(to_replace, value)
        match = re.search(pattern, template)
    return template


def make_model_config_file(configs, temp_dir):
    """
    Creates a model configuration file based on the model_type specified in the configs dictionary.
    :param configs: Dictionary containing the configuration parameters
    :param temp_dir: Path to the temporary directory where the model_config file will be stored
    :return: Path to the model_config file
    """

    source_dir = configs["source_dir"]
    config_file_template = f'{source_dir}/custom_configs/config_templates/config_file_template.txt'
    # Read config_file_template as a string
    with open(config_file_template, 'r') as file:
        config_file = file.read()

    # Replace the pattern in the config_file with the corresponding values in the configs dictionary
    config_file = replace_pattern_with_config(config_file, configs)

    # References to work_dir_path, dataset_config_path, model_arch_config_path, and schedule_config_path, and runtime_config_path need to be inside quotes
    config_file = config_file.replace(configs["work_dir_path"], f'"{configs["work_dir_path"]}"')
    config_file = config_file.replace(configs["dataset_config_path"], f'"{configs["dataset_config_path"]}"')
    config_file = config_file.replace(configs["model_arch_config_path"], f'"{configs["model_arch_config_path"]}"')
    config_file = config_file.replace(configs["schedule_config_path"], f'"{configs["schedule_config_path"]}"')
    config_file = config_file.replace(configs["runtime_config_path"], f'"{configs["runtime_config_path"]}"')

    # Save the config_file to the temp_dir as config_file.txt
    config_file_path = f'{temp_dir}/config_file.py'
    with open(config_file_path, 'w') as file:
        file.write(config_file)

    return config_file_path



def update_config_with_mmseg_data(configs):
    """
    Updates the config file to include data from the mmseg installation
    :param configs: Dictionary containing the configuration parameters
    :return configs: Dictionary containing the configuration parameters with the mmseg data
    """
    source_dir = configs["source_dir"]

    # Get the absolute path to the model architecture configuration file, which is within the mmseg installation directory
    mmseg_dir = configs["mmseg_dir"]
    model_type = configs["model_type"]
    model_arch_relative_path_key = f'model_config_path_within_package_{model_type}'
    model_arch_relative_path = configs[model_arch_relative_path_key]
    model_arch_config_path = f'{mmseg_dir}/{model_arch_relative_path}'
    configs["model_arch_config_path"] = model_arch_config_path

    # Get the absolute path to the runtime configuration file, which is within the mmseg installation directory
    runtime_config_relative_path = configs["runtime_config_path_within_package"]
    runtime_config_path = f'{mmseg_dir}/{runtime_config_relative_path}'
    configs["runtime_config_path"] = runtime_config_path

    # Read the model settings text for the specified model
    model_settings_file = f'{source_dir}/custom_configs/config_templates/model_setting_template_{model_type}.txt'
    with open(model_settings_file, 'r') as file:
        model_settings = file.read()
        configs["model_setting_text"] = model_settings

    return configs


def make_dataset_config_file(configs, temp_dir):
    """
    Creates a dataset configuration file based on the dataset specified in the configs dictionary.
    :param configs: Dictionary containing the configuration parameters
    :param temp_dir: Path to the temporary directory where the dataset_config file will be stored
    :return: Path to the dataset_config file
    """
    source_dir = configs["source_dir"]
    dataset_template = f'{source_dir}/custom_configs/config_templates/dataset_config_template.txt'
    # Read dataset_template as a string
    with open(dataset_template, 'r') as file:
        dataset_config = file.read()

    # Replace the pattern in the dataset_config with the corresponding values in the configs dictionary
    dataset_config = replace_pattern_with_config(dataset_config, configs)

    # Save the dataset_config to the temp_dir as dataset_config.txt
    dataset_config_path = f'{temp_dir}/dataset_config.py'
    with open(dataset_config_path, 'w') as file:
        file.write(dataset_config)

    return dataset_config_path


def make_schedule_config_file(configs, temp_dir):
    """
    Creates a schedule configuration file based on the schedule_type specified in the configs dictionary.
    :param configs: Dictionary containing the configuration parameters
    :param temp_dir: Path to the temporary directory where the schedule_config file will be stored
    :return: Path to the schedule_config file
    """
    schedule_type = configs["schedule_type"]

    source_dir = configs["source_dir"]
    schedule_template = f'{source_dir}/custom_configs/config_templates/schedule_config_template_{schedule_type}.txt'
    # Read schedule_template as a string
    with open(schedule_template, 'r') as file:
        schedule_config = file.read()

    # Replace the pattern in the schedule_config with the corresponding values in the configs dictionary
    schedule_config = replace_pattern_with_config(schedule_config, configs)

    # Save the schedule_config to the temp_dir as schedule_config.txt
    schedule_config_path = f'{temp_dir}/schedule_config.py'
    with open(schedule_config_path, 'w') as file:
        file.write(schedule_config)
    
    return schedule_config_path



def make_temporary_config_dir(work_dir, source_dir):
    """
    Creates a temporary directory for storing the temporary config files, mirroring the name of work_dir
    :param work_dir: Path to the working directory
    :return: the path to the temporary directory
    """

    dirname = work_dir.split("/")[-1]
    root = f'{source_dir}/custom_configs/temp'
    temp_dir = f'{root}/{dirname}'

    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    return temp_dir


def generate_work_dir_path(configs):
    """
    Creates a working directory for model training by reading the configuration parameters.
    :param configs: Dictionary containing the configuration parameters
    :return: Path to the working directory
    """

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Get the key configuration parameters
    model_output_root_path = configs["model_output_root_path"]
    dataset = configs["dataset"]
    batch_size = configs["batch_size"]
    iters = configs["iters"]
    model_type = configs["model_type"]
    exp_name = configs["exp_name"]

    # Parse the transform function from the train ann file
    train_ann_file = configs["train_ann_file"]
    transform = f'{exp_name}_ground_truth'
    if not "ground_truth" in train_ann_file:
        # Split by '/'
        filename = train_ann_file.split("/")[-1]
        # Remove "exp2_", "_train", and ".txt" if they are present
        filename = filename.replace(f'{exp_name}_', "")
        filename = filename.replace("_train", "")
        filename = filename.replace(".txt", "")
        transform = filename

    # Template for path is base_dir/dataset/model/batch_size/train_iters/exp2_model_transform_timestamp
    work_dir = f'{model_output_root_path}/{exp_name}/{dataset}/{model_type}/batch{batch_size}/iters{iters}/{model_type}_{transform}_{timestamp}'

    return work_dir


def parse_dict_from_file(file_path):
    """
    Parses a file containing a list of lines of the format kay=value into a dictionary.
    :param file_path: Path to the file
    :return: Dictionary containing the key-value pairs
    """
    with open(file_path, 'r') as file:
        # Split each line by the equal sign
        lines = file.readlines()
        dict_params = dict()
        for line in lines:
            key, value = line.strip().split("=")
            dict_params[key] = value
        return dict_params


def main(configs_param_file, paths_file):

    defaults_file = "custom_configs/config_templates/defaults.txt"

    # Step 1: parse the configs_param_file and paths_file as dictionaries
    paths = parse_dict_from_file(paths_file)
    configs_param = parse_dict_from_file(configs_param_file)
    source_dir = paths["source_dir"]
    defaults_file = f'{source_dir}/{defaults_file}'
    defaults = parse_dict_from_file(defaults_file)

    # Set the configuration to the default and add the baseline user-specified paths, then overwrite any values from the custom config arguments
    configs = defaults.copy()
    configs.update(paths)
    configs.update(configs_param)

    # Update the resume argument
    if configs["resume"] == "True":
        configs["resume"] = "--resume"
    else:
        configs["resume"] = ""

    # Step 2: generate a path where the work directory will be stored
    work_dir = generate_work_dir_path(configs)
    configs["work_dir_path"] = work_dir

    # Step 3: create the temporary directory where the config files will be stored
    temp_dir = make_temporary_config_dir(work_dir, source_dir)

    # Step 4: create the schedule configuration file
    schedule_config_temp_file_path = make_schedule_config_file(configs, temp_dir)
    configs["schedule_config_path"] = schedule_config_temp_file_path

    # Step 5: create the dataset configuration file
    dataset_config_temp_file_path = make_dataset_config_file(configs, temp_dir)
    configs["dataset_config_path"] = dataset_config_temp_file_path

    # Update the paths to items from the mmseg installation
    configs = update_config_with_mmseg_data(configs)

    # Step 6: create the model configuration file
    model_config_temp_file_path = make_model_config_file(configs, temp_dir)
    configs["model_config_path"] = model_config_temp_file_path

    # Step 7: format the configs data as json
    del configs["model_setting_text"]   # Delete this because it has quotes and newlines which disrupt json formatting
    json_configs = json.dumps(configs)
    print(json_configs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process two positional arguments.")
    parser.add_argument("config_params_file", type=str, help="Path to the file with the configuration parameters.")
    parser.add_argument("paths_file", type=str, help="Path to the file with the dataset paths.")
    args = parser.parse_args()

    main(args.config_params_file, args.paths_file)