import xmltodict
import sqlite3
import json
import datetime
import time

from mturksegutils import mturk_seg_vars, mturk_client, other_utils, hit_builder, worker_quals


db_path = mturk_seg_vars.db_path
html_task_path = mturk_seg_vars.html_task_path
reject_feedback_empty = mturk_seg_vars.reject_feedback_empty
reject_feedback_inaccurate = mturk_seg_vars.reject_feedback_inaccurate


def select_assignments_and_sort_by_auto_approve_time(cursor):
    """
    Selects all assignments with status 'Submitted' and sorts them by auto_approve_time with earliest first
    :param cursor: the sqlite3 cursor object
    :return: a list of rows in the assignments table according to the above criteria
    """

    cursor.execute("""
        SELECT * FROM assignments 
        WHERE status = 'Submitted' 
        ORDER BY auto_approve_time ASC
    """)
    results = cursor.fetchall()
    return results


def parse_answer_data_for_assignment(assignment):
    """
    Parses an MTurk assignment answer data and returns the interaction log, annotation in progress, and result data
    :param assignment: the MTurk assignment object
    :return: interaction_log, annotation_in_progress, result_data
    """

    # The answer data is stored in an xml string inside the assignment object
    assignment_answer = assignment['Answer']
    answer_dict = {}

    # Parse the xml answer data -> fields hierarchy depends on what the worker completed
    if assignment_answer is not None:
        answer_json = xmltodict.parse(assignment_answer)
        if answer_json is not None:
            answer_json = answer_json['QuestionFormAnswers']
            if answer_json is not None:
                answer_json = answer_json['Answer']
                for a in answer_json:
                    key = a['QuestionIdentifier']
                    val = a['FreeText']
                    answer_dict[key] = val

    # By default we assume no results are present
    interaction_log, annotation_in_progress, result_data = None, None, None
    if 'interaction_log' in answer_dict.keys():
        interaction_log = answer_dict['interaction_log']
    if 'annotation_in_progress' in answer_dict.keys():
        annotation_in_progress = answer_dict['annotation_in_progress']
    if 'result_data' in answer_dict.keys():
        result_data = answer_dict['result_data']

    return interaction_log, annotation_in_progress, result_data


def sync_hits_to_db(exp_group):
    """
    Given an experiment group, checks the MTurk database for new assignments and adds them to the local database
    :param exp_group: the experiment group to update the database for
    """

    # Create sandbox and production MTurk instances
    mturk_sandbox = mturk_client.create_mturk_instance(sandbox=True)
    mturk_production = mturk_client.create_mturk_instance(sandbox=False)

    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Ignore HITs where the status is 'Approved' or 'Rejected' - these can no longer be updated
    cursor.execute("SELECT * FROM hits WHERE exp_group = ? AND status = ?", (exp_group, 'Submitted',))
    submitted_hits = cursor.fetchall()
    cursor.execute("SELECT * FROM hits WHERE exp_group = ? AND status = ?", (exp_group, 'Open',))
    open_hits = cursor.fetchall()

    # Iterate over the HITs listed as submitted in the DB and see if they were approved or rejected
    print("SUBMITTED HITs:")
    count = 0
    for row in submitted_hits:
        mturk_type = row[1]
        mturk = mturk_sandbox if mturk_type == 'sandbox' else mturk_production
        # check the status to see if the HIT has been approved or rejected and update the table accordingly
        update_existing_assignment_for_hit(row, mturk, cursor)
        count += 1
        if count % 10 == 0:
            print(f"Synced {count} of {len(submitted_hits)} submitted HITs")

    conn.commit()

    # Iterate over the HITs listed as open in the DB and see if they are now submitted
    print("OPEN HITs:")
    count = 0
    for row in open_hits:
        hit_id = row[0]
        mturk_type = row[1]
        mturk = mturk_sandbox if mturk_type == 'sandbox' else mturk_production
        exp_group = row[2]
        is_qual = False
        if exp_group.startswith('qual'):
            is_qual = True
        add_new_assignments_for_hit_to_database(hit_id, mturk, cursor, is_qual=is_qual)
        count += 1
        if count % 10 == 0:
            print(f"Synced {count} of {len(open_hits)} open HITs")

    conn.commit()
    conn.close()


