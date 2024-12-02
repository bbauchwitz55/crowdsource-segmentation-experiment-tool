import requests
from io import BytesIO
from PIL import Image


def get_image_size_from_url(url):
    """
    Tests that the url links to an image and returns the height and width of the image if so
    :param url: the url to check
    :return: width, height if image found, None otherwise
    """

    try:
        r = requests.head(url)
        if r.status_code == requests.codes.ok:
            r = requests.get(url)
            image = Image.open(BytesIO(r.content))
            width, height = image.size
            return width, height
        else:
            print(f"Image {url} was not found!")
            return None
    except:
        print(f"Image {url} was not found!")
        return None


def fix_non_compliant_task_parameters(pre_annotations, time_limit):
    """
    SQLite stores boolean and null values as ints and strings repsectively.
    Transform the datatypes for compatibility with MTurk API
    :param pre_annotations: the pre_annotations string from the hits database record, which may be 'None'
    :param time_limit: the time_limit boolean from the hits database record, which is stored as 0 or 1
    :return: the corrected pre_annotations and time_limit variables
    """

    if pre_annotations == 'None':
        pre_annotations = None
    if time_limit == 0:
        time_limit = False
    else:
        time_limit = True
    return pre_annotations, time_limit


def add_leading_zeros_to_coco_image_ID(image_ID):
    """
    During pre-processing, the leading 0s in the coco image IDs may have been dropped.
    This method adds them back in.
    :param image_ID: the current image_ID, either as an int or a string
    :return: the string image ID with the appropriate number of leading zeros
    """

    ## Many image IDs are purely numeric, so standardize to strings for comparison
    image_ID = str(image_ID)

    # If the image_ID isn't already numeric, it can't be a coco image_ID
    if not image_ID.isnumeric():
        return image_ID

    # The coco image ID should be a 12-digit number with leading zeros
    while len(image_ID) < 12:
        image_ID = "0" + image_ID
    return image_ID


def contains_two_substrinsgs(large_string, substrings):
    """
    :param large_string: a string to evaluate
    :param substrings: a llist of potential substrings that may be in the large string
    :return: True if at least two different substrings are present in the large string, False otherwise
    """
    count = 0
    for substring in substrings:
        if substring in large_string:
            count += 1
        if count >= 2:
            return True
    return False