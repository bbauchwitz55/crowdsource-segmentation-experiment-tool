import boto3


def create_mturk_instance(sandbox=False):
    """
    Creates an mturk client instance
    :param sandbox: if True, creates a client for the sandbox environment, else creates a client for the production environment
    :return: the mturk client
    """
    if sandbox:
        mturk = boto3.client('mturk',
                             region_name='us-east-1',
                             endpoint_url='https://mturk-requester-sandbox.us-east-1.amazonaws.com'
                             )
    else:
        mturk = boto3.client('mturk',
                             region_name='us-east-1',
                             )
    return mturk


def get_mturk_type(mturk):
    """
    For an mturk client instance, determines whether it is a production or sandbox client
    :param mturk: the mturk client
    :return: 'sandbox' if this is a sandbox client, 'production' otherwise
    """
    mturk_type = 'production'
    if 'sandbox' in mturk._endpoint.host:
        mturk_type = 'sandbox'
    return mturk_type