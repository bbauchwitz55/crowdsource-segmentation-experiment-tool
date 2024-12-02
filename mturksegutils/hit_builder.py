import numbers

from mturksegutils import mturk_client, mturk_seg_vars, worker_quals, other_utils


def create_segmentation_batch(mturk,
                              conn,
                              cursor,
                              exp_group,
                              start_at=0,
                              end_at=8000,
                              num_assignments_per_hit=1,
                              print_status_every_n=10,
                              invite_only=False):
    """
    Creates a full batch of HITs by referencing the database for the given batch parameters

    :param mturk: the mturk client instance
    :param conn: a connection to the sqlite3 database
    :param cursor: the database client
    :param exp_group: the experiment group ID
    :param start_at: the index from the sequence of tasks for this exp_group to start at
    :param end_at: the index from the sequence of tasks for this exp_group to stop at
    :param num_assignments_per_hit: the max number of assignments per hit that is constructed
    :param print_status_every_n: prints a status update after every N hits are posted
    :param invite_only: if true, apply the invite only qual when creating this batch of hits
    """

    mturk_type = mturk_client.get_mturk_type(mturk)

    # Generate the MTurk task XML from the html file
    question = load_html_as_mturk_question(mturk_seg_vars.html_task_path)

    # Establish what score the participant must have on the qual to complete this task
    exp_group_query = exp_group
    # For qual tasks, they only need a score of 1 (i.e., have completed the consent form and vocab quiz)
    if exp_group == 'qual-any':
        qual_criteria = '1-any'
    elif exp_group.startswith('qual'):
        qual_criteria = 1

    # For experiment tasks, there may be a custom training requirement above and beyond the consent form
    else:
        exp_group_components = exp_group.split('-')
        if len(exp_group_components) > 1:
            qual_criteria = int(exp_group_components[1])
            exp_group_query = f'{exp_group_components[0]}-{exp_group_components[1]}'
        else:
            qual_criteria = '3-any'

    # Get the qualification requirements for the task
    qualification_requirements = worker_quals.get_task_qualification_set(mturk, qual_criteria, invite_only=invite_only)

    # Get the row in exp_group matching this exp_group ID and the mturk_type
    # The exp_group_query is the prefix to the exp_group
    # This is done because the exp_group may have a special suffix if it is being reposted, etc.
    cursor.execute("SELECT * FROM exp_groups WHERE exp_group=? AND mturk_type=?", (exp_group_query, mturk_type))
    exp_group_data = cursor.fetchone()

    # Get the reward size and time limit from the exp_group data
    reward_size = exp_group_data[3]
    time_limit = exp_group_data[4]

    # Get all rows in the task_config table matching this exp_group ID
    cursor.execute("SELECT * FROM task_config WHERE exp_group=?", (exp_group,))
    task_config_data = cursor.fetchall()
    num_tasks = len(task_config_data)

    # Iterate over each row and get the image URL, annotation mode, classes, and pre-annotations
    index = 0
    for row in task_config_data:

        # The start-at term enables us to pick up where we left off due to a connection disruption
        if index < start_at:
            index += 1
            continue

        # The end-at term lets us limit the number of tasks created, such as for testing in the sandbox
        if index == end_at:
            return

        # Read the task config data
        img_url = row[1]
        annotation_mode = row[2]
        classes = row[3]
        pre_annotations = row[4]

        # Fix non-compliant data types
        pre_annotations, time_limit = other_utils.fix_non_compliant_task_parameters(pre_annotations, time_limit)

        # Create a HIT for this task instance
        create_segmentation_hit(mturk,
                                conn,
                                cursor,
                                question,
                                img_url,
                                classes,
                                annotation_mode,
                                pre_annotations,
                                exp_group,
                                reward_size,
                                time_limit,
                                qualification_requirements,
                                num_assignments_per_hit)
        index += 1

        if index % print_status_every_n == 0:
            print(f"Created HIT {index} of {num_tasks} for experiment group {exp_group}")




