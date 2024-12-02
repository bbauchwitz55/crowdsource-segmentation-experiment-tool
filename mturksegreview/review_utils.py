import sqlite3
from mturksegutils import mturk_seg_vars



def refresh_batch_summary():
    """
    This method is called by the MTurkReviewFlask.py file to get the data for visualizing the status of each batch.
    It checks the database and gets the current number of hits for each batch that are approved or rejected.
    :return batch_summary_obj: a dictionary containing the status of each batch
    """

    # Create the database connection
    conn = sqlite3.connect(mturk_seg_vars.db_path)
    cursor = conn.cursor()

    # Create a dictionary for storing the batch summary data
    batch_summary_obj = {}

    # For each batch and for both sandbox and production, call the get_status_of_hits method
    cursor.execute("SELECT exp_group FROM exp_groups")
    batches = cursor.fetchall()

    for batch in batches:
        # Get the status of all HITs for this batch
        # First, count the number of sandbox HITs posted
        cursor.execute(
            """
                SELECT COUNT(*) 
                FROM hits 
                WHERE exp_group = ? 
                AND mturk_type = 'sandbox'
            """, (batch))
        posted_sandbox = cursor.fetchone()[0]

        # Count the number of sandbox HITs approved
        cursor.execute(
            """
                SELECT COUNT(*) 
                FROM hits 
                WHERE exp_group = ? 
                AND mturk_type = 'sandbox'
                AND status = 'Approved'
            """, (batch))
        approved_sandbox = cursor.fetchone()[0]

        # Count the number of sandbox hits rejected
        cursor.execute(
            """
                SELECT COUNT(*) 
                FROM hits 
                WHERE exp_group = ? 
                AND mturk_type = 'sandbox'
                AND status = 'Rejected'
            """, (batch))
        rejected_sandbox = cursor.fetchone()[0]

        # Count the number of production HITs posted
        cursor.execute(
            """
                SELECT COUNT(*) 
                FROM hits 
                WHERE exp_group = ? 
                AND mturk_type = 'production'
            """, (batch))
        posted_production = cursor.fetchone()[0]

        # Count the number of production HITs approved
        cursor.execute(
            """
                SELECT COUNT(*)
                FROM hits
                WHERE exp_group = ?
                AND mturk_type = 'production'
                AND status = 'Approved'
            """, (batch))
        approved_production = cursor.fetchone()[0]

        # Count the number of production HITs rejected
        cursor.execute(
            """
                SELECT COUNT(*)
                FROM hits
                WHERE exp_group = ?
                AND mturk_type = 'production'
                AND status = 'Rejected'
            """, (batch))
        rejected_production = cursor.fetchone()[0]

        # Calculate the number of HITs that are still open for sandbox and production
        outstanding_sandbox = posted_sandbox - (approved_sandbox + rejected_sandbox)
        outstanding_production = posted_production - (approved_production + rejected_production)

        # Format the data for this batch into a dictionary object and add it to the master dictionary
        batch_obj = {}
        batch_production_obj = {}
        batch_sandbox_obj = {}
        batch_production_obj["posted"] = posted_production
        batch_production_obj["approved"] = approved_production
        batch_production_obj["rejected"] = rejected_production
        batch_production_obj["outstanding"] = outstanding_production
        batch_sandbox_obj["posted"] = posted_sandbox
        batch_sandbox_obj["approved"] = approved_sandbox
        batch_sandbox_obj["rejected"] = rejected_sandbox
        batch_sandbox_obj["outstanding"] = outstanding_sandbox
        batch_obj["sandbox"] = batch_sandbox_obj
        batch_obj["production"] = batch_production_obj
        batch_summary_obj[batch[0]] = batch_obj

    return batch_summary_obj