import csv

def insert_task_config_into_table(conn, cursor, task_config_file, exp_group):
    """
    Inserts the contents of a task configuration file into the task_config table
    The input file must have the following fields:
    - 'image_url' or 'img_url'
    - 'classes'
    - 'annotation_mode'
    It may also optionally have the field 'pre_annotations' or 'annotations'

    :param task_config_file: a tuple containing the experiment group configuration
    :param conn: a connection to the sqlite3 database
    :param cursor: the database client
    :return: N/A
    """

    header = True
    img_url_index = 0
    annotation_mode_index = 1
    classes_index = 2
    pre_annotation_index = 3

    with open(task_config_file, 'r') as f:
        reader = csv.reader(f)

        for row in reader:
            if header:
                # Check if the first header position differs from the default value
                arg0 = row[0]
                if arg0 == 'annotation_mode':
                    annotation_mode_index = 0
                elif arg0 == 'classes':
                    classes_index = 0
                elif arg0 == 'pre_annotations' or arg0 == 'annotations':
                    pre_annotation_index = 0

                # Check if the second header position differs from the default value
                arg1 = row[1]
                if arg1 == 'img_url' or arg1 == 'image_url':
                    img_url_index = 1
                elif arg1 == 'classes':
                    classes_index = 1
                elif arg1 == 'pre_annotations' or arg1 == 'annotations':
                    pre_annotation_index = 1

                # Check if the third header position differs from the default value
                arg2 = row[2]
                if arg2 == 'img_url' or arg2 == 'image_url':
                    img_url_index = 2
                elif arg2 == 'annotation_mode':
                    annotation_mode_index = 2
                elif arg2 == 'pre_annotations' or arg2 == 'annotations':
                    pre_annotation_index = 2

                # If there is a fourth header position, check if it differs from the default value
                if len(row) == 4:
                    arg3 = row[3]
                    if arg3 == 'img_url' or arg3 == 'image_url':
                        img_url_index = 3
                    elif arg3 == 'annotation_mode':
                        annotation_mode_index = 3
                    elif arg3 == 'classes':
                        classes_index = 3
                header = False
                continue

            # Get the values from the data
            img_url = row[img_url_index]
            annotation_mode = row[annotation_mode_index]
            classes = row[classes_index]
            pre_annotations = 'None'
            if len(row) == 4:
                pre_annotations = row[pre_annotation_index]
                if pre_annotations == '':
                    pre_annotations = 'None'

            # Insert the contents into the table
            cursor.execute('''
            INSERT INTO task_config VALUES (?, ?, ?, ?, ?)
            ''', (exp_group, img_url, annotation_mode, classes, pre_annotations))

    conn.commit()


def insert_exp_group_into_table(conn, cursor, exp_group_tuple):
    """
    Inserts an experiment group configuration into the exp_groups table
    :param exp_group_tuple: a tuple containing the experiment group configuration
    :param conn: a connection to the sqlite3 database
    :param cursor: the database client
    """

    cursor.execute('''
    INSERT INTO exp_groups VALUES (?, ?, ?, ?, ?)
    ''', (exp_group_tuple[0], exp_group_tuple[1], exp_group_tuple[2], exp_group_tuple[3], exp_group_tuple[4]))
    conn.commit()