from flask import Flask, request, render_template, jsonify
from mturksegutils import mturk_seg_vars, mturk_client, assignment_manager
import review_utils
import sqlite3
import threading

app = Flask(__name__)


mturk = mturk_client.create_mturk_instance(sandbox=False)
conn = sqlite3.connect(mturk_seg_vars.db_path, check_same_thread=False)     # The flask app is multi-threaded, which will prevent database updates under the default configuration
cursor = conn.cursor()
lock = threading.Lock()


@app.route('/')
def index():
    """
    Renders the main html page
    """
    return render_template("index.html")


@app.route('/call_refresh_batch_summary', methods=['POST'])
def refresh_batch_summary():
    """
    When called, this fetches the latest data from the database on the number of approved, rejected, and submitted/open HITs
    :return: A JSON object containing the latest batch summary data
    """

    batch_summary_obj = review_utils.refresh_batch_summary()
    return jsonify({"result": batch_summary_obj})


@app.route('/call_pull_new_result_set', methods=['POST'])
def pull_new_result_set():
    """
    When called, this syncs a new batch of HITs from MTurk to the database
    Due to MTurk rate limits and computational complexity, this only fetches a limited number of HITs at a time (currently 100)
    :return: A JSON object containing the number of HITs that were synced
    """

    result = {}

    try:
        lock.acquire(True)

        hits, num_auto_rejected = assignment_manager.get_next_batch_of_submitted_results(mturk, conn, cursor, auto_reject_empties=True)
        num_hits_under_review = len(hits)
        result = {
            "num_assignments_under_review": num_hits_under_review,
            "num_auto_rejected": num_auto_rejected
        }
        #print(result, flush=True)
    finally:
        lock.release()
    
    return jsonify({"result": result})



@app.route('/call_get_next_result_to_review', methods=['POST'])
def get_next_result_to_review():
    """
    When called, this fetches the next HIT from the database that is ready to be reviewed
    :return: A JSON object containing the data for the HIT and its revieable assignment
    """

    current_hit_record = {}
    mturk_type = mturk_client.get_mturk_type(mturk)

    try:
        lock.acquire(True)

        # Filter the database to keep only the HITs with mturk_type = mturk_type and with status = "Submitted"
        cursor.execute("""
            SELECT * 
            FROM hits 
            WHERE mturk_type = ? 
            AND status = 'Submitted'
            ORDER BY auto_approve_time ASC 
            LIMIT 1
        """, (mturk_type,))

        # Select the first hit, ordered by nearest auto_approve time
        db_record = cursor.fetchone()

        if db_record is not None:
            current_hit_record['hit_id'] = db_record[0]
            current_hit_record['mturk_type'] = db_record[1]
            current_hit_record['exp_group'] = db_record[2]
            current_hit_record['image_url'] = db_record[3]
            current_hit_record['classes'] = db_record[4]
            current_hit_record['annotation_mode'] = db_record[5]
            current_hit_record['pre_annotations'] = db_record[6]
            current_hit_record['status'] = db_record[7]
            current_hit_record['assignment_id'] = db_record[8]
            current_hit_record['auto_approve_time'] = db_record[9]
            current_hit_record['interaction_log'] = db_record[10]
            current_hit_record['worker_id'] = db_record[13]

            # Since ann_in_progress is stored as a json string, special characters need to be reformatted so that it can be parsed back as a json object
            ann_in_progress = db_record[11]
            if ann_in_progress is not None:
                ann_in_progress = ann_in_progress.replace("\\", "")
                ann_in_progress = ann_in_progress.replace("\"", "\'")
            current_hit_record['annotation_in_progress'] = ann_in_progress

            # Since ann_final is stored as a json string, special characters need to be reformatted so that it can be parsed back as a json object
            ann_final = db_record[12]
            if ann_final is not None:
                ann_final = ann_final.replace("\\", "")
                ann_final = ann_final.replace("\"", "\'")
            current_hit_record['annotation_final'] = ann_final

        #print(current_hit_record, flush=True)

    finally:
        lock.release()

    return jsonify({"result": current_hit_record})


@app.route('/call_get_next_qualifier_result_to_review', methods=['POST'])
def get_next_qualifier_result_to_review():
    """
    When called, this fetches the next assignment from the training_task table that is ready to be reviewed
    :return: A JSON object containing the data for the reviewable assignment
    """

    current_assignment_record = {}
    mturk_type = mturk_client.get_mturk_type(mturk)

    try:
        lock.acquire(True)

        # Filter the database to keep only the assignments with mturk_type = mturk_type and with status = "Submitted"
        cursor.execute("""
            SELECT * 
            FROM training_tasks 
            WHERE mturk_type = ? 
            AND status = 'Submitted'
            AND qual_score = -1
            ORDER BY auto_approve_time ASC 
            LIMIT 1
        """, (mturk_type,))

        # Select the first assignment, ordered by nearest auto_approve time
        db_record = cursor.fetchone()

        if db_record is not None:
            current_assignment_record['hit_id'] = db_record[0]
            current_assignment_record['mturk_type'] = db_record[1]
            current_assignment_record['exp_group'] = db_record[2]
            current_assignment_record['image_url'] = db_record[3]
            current_assignment_record['classes'] = db_record[4]
            current_assignment_record['annotation_mode'] = db_record[5]
            current_assignment_record['pre_annotations'] = db_record[6]
            current_assignment_record['status'] = db_record[7]
            current_assignment_record['assignment_id'] = db_record[8]
            current_assignment_record['auto_approve_time'] = db_record[9]
            current_assignment_record['interaction_log'] = db_record[10]
            current_assignment_record['worker_id'] = db_record[13]

            # Since ann_in_progress is stored as a json string, special characters need to be reformatted so that it can be parsed back as a json object
            ann_in_progress = db_record[11]
            if ann_in_progress is not None:
                ann_in_progress = ann_in_progress.replace("\\", "")
                ann_in_progress = ann_in_progress.replace("\"", "\'")
            current_assignment_record['annotation_in_progress'] = ann_in_progress

            # Since ann_final is stored as a json string, special characters need to be reformatted so that it can be parsed back as a json object
            ann_final = db_record[12]
            if ann_final is not None:
                ann_final = ann_final.replace("\\", "")
                ann_final = ann_final.replace("\"", "\'")
            current_assignment_record['annotation_final'] = ann_final

        #print(current_hit_record, flush=True)

    finally:
        lock.release()

    return jsonify({"result": current_assignment_record})