def get_status_of_hits(mturk, search_key, verbose=False):
    # TODO: we should not be directly querying MTurk. Instead, query the database and then sync wih MTurk as requested.
    """
    Given an MTurk instance, and an experiment group to filter by, returns the number of approved, rejected, submitted, and open HITs for that group
    :param mturk: the mturk instance to query
    :param search_key: the experiment group to filter by
    :param verbose: whether to print detailed results to the console
    :return: the number of approved, submitted, and open HITs for the specified experiment group
    """

    # Establish a connection to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Define the exp_group value to filter by
    exp_group_value = search_key

    # Get the mturk type to filter by
    mturk_type = 'production'
    if 'sandbox' in mturk._endpoint.host:
        mturk_type = 'sandbox'

    # Query the hits table for records with the desired exp_group and mturk_type and retrieve their hit_id
    cursor.execute("SELECT hit_id FROM hits WHERE exp_group = ? AND mturk_type = ?", (exp_group_value, mturk_type))
    result = cursor.fetchall()

    # Set up counters for the number of hits in each state
    num_hits_open = 0
    num_hits_submitted = 0
    num_hits_approved = 0

    # Print the results
    for row in result:
        hit_id = row[0]
        # get the hit from mturk
        hit = mturk.get_hit(HITId=hit_id)

        hit_status = hit['HIT']['HITStatus']

        # If verbose: print the hit_id, the hit status, and the approval status
        if verbose:
            print(f"Hit ID: {hit_id}; Hit status: {hit_status}; Approval status: {hit['HIT']['HITReviewStatus']}")

        # If there are assignments for the HIT, print their details and count the open, submitted, and approved assignments
        if hit_status == "Reviewable":

            # If verbose, first list all assignments that have been rejected
            if verbose:
                rejected_assignments = mturk.list_assignments_for_hit(HITId=hit_id, AssignmentStatuses=['Rejected'])[
                    'Assignments']
                for assignment in rejected_assignments:
                    assignment_id = assignment['AssignmentId']
                    assignment_status = assignment['AssignmentStatus']
                    print(f"    Assignment ID: {assignment_id}; Assignment status: {assignment_status}")

            # Check if there is any assignment that has been approved
            approved_assignments = mturk.list_assignments_for_hit(HITId=hit_id, AssignmentStatuses=['Approved'])[
                'Assignments']
            if len(approved_assignments) > 0:
                num_hits_approved += 1

                # If verbose: list the approved assignments
                if verbose:
                    # This loop is just for error testing - the segmentation task should never have multiple approved assignments for a single HIT
                    for assignment in approved_assignments:
                        assignment_id = assignment['AssignmentId']
                        assignment_status = assignment['AssignmentStatus']
                        print(f"    Assignment ID: {assignment_id}; Assignment status: {assignment_status}")
                continue

            # If no assignments are approved, check if some assignment has been submitted
            submitted_assignments = mturk.list_assignments_for_hit(HITId=hit_id, AssignmentStatuses=['Submitted'])[
                'Assignments']
            if len(submitted_assignments) > 0:
                num_hits_submitted += 1

                # This loop is just for error testing - the segmentation task should never have multiple assignments
                # for the same HIT that are in 'submitted' state at the same time
                if verbose:
                    for assignment in submitted_assignments:
                        assignment_id = assignment['AssignmentId']
                        assignment_status = assignment['AssignmentStatus']
                        interaction_log, annotation_in_progress, result_data = parse_answer_data_for_assignment(
                            assignment)
                        if interaction_log is None:
                            interaction_log = 'N/A'
                        if annotation_in_progress is None:
                            annotation_in_progress = 'N/A'
                        if result_data is None:
                            result_data = 'N/A'
                        print(f"    Assignment ID: {assignment_id}; Assignment status: {assignment_status}")
                        print(f'    - Interaction log: {interaction_log}')
                        print(f'    - Annotation in progress: {annotation_in_progress}')
                        print(f'    - Result data: {result_data}')

            # If there are no submitted or approved assignments, then the HIT is open
            if len(submitted_assignments) == 0 and len(approved_assignments) == 0:
                num_hits_open += 1

        # If there are no assinments for the HIT then it is open by default
        elif hit_status == "Assignable":
            num_hits_open += 1

    if verbose:
        # Print the summary
        print("")
        print(f'HITs approved: {num_hits_approved}')
        print(f'HITs submitted: {num_hits_submitted}')
        print(f'HITs open: {num_hits_open}')

    # Close the connection
    conn.close()

    return num_hits_approved, num_hits_submitted, num_hits_open


