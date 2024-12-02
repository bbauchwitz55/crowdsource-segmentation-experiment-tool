import sqlite3
from mturksegutils import mturk_client, mturk_seg_vars, hit_builder


# Open a connection to the database and set up the Mechanical Turk client
conn = sqlite3.connect(mturk_seg_vars.db_path)
cursor = conn.cursor()
mturk = mturk_client.create_mturk_instance()

exp_group = "Cohort1"
start_index = 0
end_index = 1000
repeats = 3	# Each image should be repeated by 3 unique labelers

hit_builder.create_segmentation_batch(
    mturk,
    conn,
    cursor,
    exp_group,
    start_at=start_index,
    end_at=end_index,
    num_assignments_per_hit=repeats
)