@app.route('/call_mark_current_qual_record_as_good', methods=['POST'])
def mark_current_qual_record_as_good():
    print("received call for mark_current_qual_record_as_good")
    data = request.json
    hit_id = data['hit_id']
    assignment_id = data['assignment_id']
    print(data)

    try:
        lock.acquire(True)

        # Get the assignment_id by finding the table row with this hit_id in hits
        cursor.execute("SELECT * FROM training_tasks WHERE hit_id=? AND assignment_id=?", (hit_id, assignment_id,))
        record = cursor.fetchone()[0]

        # mark the assignment as good in the database
        cursor.execute("UPDATE training_tasks SET qual_score=1 WHERE hit_id=? AND assignment_id=?", (hit_id, assignment_id,))
        conn.commit()

        print(f'Marked assignment {assignment_id} for training task {hit_id} as GOOD', flush=True)

    finally:
        lock.release()

    return jsonify({"result": "success"})


@app.route('/call_mark_current_qual_record_as_bad', methods=['POST'])
def mark_current_qual_record_as_bad():
    print("received call for mark_current_qual_record_as_good")
    data = request.json
    hit_id = data['hit_id']
    assignment_id = data['assignment_id']
    print(data)

    try:
        lock.acquire(True)

        # Get the assignment_id by finding the table row with this hit_id in hits
        cursor.execute("SELECT * FROM training_tasks WHERE hit_id=? AND assignment_id=?", (hit_id, assignment_id,))
        record = cursor.fetchone()[0]

        # mark the assignment as bad in the database
        cursor.execute("UPDATE training_tasks SET qual_score=0 WHERE hit_id=? AND assignment_id=?", (hit_id, assignment_id,))
        conn.commit()

        print(f'Marked assignment {assignment_id} for training task {hit_id} as BAD', flush=True)

    finally:
        lock.release()

    return jsonify({"result": "success"})


@app.route('/call_approve_current_record', methods=['POST'])
def approve_current_record():

    data = request.json
    hit_id = data['hit_id']

    try:
        lock.acquire(True)

        # Get the assignment_id by finding the table row with this hit_id in hits
        cursor.execute("SELECT assignment_id FROM hits WHERE hit_id=?", (hit_id,))
        assignment_id = cursor.fetchone()[0]

        assignment_manager.approve_assignment(mturk, conn, cursor, assignment_id)
        print(f'Approved assignment for HIT ID {hit_id}', flush=True)

    finally:
        lock.release()

    return jsonify({"result": "success"})


@app.route('/call_reject_current_record_too_inaccurate', methods=['POST'])
def reject_current_record_too_inaccurate():

    data = request.json
    hit_id = data['hit_id']

    try:
        lock.acquire(True)

        # Get the assignment_id by finding the table row with this hit_id in hits
        cursor.execute("SELECT assignment_id FROM hits WHERE hit_id=?", (hit_id,))
        assignment_id = cursor.fetchone()[0]
        feedback = mturk_seg_vars.reject_feedback_inaccurate

        assignment_manager.reject_and_repost_assignment(mturk, conn, cursor, assignment_id, feedback)
        print(f'Rejected assignment for HIT ID {hit_id} - too inaccurate', flush=True)

    finally:
        lock.release()

    return jsonify({"result": "success"})



@app.route('/call_reject_current_record_too_few', methods=['POST'])
def reject_current_record_too_few():

    data = request.json
    hit_id = data['hit_id']

    try:
        lock.acquire(True)

        # Get the assignment_id by finding the table row with this hit_id in hits
        cursor.execute("SELECT assignment_id, exp_group FROM hits WHERE hit_id=?", (hit_id,))
        record = cursor.fetchone()
        assignment_id = record[0]
        exp_group = record[1]

        # Get the number of objects for this exp_group from the exp_group table
        cursor.execute("SELECT num_objects FROM exp_groups WHERE exp_group=?", (exp_group,))
        num_objects = cursor.fetchone()[0]
        #print(f'Number of objects for this exp_group: {num_objects}', flush=True)

        feedback = mturk_seg_vars.reject_feedback_too_few.format(num_objects)
        assignment_manager.reject_and_repost_assignment(mturk, conn, cursor, assignment_id, feedback)

        print(f'Rejected assignment for HIT ID {hit_id} - too few objects labeled', flush=True)

    finally:
        lock.release()

    return jsonify({"result": "success"})



if __name__ == '__main__':
    app.run(debug=True)