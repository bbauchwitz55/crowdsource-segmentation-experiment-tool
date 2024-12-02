from mturksegutils import mturk_seg_vars, database_builder, database_initializer
import sqlite3
import csv

database_path = mturk_seg_vars.db_path

exp_group_config_file = "/path/to/exp_group_config.csv"

task_config_files = [
    "/path/to/task_config_1.csv",
    "/path/to/task_config_2.csv",
    "/path/to/task_config_3.csv"
    "/path/to/task_config_4.csv"
]

# For storing the experiment group and task level configurations
database_builder.create_exp_groups_table()
database_builder.create_task_config_table()

# For storing results later
database_builder.create_hits_table()

# Optional, if your experiment will use training tasks
database_builder.create_training_task_table()

# Open a connection to the newly created database
conn = sqlite3.connect(database_path)
cursor = conn.cursor()

# Read each line of the exo_group_config_file and add to the table
with open(exp_group_config_file, 'r') as csv_file:
    csv_reader = csv.reader(csv_file)
    header = True
    for row in csv_reader:
        if header:
            header = False
            continue

        # Insert the experiment group configuration into the exp_groups table
        database_initializer.insert_exp_group_into_table(conn, cursor, row)

# Add the data from each task config file to the database
for task_config_file in task_config_files:
    database_initializer.insert_task_config_into_table(conn, cursor, task_config_file)

# Close the database connection
conn.close()

