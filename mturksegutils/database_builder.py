import sqlite3

from mturksegutils import mturk_seg_vars


db_path = mturk_seg_vars.db_path


def create_hits_table():
    """
    Creates a table for storing the data on each MTurk HIT
    Currently assumes only a single assignment per HIT in the main experiment
    - hit_id: the unique HIT ID assignned by Amazon when the HIT is created
    - mturk type: "production" if the hit is posted to the production environment, "sandbox" otherwise
    - exp_group: which experiment group the hit is a part of
    - image_url: the image_url data for configuring this HIT
    - classes: a string containing the object classes to be listed in the UI for this HIT, separated by '-'
    - annotation_mode: a string containing the annotation modes available in the UI, separated by '-'
    - pre_annotations: any annotations that are pre-imported and displayed on the image (not currently functional)
    - status: the status of this HIT (or the status of its assignment once one is available)
    - assignment_id: the unique ID of the assignment for this HIT, if one has been completed
    - auto_approve_time: the time at which the assignment for this hit will auto-approve, if one is available
    - interaction_log: the interaction log data for the assignment, if one is available
    - annotation_in_progress: the json data for in-progress annotations for the assignment, if one is available
    - result_data: the json data for final annotations for the assignment, if one is available
    - worker_id: the unique Amazon ID for the worker who completed the assignment, if one is available
    """

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Table 'hits' stores data on each individual HIT and any associated assignment
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS hits (
        hit_id TEXT PRIMARY KEY,
        mturk_type TEXT,
        exp_group TEXT,
        image_url TEXT,
        classes TEXT,
        annotation_mode TEXT,
        pre_annotations TEXT,
        status TEXT,
        assignment_id TEXT,
        auto_approve_time DATETIME
        interaction_log TEXT,
        annotation_in_progress TEXT,
        result_data TEXT,
        worker_id TEXT
    )
    ''')

    conn.commit()
    conn.close()


def create_exp_groups_table():
    """
    Creates a table for storing the major task parameters that customize each experiment group
    - exp_group: the unique ID for the experiment group (each ID can be used once in production and once in sandbox)
    - mturk_type: "production" if the experiment group is posted to the production environment, "sandbox" otherwise
    - num_objects: the number of objects in the images for the experiment group (use -1 for unspecified)
    - reward_size: the reward size, in dollars, for HITs in this experiment group
    - time_limit: if True, a 180 second time limit is applied, if False, no time limit is applied
    """

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Table 'exp_groups' stores data on each experiment group configuration
    # For num_objects, -1 indicates the images can have any number of objects
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS exp_groups (
        exp_group TEXT,
        mturk_type TEXT,
        num_objects INTEGER,
        reward_size REAL,
        time_limit BOOLEAN,
        PRIMARY KEY (exp_group, mturk_type)
    )
    ''')

    conn.commit()
    conn.close()


def create_task_config_table():
    """
    Creates a table for storing the configuration data for each individual HIT
    - exp_group: which experiment group the HIT in this line is assigned to
    - img_url: the url of the image to be used for this HIT (currently each image can be used only once per exp_group)
    - classes: a string containing the object classes to be listed in the UI for this HIT, separated by '-'
    - annotation_mode: a string containing the annotation modes available in the UI, separated by '-'
    - pre_annotations: any annotations that are pre-imported and displayed on the image (not currently functional)
    """

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Table 'task_config' stores data on each individual HIT
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS task_config (
        exp_group TEXT,
        img_url TEXT,
        annotation_mode TEXT,
        classes TEXT,
        pre_annotation TEXT,
        PRIMARY KEY (exp_group, img_url)
    )
    ''')

    conn.commit()
    conn.close()


def create_training_task_table():
    """
    Creates a table for storing training task results
    Training tasks differ from experiment group HITs because there can be multiple assignments per task
    - hit_id: the unique HIT ID assignned by Amazon when the HIT is created
    - mturk type: "production" if the hit is posted to the production environment, "sandbox" otherwise
    - exp_group: which experiment group the hit is a part of
    - image_url: the image_url data for configuring this HIT
    - classes: a string containing the object classes to be listed in the UI for this HIT, separated by '-'
    - annotation_mode: a string containing the annotation modes available in the UI, separated by '-'
    - pre_annotations: any annotations that are pre-imported and displayed on the image (not currently functional)
    - status: the status of this HIT (or the status of its assignment once one is available)
    - assignment_id: the unique ID of the assignment for this HIT, if one has been completed
    - auto_approve_time: the time at which the assignment for this hit will auto-approve, if one is available
    - interaction_log: the interaction log data for the assignment, if one is available
    - annotation_in_progress: the json data for in-progress annotations for the assignment, if one is available
    - result_data: the json data for final annotations for the assignment, if one is available
    - worker_id: the unique Amazon ID for the worker who completed the assignment, if one is available
    - qual_score: 1 if the worker passed the qual task, 0 if they failed, -1 if the result has not yet been reviewed
    """

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS training_tasks (
        hit_id TEXT,
        mturk_type TEXT,
        exp_group TEXT,
        image_url TEXT,
        classes TEXT,
        annotation_mode TEXT,
        pre_annotations TEXT,
        status TEXT,
        assignment_id TEXT,
        auto_approve_time DATETIME,
        interaction_log TEXT,
        annotation_in_progress TEXT,
        result_data TEXT,
        worker_id TEXT,
        qual_score INTEGER,
        PRIMARY KEY (hit_id, assignment_id)
    )
    ''')

    conn.commit()
    conn.close()