def get_next_batch_of_submitted_results(mturk, conn, cursor, max_results_to_pull=100, auto_reject_empties=True):
    """
    Pulls a set of submitted assignments from MTurk and syncs them with the database
    Returns them for use by the flask review app
    Can only pull a limited number of results at a time do to computational cost and API usage limits
    Will filter out results that are not associated with one of the named experiment groups in the database

    :param mturk: the mturk client instance
    :param conn: a connection to the sqlite3 database
    :param cursor: the database client
    :param max_results_to_pull: the number of results to pull
    :param auto_reject_empties: whether to automatically reject and repost assignments with empty results
    :return results: a list of hit_ids with submitted assignments
    """

    submitted_hit_ids = []
    num_auto_rejected = 0

    # get all unique values of exp_group in the exp_groups table
    cursor.execute("SELECT DISTINCT exp_group FROM exp_groups")
    exp_groups = cursor.fetchall()
    exp_groups = [exp_group[0] for exp_group in exp_groups]
    print(exp_groups)

    # Pull a set of hits with submitted assignments from MTurk
    reviewable_hits = mturk.list_reviewable_hits(MaxResults=max_results_to_pull)['HITs']

    # Iterate over each HIT and get the assignments
    for hit in reviewable_hits:
        hit_id = hit['HITId']

        # Change the internal mturk status for this HIT to 'Reviewing' so that it is no longer pulled by this operation
        mturk.update_hit_review_status(HITId=hit_id, Revert=False)

        # Skip the hit if it is not from one of the official experiment groups
        # Only hits created via the API with a named requester annotation are eligible
        if 'RequesterAnnotation' not in hit.keys():
            print(f'Requester annotation not found for hit: {hit}')
            continue

        requester_ann = hit['RequesterAnnotation']
        if requester_ann is None or requester_ann == "" or requester_ann not in exp_groups:
            print(f'Requester annotation {requester_ann} is not a valid experiment group for hit {hit_id}')
            continue

        assignments = mturk.list_assignments_for_hit(HITId=hit_id)

        print(f'{hit}, num assignments: {len(assignments["Assignments"])}')

        # For this task, there should never be more than one submitted assignment
        # The boto3 library always returns a list anyway
        for assignment in assignments['Assignments']:

            # Get the assignment data
            assignment_id = assignment['AssignmentId']
            status = assignment['AssignmentStatus']
            auto_approve_time = assignment['AutoApprovalTime']
            worker_id = assignment['WorkerId']
            interaction_log, annotation_in_progress, result_data = parse_answer_data_for_assignment(assignment)

            # Update the table row
            cursor.execute("""
                UPDATE hits 
                SET assignment_id = ?, 
                status = ?, 
                worker_id = ?, 
                auto_approve_time = ?, 
                interaction_log = ?, 
                annotation_in_progress = ?, 
                result_data = ?
                WHERE hit_id = ?
            """, (
                assignment_id, status, worker_id, auto_approve_time, interaction_log, annotation_in_progress,
                result_data, hit_id))
            conn.commit()

            if status != 'Submitted':
                continue

            # If auto_reject_empties, check if the result data is empty and if so, reject and repost the assignment
            if auto_reject_empties:
                is_empty = check_if_response_is_empty(interaction_log, annotation_in_progress, result_data)
                if is_empty:
                    reject_and_repost_assignment(mturk, conn, cursor, assignment_id, reject_feedback_empty)
                    num_auto_rejected += 1
                    continue

            # If the hit has not been excluded up to this point, add it to the list of revieable hits
            submitted_hit_ids.append(hit_id)

    return submitted_hit_ids, num_auto_rejected


def get_hits_with_annotation(mturk, annotation, max_results=100):
    """
    Gets the IDs of all HITs having a particular requester annotation (used to store the experiment group name)

    :param mturk: the mturk client instance
    :param annotation: the requester annotation
    :param max_results: the max number of results to search
    :return: a list of HIT IDs
    """

    # The list to store HIT IDs
    hit_ids = []

    # Start with the initial call
    response = mturk.list_hits(MaxResults=max_results)

    while response:
        for hit in response['HITs']:
            if hit.get('RequesterAnnotation') == annotation:
                hit_ids.append(hit['HITId'])

        # Check if there are more results to fetch
        if 'NextToken' in response:
            response = mturk.list_hits(NextToken=response['NextToken'], MaxResults=max_results)
        else:
            response = None

    return hit_ids


