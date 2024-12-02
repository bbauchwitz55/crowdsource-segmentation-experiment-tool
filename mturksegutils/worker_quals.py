import csv
from mturksegutils import mturk_seg_vars, mturk_client

"""
There are three quals that are used to manage worker enrollment in tasks
- main_seg_qual: the main qual, assigned to enrolled workers, different integer values reflect cohort/skill level
- any_object_count_qual: certifies a worker can complete tasks with an unspecified number of objects per image
- invite_only_qual: assigned to workers on a temporary basis to give priority access to tasks
"""


# Read the custom qualification variable values
any_object_count_qual_indicator = mturk_seg_vars.any_object_count_qual_indicator
main_seg_qual_name = mturk_seg_vars.main_seg_qual_name
any_object_count_qual_name = mturk_seg_vars.any_object_count_qual_name
invite_only_qual_name = mturk_seg_vars.invite_only_qual_name
vocab_score_requirement = 80


def get_task_qualification_set(mturk, qual_criteria=1, invite_only=False):
    """
    Gets the qualifications that must be met for a worker to accept the segmentation task
    :param mturk: the mturk client instance
    :param qual_criteria: an int indicating the score needed on the main qualification, or a string separated with '-'
    :param invite_only: whether the task is meant to be invite only (i.e., available to a pre-selected set of workers)
    :return: the qualification list object
    """

    # qual_criteria can pass a string for indicating special behavior
    any_object_count_requirement = False
    if isinstance(qual_criteria, str):
        # First check if this is a task that requires the any object count qual
        if qual_criteria == any_object_count_qual_indicator:
            any_object_count_requirement = True

        pieces = qual_criteria.split('-')
        if len(pieces) > 1:
            qual_criteria = int(pieces[0])
        else:
            qual_criteria = int(pieces)

    main_seg_qual_id = get_qual_id(mturk, main_seg_qual_name)

    main_qual_comparator = 'GreaterThanOrEqualTo'

    qualifications = [
        # The main segmentation qual
        {
            'QualificationTypeId': main_seg_qual_id,
            'Comparator': main_qual_comparator,
            'IntegerValues': [qual_criteria],
            'RequiredToPreview': False  # Workers can preview, but need the qualification to accept
        },
        # Worker must be based in the US
        {
            'QualificationTypeId': '00000000000000000071',
            'Comparator': 'EqualTo',
            'LocaleValues': [
                {
                    'Country': 'US'
                },
            ],
            'RequiredToPreview': False  # Workers can preview, but need to be from the US to accept
        },
        # Worker must have an HIT approval rate greater than 90%
        {
            'QualificationTypeId': '000000000000000000L0',
            'Comparator': 'GreaterThan',
            'IntegerValues': [90],
            'RequiredToPreview': False  # Workers can preview, but need >90% approval rate to accept
        }
    ]

    if any_object_count_requirement:
        # This means the worker needs to be qualified in annotating images with an arbitrary number of objects
        any_object_qual_id = get_qual_id(mturk, any_object_count_qual_name)
        any_object_qual = {
            'QualificationTypeId': any_object_qual_id,
            'Comparator': 'EqualTo',
            'IntegerValues': [1],
            'RequiredToPreview': False  # Workers can preview, but need the qualification to accept
        }
        qualifications.append(any_object_qual)

    if invite_only:
        # This means the task is created to invite a specific worker
        invite_only_qual_id = get_qual_id(mturk, invite_only_qual_name)
        invite_only_qual = {
            'QualificationTypeId': invite_only_qual_id,
            'Comparator': 'EqualTo',
            'IntegerValues': [1],
            'RequiredToPreview': False  # Workers can preview, but need the qualification to accept
        }
        qualifications.append(invite_only_qual)
    return qualifications


def assign_qualification_to_worker(mturk, worker_id, qual_type_id, integer_value=1, verbose=False):
    """
    Assigns the specified qualiication to the worker

    :param mturk: the client for the mturk environment in which to assign the qual (sandbox or production)
    :param worker_id: the worker ID
    :param qual_type_id: the ID of the qualification to assign
    :param integer_value: the integer value to assign to the qualification
    :param verbose: if True, print status to the console
    """

    try:
        mturk.associate_qualification_with_worker(
            QualificationTypeId=qual_type_id,
            WorkerId=worker_id,
            IntegerValue=integer_value,
            SendNotification=False
        )
        if verbose:
            print(f"Assigned qualification to worker {worker_id}")
    except Exception as e:
        if verbose:
            print(f"Error assigning qualification to worker {worker_id}: {e}")


def get_qual_id(mturk, qual_name):
    """
    Gets the type ID for given qualification name
    :param mturk: the mturk client instance
    :param qual_name: the name of the qualification to get the ID for
    :return: the qualification type ID
    """

    # Query MTurk for the qualification name
    response = mturk.list_qualification_types(
        Query=qual_name,
        MustBeRequestable=False,
        MustBeOwnedByCaller=True
    )

    # Extract qualification details from the response
    qualifications = response['QualificationTypes']
    return qualifications[0]['QualificationTypeId']


def assign_qualifications_to_consent_and_vocab_batch(mturk, batch_csv_file):
    """
    Reads the csv file containing results of a screening qualifier batch (consent form + vocab quiz)
    Assigns a score of 1 for the Duke Hal segmentation qual for workers with vocab score > 80%
    :param mturk: the mturk client instance
    :param batch_csv_file: the csv file containing results from a consent + vocab batch
    """

    duke_hal_seg_qual_id = get_qual_id(mturk, main_seg_qual_name)

    # Read the csv file
    with open(batch_csv_file, 'r') as f:
        reader = csv.reader(f)
        header = True
        for row in reader:

            # Skip the header row
            if header:
                header = False
                continue

            # Get the data from the row
            worker_id = row[15]
            result_data = row[51]
            vocab_result = result_data.split('|')[-1]
            vocab_score = vocab_result.split('-')[-1]
            passes = float(vocab_score) >= vocab_score_requirement

            # If the worker has a vocab score > vocab_score_requirement, assign a qual score of 1 so that they can enter the study
            if passes:
                assign_qualification_to_worker(mturk, worker_id, duke_hal_seg_qual_id, integer_value=1)


def pass_list_of_workers(passing_workers, qual_id, qual_score):
    """
    Assigns the specified qualification to the workers in the list
    :param passing_workers: a list of worker IDs
    :param qual_id: the ID of the qualification to assign
    :param qual_score: the score to assign to the qualification
    """

    # Establish a connection to MTurk
    mturk = mturk_client.create_mturk_instance(sandbox=False)

    for worker_id in passing_workers:

        # Check if the worker already has a higher score for this qualification
        worker_qualification = None
        try:
            worker_qualification = mturk.get_qualification_score(QualificationTypeId=qual_id, WorkerId=worker_id)
        except:
            print("Worker does not have this qualification type.")
        if worker_qualification is not None and worker_qualification['Qualification']['IntegerValue'] > qual_score:
            print(f'Worker {worker_id} already has a higher score for this qualification. Skipping.')
            continue

        # Assign the qualification to the worker
        assign_qualification_to_worker(mturk, worker_id, qual_id, qual_score)
        print(f'Successfully assigned qual score of {qual_score} to worker {worker_id}')
