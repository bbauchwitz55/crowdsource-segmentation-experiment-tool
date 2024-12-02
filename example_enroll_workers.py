from mturksegutils import mturk_seg_vars, worker_quals, mturk_client

screening_results = "/path/to/results/from/screening/task.csv"
mturk = mturk_client.create_mturk_instance()

worker_quals.assign_qualifications_to_consent_and_vocab_batch(mturk, screening_results)

qual1 = mturk_seg_vars.main_seg_qual_name
qual2 = mturk_seg_vars.any_object_count_qual_name
qual3 = mturk_seg_vars.invite_only_qual_name

# In this example, we'll assign the worker to cohort 3
cohort_qual_id = worker_quals.get_qual_id(mturk, qual1)
worker_id = "ABCDEFG1234567"
cohort_index = 3

worker_quals.assign_qualification_to_worker(
    mturk,
    worker_id,
    cohort_qual_id,
    integer_value=cohort_index
)