def check_if_response_is_empty(interaction_log_str, annotation_in_progress_str, result_data_str):
    """
    :return: True if the annotation data is empty, false otherwise
    """

    # If the interaction log only has a start indicator, then no UI elements were pressed and the result is empty
    if interaction_log_str is not None and len(interaction_log_str.split('-')) < 2:
        return True

    # If there is no data for either the in progress of final annotations, the worker did not make any annotations
    if annotation_in_progress_str == 'None' and result_data_str == 'None':
        return True

    if annotation_in_progress_str is not None and annotation_in_progress_str != 'None':
        annotation_in_progress = json.loads(annotation_in_progress_str)
        for ann in annotation_in_progress:
            if 'data' in ann.keys() and len(ann['data']) > 0:
                return False
            elif 'strokes' in ann.keys() and len(ann['strokes']) > 0:
                return False

    if result_data_str is not None and result_data_str != 'None':
        result_data = json.loads(result_data_str)
        for ann in result_data:
            if 'strokes' in ann.keys() and len(ann['strokes']) > 0:
                return False

    return True


def reject_empty_responses(mturk, cursor, exp_group, verbose=True):
    """
    Automatically reject all assignments listed in the database that have no annotation result data
    :param mturk: the mturk client instance
    :param cursor: the database cursor
    :param verbose: if true, print detailed logs to the console
    """

    mturk_type = mturk_client.get_mturk_type(mturk)

    # Get all submitted hits
    cursor.execute("""
        SELECT * FROM hits 
        WHERE status = 'Submitted' 
        AND exp_group = ? 
        AND mturk_type = ?
    """, (exp_group, mturk_type))
    results = cursor.fetchall()

    # For each submitted assignment, check the result data
    for row in results:
        assignment_id = row[8]
        interaction_log = row[10]
        ann_in_progress = row[11]
        ann_final = row[12]

        # Fix json string formatting artifacts introduced by sqlite
        if ann_in_progress is not None:
            ann_in_progress = ann_in_progress.replace("\\", "")
            ann_in_progress = ann_in_progress.replace("\"", "\'")
        if ann_final is not None:
            ann_final = ann_final.replace("\\", "")
            ann_final = ann_final.replace("\"", "\'")

        is_empty = check_if_response_is_empty(interaction_log, ann_in_progress, ann_final)
        if is_empty:
            mturk.reject_assignment(AssignmentId=assignment_id, RequesterFeedback=reject_feedback_empty)
            if verbose:
                print(f'Rejecting assignment {assignment_id} for exp_group {exp_group} due to empty result data')


def update_existing_assignment_for_hit(row, mturk, cursor, verbose=False):
    """
    Given a row from the hits table, checks whether the assignment associated with that hit has been updated
    :param row: the row from the hits table
    :param mturk: the mturk client instance
    :param cursor: the database cursor
    :param verbose: whether or not to print details to the console
    """

    # Get the existing assignment info in the database
    hit_id = row[0]
    assignment_id = row[8]
    current_status = row[7]

    if verbose:
        print(f'Updating assignment for HIT {hit_id}')

    # Get the most recent data for this assignment from MTurk
    assignment = mturk.get_assignment(AssignmentId=assignment_id)
    # print(assignment)
    new_status = assignment['Assignment']['AssignmentStatus']

    # Update the database if the new data is different from the existing data
    if new_status != current_status:
        cursor.execute("UPDATE assignments SET status = ? WHERE assignment_id = ?", (new_status, assignment_id))
        if verbose:
            print(f'UPDATING assignment {assignment_id}: status = {new_status}')