def create_segmentation_hit(mturk,
                            conn,
                            cursor,
                            question,
                            img_url=None,
                            classes=None,
                            annotation_mode=None,
                            pre_annotations=None,
                            exp_group=None,
                            reward=None,
                            time_limit=False,
                            qualification_requirements=None,
                            max_assignments=1):
    """
    Programmatically generate an MTurk HIT for the Duke HAL segmentation experiment

    :param mturk: the mturk client instance
    :param conn: a connection to the sqlite3 database
    :param cursor: the database client
    :param question: the MTurk question XML
    :param img_url: the image to annotate
    :param classes: the list of objet classes to display in the user interface
    :param annotation_mode: the drawing modes available or annotation
    :param pre_annotations: the pre-annotations to display in the user interface
    :param exp_group: the experiment group
    :param reward: the reward size, in dollars
    :param time_limit: True if there is a 3-minute time limit, false otherwise
    :param qualification_requirements: the list of qualifications that must be met to accept the HIT
    :param max_assignments: the number of repeats of this hit to be posted
    :return: the HIT Id
    """

    num_objects_instruction = 'ALL objects'         # Text that appears in the MTurk details section
    num_objects_headline = 'THREE'                  # Text that appears at the top of the HIT
    training_group_label = 1                        # Number that appears in the HIT title for training tasks

    # Fill in the HIT-specific layout parameters by overwriting the default text in the html
    if img_url is not None and img_url != 'demo':
        question = question.replace('${img_url}', img_url)
    if classes is not None and classes != 'all':
        question = question.replace('${classes}', classes)
    if annotation_mode is not None:
        question = question.replace('${annotation_mode}', annotation_mode)
    # TODO: handle preannotations once that functionality is available

    # Set the experiment group data, which influences the instruction text
    if exp_group is None:
        exp_group = 'api_test'
    else:
        # If the experiment group specifies the number of objects to annotate, clearly indicate that in the instructions
        if '-' in exp_group:
            count = exp_group.split('-')[1]
            if count == '1':
                num_objects_instruction = 'ONE object'
                num_objects_headline = 'ONE'
            elif count == '2':
                num_objects_instruction = 'TWO objects'
                num_objects_headline = 'TWO'
                training_group_label = 2
            elif count == '3':
                num_objects_instruction = 'THREE objects'
                num_objects_headline = 'THREE'
                training_group_label = 3
            elif count == '4':
                num_objects_instruction = 'FOUR objects'
                num_objects_headline = 'FOUR'
                training_group_label = 4
            elif count == '5':
                num_objects_instruction = 'FIVE objects'
                num_objects_headline = 'FIVE'
                training_group_label = 5
    requester_annotation = exp_group                       # This is a private string that assists API searches

    # Update the headline text to describe the intended number of objects to annotate
    question = question.replace('[**X**]', num_objects_headline)

    # Set the reward size
    if isinstance(reward, numbers.Number) and 0 < reward <= 0.10:
        reward = str(reward)
    else:
        reward = '0.06'

    # Set the duration and lifespan variables
    assignment_duration_in_seconds = 3600           # 1 hour
    if time_limit:
        assignment_duration_in_seconds = 180        # 3 minutes
    lifetime_in_seconds = 2419200                      # 28 days
    auto_approval_delay_in_seconds = 604800         # 7 days

    # Set the title and instruction data
    title = f'Duke HAL Image Segmentation Task ({exp_group})'
    if exp_group.startswith('qual'):
        title = f'Duke HAL Image Segmentation Training (group {training_group_label})'
    description = f'In this task, you will provide segmentation annotations for images. ' \
                  f'This requires you to mark all of the pixels that make up an object as closely as possible. ' \
                  f'In these images, you should mark {num_objects_instruction} from the classes listed.'
    keywords = 'segmentation, annotation, label, image, qualification'

    # Create a dictionary of the hit parameters
    hit_params = {
        'Title': title,
        'Description': description,
        'Keywords': keywords,
        'Reward': reward,
        'MaxAssignments': max_assignments,
        'AssignmentDurationInSeconds': assignment_duration_in_seconds,
        'LifetimeInSeconds': lifetime_in_seconds,
        'AutoApprovalDelayInSeconds': auto_approval_delay_in_seconds,
        'Question': question,
        'RequesterAnnotation': requester_annotation
    }
    if qualification_requirements is not None:
        hit_params['QualificationRequirements'] = qualification_requirements

    # Send the HIT to MTurk
    response = mturk.create_hit(**hit_params)

    # Get the HIT data to store in the database
    hit_id = response['HIT']['HITId']
    mturk_type = mturk_client.get_mturk_type(mturk)
    status = "Open"

    # Enter a record of the HIT in the database
    cursor.execute("INSERT INTO hits "
                   "(hit_id, mturk_type, exp_group, image_url, classes, annotation_mode, pre_annotations, status) "
                   "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                   (hit_id, mturk_type, exp_group, img_url, classes, annotation_mode, pre_annotations, status))
    conn.commit()

    return hit_id


def load_html_as_mturk_question(html_file_path):
    """
    Takes an html file and converts it to the XML format required for MTurk tasks
    :param html_file_path: the path to the html file
    :return: the xml text for the MTurk task
    """

    with open(html_file_path, 'r') as f:
        html_content = f.read()
    xml_content = f"""
<HTMLQuestion xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2011-11-11/HTMLQuestion.xsd">
  <HTMLContent><![CDATA[<!DOCTYPE html>
  <script src="https://assets.crowd.aws/crowd-html-elements.js"></script>
  <crowd-form answer-format="flatten-objects">
  {html_content}
  </crowd-form>
  ]]></HTMLContent>
  <FrameHeight>0</FrameHeight>
</HTMLQuestion>
        """
    return xml_content
