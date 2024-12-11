#!/bin/bash
##SBATCH --mem=40G -p compsci-gpu --gres=gpu:1 # To request 1 GPU
#SBATCH --mem=40G -p compsci-gpu --gres=gpu:a5000:1 # To request the a5000 GPU


# This script takes two positional arguments: the model type and the dataset subgroup.
# Check if two arguments were passed
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 custom_config_args custom_path_args"
    exit 1
fi

# Activate the python venv
source PATH_TO_YOUR_VENV

# Parse the config and path arguments
config_args="$1"
path_args="$2"
json_output=$(python3 parse_training_arg_file.py $config_args $path_args)
MMSEG_DIR=$(echo "$json_output" | jq -r '.engine_dir')
CONFIG_FILE=$(echo "$json_output" | jq -r '.model_config_path')
WORK_DIR=$(echo "$json_output" | jq -r '.work_dir_path')
RESUME_FLAG=$(echo "$json_output" | jq -r '.resume')

echo "MMSEG_DIR: $MMSEG_DIR"
echo "CONFIG_FILE: $CONFIG_FILE"
echo "WORK_DIR: $WORK_DIR"
echo "RESUME_FLAG: $RESUME_FLAG"

# Ensure the working directory exists
mkdir -p ${WORK_DIR}

# Run the training
python3 ${MMSEG_DIR}/tools/train.py ${CONFIG_FILE} --work-dir ${WORK_DIR} ${RESUME_FLAG}