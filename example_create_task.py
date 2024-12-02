import sqlite3
from mturksegutils import mturk_client, mturk_seg_vars, hit_builder, worker_quals


# Open a connection to the database and set up the Mechanical Turk client
conn = sqlite3.connect(mturk_seg_vars.db_path)
cursor = conn.cursor()
mturk = mturk_client.create_mturk_instance()

# Even for a 1-off, you will want to be able to search for it later
search_key = "1-off-task"

# Who is eligible to complete this task
required_training_score = 5
qual_requirements = worker_quals.get_task_qualification_set(
    mturk,
    qual_criteria=required_training_score,
    invite_only=False
)

# Import the code for javascript segmentation app
app = hit_builder.load_html_as_mturk_question(mturk_seg_vars.html_task_path)

# Data for customizing the task
image_url = "https://web.address.to.image.com"
obj_classes = "car-truck-bus" # The classes the labeler should mark
annotation_mode = "outline" # Which drawing tool(s) will be present
payment_amt = 0.08 # How much the labeler will be paid
time_limit = 600 # How much time the labeler has to finish (10 min)
repeats = 5	# Each image should be repeated by 5 unique labelers

hit_builder.create_segmentation_hit(
    mturk,
    conn,
    cursor,
    img_url=image_url,
    classes=obj_classes,
    annotation_mode=annotation_mode,
    exp_group=search_key,
    reward=payment_amt,
    time_limit=time_limit,
    qualification_requirements=qual_requirements,
    max_assignments=repeats
)