def add_new_assignments_for_hit_to_database(hit_id, mturk, cursor, verbose=False, is_qual=False):
    """
    Given a hit_id, returns a list of all assignments for that HIT
    :param hit_id: the hit id to query
    :param mturk: the mturk client instance
    :param cursor: the database cursor
    :param verbose: whether or not to print details to the console
    :param is_qual: True if this is a qual task and should be logged to the training_tasks table
    """

    if verbose:
        print(f'Checking for new assignments for HIT {hit_id}')

    mturk_assignments = mturk.list_assignments_for_hit(
        HITId=hit_id, AssignmentStatuses=['Submitted', 'Approved', 'Rejected'])['Assignments']
    print(f'Number of assignments found: {len(mturk_assignments)}')

    # In general there should only be one, but loop regardless
    for assignment in mturk_assignments:

        # Get the assignment info
        assignment_id = assignment['AssignmentId']
        assignment_status = assignment['AssignmentStatus']
        if assignment_status == 'Reviewable':
            assignment_status = 'Submitted'
        worker_id = assignment['WorkerId']
        auto_approve_time = assignment['AutoApprovalTime']

        # Get the detailed results from the assignment
        interaction_log, annotation_in_progress, result_data = parse_answer_data_for_assignment(assignment)

        # For qual tasks there is a separate table that needs to be updated
        if is_qual:
            mturk_type = mturk_client.get_mturk_type(mturk)

            # Get the relevant hit parameters
            cursor.execute("""
                SELECT * FROM hits where hit_id = ?""", (hit_id,))
            row = cursor.fetchone()

            exp_group = row[2]
            image_url = row[3]
            classes = row[4]
            annotation_mode = row[5]
            pre_annotations = row[6]

            try:
                # Update the training_tasks table
                cursor.execute("""
                    INSERT INTO training_tasks
                    (hit_id, 
                    mturk_type, 
                    exp_group, 
                    image_url, 
                    classes, 
                    annotation_mode, 
                    pre_annotations, 
                    status, 
                    assignment_id, 
                    auto_approve_time, 
                    interaction_log, 
                    annotation_in_progress, 
                    result_data, 
                    worker_id, 
                    qual_score) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, -1)
                """, (hit_id,
                      mturk_type,
                      exp_group,
                      image_url,
                      classes,
                      annotation_mode,
                      pre_annotations,
                      assignment_status,
                      assignment_id,
                      auto_approve_time,
                      interaction_log,
                      annotation_in_progress,
                      result_data,
                      worker_id))
            except:
                print("Error! This record is already in the training_tasks table.")

        else:
            # Update the table row
            cursor.execute("""
                UPDATE hits 
                SET assignment_id = ?, 
                status = ?, 
                worker_id = ?, 
                auto_approve_time = ?, 
                interaction_log = ?, 
                annotation_in_progress = ?, 
                result_data = ?
                WHERE hit_id = ?
            """, (
                assignment_id, assignment_status, worker_id, auto_approve_time, interaction_log, annotation_in_progress,
                result_data, hit_id))

        if verbose:
            print(f'ADDING assignment {assignment_id}: status = {assignment_status}')


def approve_assignment(mturk, conn, cursor, assignment_id):
    """
    Approve the specified assignment in the database and on MTurk
    :param mturk: the mturk client instance
    :param conn: the database connection
    :param cursor: the database cursor
    :param assignment_id: the assignment to approve
    """

    try:
        mturk.approve_assignment(AssignmentId=assignment_id)
    except:
        print(f'Failed to approve assignment {assignment_id}')
    cursor.execute("UPDATE hits SET status = ? WHERE assignment_id = ?", ('Approved', assignment_id))
    cursor.execute("UPDATE training_tasks SET status = ? WHERE assignment_id = ?", ('Approved', assignment_id))
    # TODO: eventually we should add a table for screened workers which should be updated
    conn.commit()


def reject_and_repost_assignment(mturk, conn, cursor, assignment_id, feedback):
    """
    Reject the specified assignment in the database and on MTurk, and then repost the HIT
    :param mturk: the mturk client instance
    :param conn: the database connection
    :param cursor: the database cursor
    :param assignment_id: the assignment to reject
    :param feedback: the feedback to provide to the worker
    :return: N/A
    """

    # First, reject the assignment on mturk
    try:
        mturk.reject_assignment(AssignmentId=assignment_id, RequesterFeedback=feedback)
    except:
        print(f'Failed to reject assignment {assignment_id}')

    # Second, update the corresponding row in the hits table of the database
    cursor.execute("UPDATE hits SET status = ? WHERE assignment_id = ?", ('Rejected', assignment_id))

    # Third, post a new hit with the same parameters as the original hit
    cursor.execute("SELECT * FROM hits WHERE assignment_id = ?", (assignment_id,))
    hit_result = cursor.fetchone()

    # Get the hit data
    exp_group = hit_result[2]
    img_url = hit_result[3]
    classes = hit_result[4]
    annotation_mode = hit_result[5]
    pre_annotations = hit_result[6]

    # Get the experiment group data
    cursor.execute("SELECT * FROM exp_groups WHERE exp_group = ?", (exp_group,))
    exp_group_result = cursor.fetchone()
    reward_size = exp_group_result[3]
    time_limit = exp_group_result[4]

    # Fix non-compliant task parameters
    pre_annotations, time_limit = other_utils.fix_non_compliant_task_parameters(pre_annotations, time_limit)

    # Generate the MTurk task XML from the html file
    question = hit_builder.load_html_as_mturk_question(html_task_path)

    # Get the qualification requirements for the task
    qualification_requirements = worker_quals.get_task_qualification_set(mturk)

    hit_builder.create_segmentation_hit(mturk, conn, cursor, question, img_url, classes,
                                        annotation_mode, pre_annotations, exp_group, reward_size,
                                        time_limit, qualification_requirements)


