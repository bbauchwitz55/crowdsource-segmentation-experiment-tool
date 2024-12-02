

# The location where the experiment database should be stored
db_path = ''

# The location of the main MTurk task html file
html_task_path = ''

# The feedback to be given for different types of assignment approvals/rejections
approval_feedback = ''
reject_feedback_empty = 'No segment annotation provided'
reject_feedback_too_few = 'Too few annotations provided. Needed to annotate at least {num_objects} objects'
reject_feedback_inaccurate = 'Segment annotation too inaccurate'

# An indicator variable passed between modules to indicate that a task requires the 'any object count' qual
any_object_count_qual_indicator = '3-any'

# The names to be used for the custom qualifications
main_seg_qual_name = ''
any_object_count_qual_name = ''
invite_only_qual_name = ''

# The score required on the vocab screening quiz for entry into the study
vocab_score_requirement = 80