def approve_all_submitted_training_qual_tasks():
    """
    Approves all tasks designated as training, regardless of whether they were assessed as high quality
    """

    # Establish a connection to the database and MTurk
    mturk = mturk_client.create_mturk_instance(sandbox=False)
    conn = sqlite3.connect(mturk_seg_vars.db_path)
    cursor = conn.cursor()

    # select assignment_id from the table 'training_tasks' where exp_group starts with 'qual' and status = 'Submitted'
    cursor.execute("SELECT assignment_id FROM training_tasks WHERE exp_group LIKE 'qual%' AND status='Submitted'")
    rows = cursor.fetchall()

    # Approve the assignment
    for row in rows:
        assignment_id = row[0]
        print(f'Approving assignment {assignment_id}')
        approve_assignment(mturk, conn, cursor, assignment_id)


def auto_approve_if_has_multiple_annotations(exp_group, sandbox=False, verbose=False):
    """
    Automatically approves all assignments for the given experiment group if it has at least two distinct annotations
    :param exp_group: the experiment group to approve for
    :param sandbox: True if approving in the sandbox, False otherwise
    """

    # Establish a connection to the database and MTurk
    conn = sqlite3.connect(mturk_seg_vars.db_path)
    cursor = conn.cursor()
    mturk = mturk_client.create_mturk_instance(sandbox=sandbox)
    mturk_type = mturk_client.get_mturk_type(mturk)

    cursor.execute("""
        SELECT * 
        FROM hits 
        WHERE mturk_type = ? 
        AND exp_group = ?
        AND status = 'Submitted'
        ORDER BY auto_approve_time ASC 
    """, (mturk_type, exp_group,))
    db_records = cursor.fetchall()

    if verbose:
        print(f'There are {len(db_records)} submitted HITs for experiment group {exp_group} running in {mturk_type}.')

    # Iterate over each submitted HIT
    count = 0
    for db_record in db_records:

        assignment_id = db_record[8]

        # Check if it had an in-progress annotation when it was submitted
        ann_in_progress = db_record[11]
        if ann_in_progress is not None:
            ann_in_progress = ann_in_progress.replace("\\", "")
            ann_in_progress = ann_in_progress.replace("\"", "\'")

        # Check if it had completed annotations when it was submitted
        ann_final = db_record[12]
        if ann_final is not None:
            ann_final = ann_final.replace("\\", "")
            ann_final = ann_final.replace("\"", "\'")

        # Check if it has two annotations
        has_two_objects = False
        # There can only be one in-progress annotation, so there must be at least one final annotation
        if ann_final is not None and ann_final != 'None' and ann_final != '[]':
            if ann_in_progress is not None and ann_in_progress != 'None':
                # Make sure the data for in-progress annotation is not an empty array
                if "\'strokes\':[]" not in ann_in_progress:
                    # Count the instances of "\'strokes\'" in the final annotation
                    num_strokes_final = ann_final.count("\'strokes\'")
                    num_empty_strokes_final = ann_final.count("\'strokes\':[]")
                    num_full_strokes_final = num_strokes_final - num_empty_strokes_final
                    if num_full_strokes_final >= 1:
                        has_two_objects = True
            else:
                # Check that the final annotations list has at least two objects
                num_strokes_final = ann_final.count("\'strokes\'")
                num_empty_strokes_final = ann_final.count("\'strokes\':[]")
                num_full_strokes_final = num_strokes_final - num_empty_strokes_final
                if num_full_strokes_final >= 2:
                    has_two_objects = True

        # Approve the assignment if it has at least two objects
        if has_two_objects:
            count += 1
            if verbose:
                print(ann_in_progress)
                print("")
                print(ann_final)
                print("")
                print("=====================================")
            try:
                approve_assignment(mturk, conn, cursor, assignment_id)
                if verbose:
                    print(f"Approved assignment {assignment_id}.")
            except:
                print(f"Warning! MTurk failed to approve assignment {assignment_id}!")

    print(f'Auto approved {count} assignments.')


def auto_approve_if_has_multiple_classes(exp_group, sandbox=False, verbose=False):
    """
    Automatically approves assignments that have multiple object classes annotated
    :param exp_group: the experiment group to check
    """

    # The list of class strings occurring in the annotation result or annotation in progress data
    class_strings = [
        "\'class\':\'airplane\'",
        "\'class\':\'backpack\'",
        "\'class\':\'bicycle\'",
        "\'class\':\'boat\'",
        "\'class\':\'bus\'",
        "\'class\':\'car\'",
        "\'class\':\'cat\'",
        "\'class\':\'dog\'",
        "\'class\':\'motorcycle\'",
        "\'class\':\'person\'",
        "\'class\':\'train\'",
        "\'class\':\'truck\'"
    ]

    # Set up the database and mturk sessions
    conn = sqlite3.connect(mturk_seg_vars.db_path)
    cursor = conn.cursor()
    mturk = mturk_client.create_mturk_instance(sandbox=sandbox)
    mturk_type = mturk_client.get_mturk_type(mturk)

    # Get all submitted hits for this experiment group and rank them in order of auto_approve_time
    cursor.execute("""
        SELECT * 
        FROM hits 
        WHERE mturk_type = ? 
        AND exp_group = ?
        AND status = 'Submitted'
        ORDER BY auto_approve_time ASC 
    """, (mturk_type, exp_group,))
    db_records = cursor.fetchall()

    if verbose:
        print(f'There are {len(db_records)} submitted HITs for experiment group {exp_group} running in {mturk_type}.')

    # Iterate over each database record that was fetched and approve those that have at least two unique class strings listed
    count = 0
    for db_record in db_records:
        assignment_id = db_record[8]

        # Create a string that contains all the annotation data for this assignment
        full_result = ""

        # Format the special characters in the current annotation data and add that to the result string
        ann_in_progress = db_record[11]
        if ann_in_progress is not None:
            ann_in_progress = ann_in_progress.replace("\\", "")
            ann_in_progress = ann_in_progress.replace("\"", "\'")
            full_result = full_result + ann_in_progress

        # Format the special characters in the final annotation data and add that to the result string
        ann_final = db_record[12]
        if ann_final is not None:
            ann_final = ann_final.replace("\\", "")
            ann_final = ann_final.replace("\"", "\'")
            full_result = full_result + ann_final

        # Test if there are at least two unique class strings across all the result data
        if (other_utils.contains_two_substrinsgs(full_result, class_strings)
                and ann_final is not None and ann_final != 'None' and ann_final != '[]'):
            if verbose:
                print(ann_in_progress)
                print("")
                print(ann_final)
                print("")
                print("=====================================")

            # Depending on the timing of mturk and db updates, we may attempt to approve an assignment that is already approved on mturk
            try:
                approve_assignment(mturk, conn, cursor, assignment_id)
                if verbose:
                    print(f"Approved assignment {assignment_id}.")
            except:
                print(f"Warning! MTurk failed to approve assignment {assignment_id}!")

    # Report the number of assignments that were approved
    print(f'Auto approved {count} assignments.')


def override_rejected_hits(hits_to_correct, update_db=True):
    """
    Takes a list of HIT IDs, and if they are rejeted, overrides the rejection
    :param hits_to_correct: a list of HIT IDs to override rejections for
    :param update_db: if true, updates the database to reflect the change
    Note: you might not want to update the DB, such as if you want to internally track these HITs as unacceptable data
    """

    # Establish a connection to the database and MTurk
    mturk = mturk_client.create_mturk_instance(sandbox=False)
    conn = sqlite3.connect(mturk_seg_vars.db_path)
    cursor = conn.cursor()

    # Iterate over each HIT listed
    for hit in hits_to_correct:
        cursor.execute("SELECT assignment_id FROM hits WHERE hit_id=?", (hit,))
        assignment_id = cursor.fetchone()[0]

        # Approve the assignment
        mturk.approve_assignment(AssignmentId=assignment_id, RequesterFeedback="Corrected - mistakenly rejected", OverrideRejection=True)

        # Update the status for this line in the database
        cursor.execute("UPDATE hits SET status = ? WHERE assignment_id = ?", ('Approved', assignment_id))
        conn.commit()


def pull_training_task_assignments_to_db(sandbox=False):
    """
    Pulls all submitted training tasks from MTurk and syncs to the table
    :param sandbox: True if pulling from the sandbox, False otherwise
    """

    # get all rows from the table 'hits' where exp_group starts with 'qual'
    mturk = mturk_client.create_mturk_instance(sandbox=sandbox)
    mturk_type = mturk_client.get_mturk_type(mturk)

    conn = sqlite3.connect(mturk_seg_vars.db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM hits WHERE mturk_type = ? AND exp_group LIKE 'qual%'", (mturk_type,))
    rows = cursor.fetchall()

    # iterate over each row
    for row in rows:
        hit_id = row[0]
        print(hit_id)
        add_new_assignments_for_hit_to_database(hit_id, mturk, cursor, is_qual=True)
    conn.commit()

    cursor.execute("SELECT * FROM training_tasks WHERE exp_group LIKE 'qual%'")
    rows = cursor.fetchall()

    print(len(rows))
    for row in rows:
        print(row)


def remove_hits_early(exp_group, sandbox=True, verbose=False):
    """
    Removes posted HITs from MTurk, as long as they haven't already been assigned or submitted
    :param exp_group: the experiment group to remove hits from
    :param sandbox: if True, remove hits from the sandbox, else, remove hits from production
    """

    mturk = mturk_client.create_mturk_instance(sandbox=sandbox)
    conn = sqlite3.connect(mturk_seg_vars.db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM hits WHERE exp_group=?", (exp_group,))
    rows = cursor.fetchall()

    delete_count = 0
    expired_count = 0
    for row in rows:
        hit_id = row[0]
        if verbose: print(f'HIT ID: {hit_id}')

        # First, try to delete the HIT
        try:
            mturk.delete_hit(HITId=hit_id)
            delete_count += 1
            if verbose: print(f'    Deleted HIT {hit_id}')
        except:
            if verbose: print(f'    Could not delete HIT {hit_id}')

        # If it can't be deleted, then expire it by moving up the auto-expire time
        try:
            current_time = datetime.datetime.now()
            time.sleep(1)
            mturk.update_expiration_for_hit(HITId=hit_id, ExpireAt=current_time)
            expired_count += 1
            if verbose: print(f'    Expired HIT {hit_id}')
        except:
            if verbose: print(f'    Could not expire HIT {hit_id}')

    print(f'deleted {delete_count}')
    print(f'expired {expired_count}')


def update_status_for_approved_and_rejected_hits(sandbox=False):
    """
    HITs that have their status modified directly by MTurk (e.g., due to expiry) will not have that change automatically reflected in the table
    This method checks each HIT listed as submitted in the table and updates the record if it was approved or rejected by MTurk
    :param sandbox: True if updating hits in the sandbox, False otherwise
    """

    # Open connections to the DB and MTurk
    conn = sqlite3.connect(mturk_seg_vars.db_path)
    cursor = conn.cursor()
    mturk = mturk_client.create_mturk_instance(sandbox=sandbox)
    mturk_type = mturk_client.get_mturk_type(mturk)

    # Initialize the count variables
    approved_count = 0
    rejected_count = 0
    row_count = 0

    # Pull all the rows from the hits table listed as submitted
    cursor.execute("SELECT * FROM hits WHERE status='Submitted' AND mturk_type=?", (mturk_type,))
    rows = cursor.fetchall()
    print(f'There are currently {len(rows)} submitted HITs in the database')

    # For each row, get the status of the assignment for that hit from MTurk
    for row in rows:
        hit_id = row[0]
        assignment_id = row[8]

        # get the assignment from mturk
        assignment = mturk.get_assignment(AssignmentId=assignment_id)
        mturk_status = assignment['Assignment']['AssignmentStatus']

        # Update the table for any HITs that were auto-approved or auto-rejected by MTurk (usually due to task expiry)
        if mturk_status == 'Approved':
            approved_count += 1
            cursor.execute("UPDATE hits SET status=? WHERE hit_id=?", (mturk_status, hit_id))
        elif mturk_status == 'Rejected':
            rejected_count += 1
            cursor.execute("UPDATE hits SET status=? WHERE hit_id=?", (mturk_status, hit_id))

        # Only commit changes at intervals to improve performance
        row_count += 1
        if row_count % 10 == 0:
            print(f'Processed {row_count} rows')
            conn.commit()

    # At the end, commit any remaining changes
    conn.commit()

    print(f'Approved {approved_count} HITs')
    print(f'Rejected {rejected_count} HITs')

    cursor.execute("SELECT * FROM hits WHERE status='Submitted' AND mturk_type='production'")
    rows = cursor.fetchall()
    print(f'There are now {len(rows)} submitted HITs in the database')