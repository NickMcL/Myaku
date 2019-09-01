"""Backups a mongo instance with mongodump and stores dumps in AWS S3.

Requires that the following four env vars be set:
    DB_USERNAME_FILE - Path to a file containing the username to use to connect
        to the MongoDB instance.
    DB_PASSWORD_FILE - Path to a file containing the password to use to connect
        to the MongoDB instance.
    AWS_ACCESS_KEY_ID_FILE - Path to a file containing the access key ID to use
        to connect to AWS.
    AWS_SECRET_ACCESS_KEY_FILE - Path to a file containing the secret access
        key to use to connect to AWS.
    BACKUP_CONFIG_FILE - Path to a yaml file containing at minimum the
        mandatory settings to use for the backups. See below for details on
        these settings.

The password/key files can be supplied securely using docker secrets. The
config file can be supplied using a docker config.

The following parameters can be set in the yaml config file:
    --- MANDATORY PARAMETERS ---
    db_host - The host for the MongoDB instance to backup.
    max_allowed_backups - The max number of backups to store in S3
        at a given time. If this max is exceeded, the oldest backups will be
        deleted to keep the total within the max.
    aws_region_name - Name of the AWS region to use when connecting to AWS for
        S3 operations.
    aws_s3_backup_bucket - Name of the S3 bucket to store the backups in.

    --- OPTIONAL PARAMETERS ---
    aws_s3_backup_bucket_prefix' - Prefix to apply to all of the backups when
        storing in the S3 bucket specified by aws_s3_backup_bucket.
    aws_s3_storage_class - S3 storage class to use for the backups. If not
        given, will use STANDARD_IA by default.
    aws_s3_object_metadata - Dictionary of tag: value pairs to apply as
        metadata for the objects for the backups uploaded to S3. If not given,
        will not apply any metadata to the backup objects
"""

import logging
import os
import posixpath
import subprocess
import sys
import time
import threading
from datetime import datetime
from logging.handlers import RotatingFileHandler
from operator import itemgetter
from pprint import pformat
from typing import Any, Dict, List

import yaml
from boto3.session import Session
from botocore import client

_log = logging.getLogger(__name__)

_CONFIG_FILE_PATH_ENV_VAR = 'BACKUP_CONFIG_FILE'

_LOG_DIR_ENV_VAR = 'LOG_DIR'
_LOG_FILENAME_BASE = 'mongobackup'
_LOGGING_FORMAT = '%(asctime)s:%(name)s:%(levelname)s: %(message)s'

_LOG_ROTATING_BACKUP_COUNT = 5
_LOG_MAX_SIZE_ENV_VAR = 'LOG_MAX_SIZE'
_LOG_MAX_SIZE_DEFAULT = 1024 * 1024 * 20  # 20 MB

# All of these file environment variables must be set, or the script will raise
# an error.
_DB_USERNAME_FILE_ENV_VAR = 'DB_USERNAME_FILE'
_DB_PASSWORD_FILE_ENV_VAR = 'DB_PASSWORD_FILE'
_AWS_ACCESS_KEY_ID_FILE_ENV_VAR = 'AWS_ACCESS_KEY_ID_FILE'
_AWS_SECRET_ACCESS_KEY_FILE_ENV_VAR = 'AWS_SECRET_ACCESS_KEY_FILE'

_CONFIG_KEYS = [
    # Mandatory
    'db_host',
    'max_allowed_backups',
    'aws_region_name',
    'aws_s3_backup_bucket',

    # Optional. Uses default value if not given.
    'aws_s3_backup_bucket_prefix',
    'aws_s3_storage_class',
    'aws_s3_object_metadata',
]

_CONFIG_DEFAULT_VALUES = {
    'aws_s3_backup_bucket_prefix': '',
    'aws_s3_storage_class': 'STANDARD_IA',
    'aws_s3_object_metadata': {}
}

# Backups are dumped here temporarily before uploading to S3.
_BACKUP_TMP_DIR = '/tmp/'

_BACKUP_FILENAME_SUFFIX = '_backup.gz'


class UploadProgressLogger(object):
    """Logs the progress of an upload to S3."""

    MIN_TIME_BETWEEN_LOGS = 1  # in seconds

    def __init__(self, filepath: str) -> None:
        """Inits the progress tracking."""
        self._filepath = filepath
        self._file_size = os.path.getsize(filepath)
        self._uploaded_so_far = 0
        self._last_log_time = time.monotonic()
        self._lock = threading.Lock()

    def __call__(self, bytes_uploaded: int) -> None:
        """Adds bytes_uploaded to upload progress and logs current progress."""
        with self._lock:
            self._uploaded_so_far += bytes_uploaded

            time_since_last_log = time.monotonic() - self._last_log_time
            if (self._uploaded_so_far != self._file_size
                    and time_since_last_log < self.MIN_TIME_BETWEEN_LOGS):
                return

            percentage_uploaded = (
                (self._uploaded_so_far / self._file_size) * 100
            )
            _log.info(
                'Uploading %s to S3: %s / %s MB (%.1f%%)',
                self._filepath, round(self._uploaded_so_far / (1024 * 1024)),
                round(self._file_size / (1024 * 1024)), percentage_uploaded
            )
            self._last_log_time = time.monotonic()


def setup_logger() -> logging.Logger:
    """Sets up the logger for the script.

    Writes the log to both stderr and to a rotating file.

    Returns:
        The setup logger to use for the script.
    """
    log_dir = os.environ.get(_LOG_DIR_ENV_VAR)
    if not _LOG_DIR_ENV_VAR:
        raise RuntimeError(
            f'Log directory env variable "{_LOG_DIR_ENV_VAR}" is not set'
        )
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logging.Formatter.converter = time.gmtime  # Use UTC time for timestamps
    log_formatter = logging.Formatter(_LOGGING_FORMAT)

    log_max_size = int(
        os.environ.get(_LOG_MAX_SIZE_ENV_VAR, _LOG_MAX_SIZE_DEFAULT)
    )
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, _LOG_FILENAME_BASE + '.info.log'),
        maxBytes=log_max_size // (_LOG_ROTATING_BACKUP_COUNT + 1),
        backupCount=_LOG_ROTATING_BACKUP_COUNT
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(log_formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(log_formatter)
    logger.addHandler(stream_handler)

    return logger


def read_value_from_env_file(env_file_var: str) -> str:
    """Reads a value from a file specified by an environment variable.

    Args:
        env_file_var: Environment variable specifying the path to the file to
            read the value from.

    Returns:
        The read value.

    Raises:
        RuntimeError: The value could not be read from the environment.
    """
    filepath = os.environ.get(env_file_var)
    if filepath is None:
        raise RuntimeError(
            f'File environment variable "{env_file_var}" is not set in the '
            f'environment and has no default value'
        )

    if not os.path.exists(filepath):
        raise RuntimeError(
            f'The file path "{filepath}" specified by file environment '
            f'variable "{env_file_var}" does not exist'
        )

    with open(filepath, 'r') as file:
        value = file.read()
    if not value:
        raise RuntimeError(
            f'The file at path "{filepath}" specified by file environment '
            f'variable "{env_file_var}" is empty'
        )

    return value


def load_script_config() -> Dict:
    """Loads the yaml config for the script.

    If a value is not explictly definited in the loaded config file, sets the
    default value for it in the returned config dict.
    """
    config_file_data = read_value_from_env_file(_CONFIG_FILE_PATH_ENV_VAR)
    config = yaml.safe_load(config_file_data)
    for key in config:
        if key not in _CONFIG_KEYS:
            raise RuntimeError(f'Unrecognized key in config file: "{key}"')

    for key in _CONFIG_KEYS:
        if key in config:
            continue

        if key in _CONFIG_DEFAULT_VALUES:
            _log.info(
                'Using default value "%s" for config key "%s"',
                _CONFIG_DEFAULT_VALUES[key], key
            )
            config[key] = _CONFIG_DEFAULT_VALUES[key]
        else:
            raise RuntimeError(
                f'Missing manadatory key in config file: "{key}"'
            )

    _log.info('Loaded script config:\n%s', pformat(config))
    return config


def setup_aws_s3_client(config: Dict) -> client.BaseClient:
    """Sets up the client for accessing AWS S3.

    Args:
        config: Complete config for the script.

    Returns:
        Setup AWS S3 client.
    """
    # The access key values are secrets, so they are stored in separate files
    # from the script config file.
    aws_access_key_id = read_value_from_env_file(
        _AWS_ACCESS_KEY_ID_FILE_ENV_VAR
    )
    aws_secret_access_key = read_value_from_env_file(
        _AWS_SECRET_ACCESS_KEY_FILE_ENV_VAR
    )
    session = Session(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=config['aws_region_name']
    )

    return session.client('s3')


def create_local_backup(config: Dict) -> str:
    """Creates a local backup of the mongo instance.

    Args:
        config: Complete config for the script.

    Returns:
        The path to the locally created backup of the mongo instance.
    """
    # The DB creds are secrets, so they are stored in separate files from the
    # script config file.
    db_username = read_value_from_env_file(_DB_USERNAME_FILE_ENV_VAR)
    db_password = read_value_from_env_file(_DB_PASSWORD_FILE_ENV_VAR)

    backup_path = os.path.join(
        _BACKUP_TMP_DIR,
        datetime.utcnow().isoformat().replace(':', ',')
        + _BACKUP_FILENAME_SUFFIX
    )
    mongodump_cmd = [
        'mongodump',
        '-h', config['db_host'], '-u', db_username, '-p', db_password,
        '--gzip', f'--archive={backup_path}'
    ]

    _log.info(
        'Running mongodump to create mongo instance backup at "%s"',
        backup_path
    )
    proc = subprocess.Popen(
        mongodump_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True
    )
    for line in proc.stdout:
        _log.info(line.strip())

    return_code = proc.wait()
    if (return_code != 0):
        raise RuntimeError(
            'mongodump failed with non-zero return code %s', return_code
        )
    _log.info(
        'Mongo instance backup created successfully at "%s"', backup_path
    )

    return backup_path


def upload_backup_to_s3(
    backup_path: str, s3_client: client.BaseClient, config: Dict
) -> None:
    """Uploads a local backup to S3.

    Deletes the local backup file if the upload to S3 was successful.

    Args:
        backup_path: Local path to the backup file.
        s3_client: Client to use for S3 operations.
        config: Complete config for the script.
    """
    backup_s3_key = posixpath.join(
        config['aws_s3_backup_bucket_prefix'], os.path.split(backup_path)[1]
    )
    backup_s3_uri = 's3://{}/{}'.format(
        config['aws_s3_backup_bucket'], backup_s3_key
    )
    extra_args = {
        'Metadata': config['aws_s3_object_metadata'],
        'StorageClass': config['aws_s3_storage_class']
    }

    _log.info(
        'Will upload backup at "%s" to "%s" with extra args:\n%s',
        backup_path, backup_s3_uri, pformat(extra_args)
    )
    s3_client.upload_file(
        Filename=backup_path,
        Bucket=config['aws_s3_backup_bucket'],
        Key=backup_s3_key,
        ExtraArgs=extra_args,
        Callback=UploadProgressLogger(backup_path)
    )
    _log.info('Backup upload completed')

    _log.info('Removing local backup at "%s"', backup_path)
    os.remove(backup_path)
    _log.info('Local backup at "%s" removed successfully', backup_path)


def delete_backups_from_s3(
    backup_objs: List[Dict[str, Any]], s3_client: client.BaseClient,
    config: Dict
) -> None:
    """Deletes backups from S3.

    Args:
        backup_objs: Object JSON return by a list_objects_v2 call for each of
            the backup objects to delete.
        s3_client: Client to use for S3 operations.
        config: Complete config for the script.
    """
    _log.info(
        'Will delete the following backup object(s) from bucket "%s":\n%s',
        config['aws_s3_backup_bucket'], pformat(backup_objs)
    )
    obj_delete_dicts = [{'Key': o['Key']} for o in backup_objs]
    response = s3_client.delete_objects(
        Bucket=config['aws_s3_backup_bucket'],
        Delete={'Objects': obj_delete_dicts}
    )

    if 'Errors' in response and len(response['Errors']) > 0:
        raise RuntimeError(
            'S3 delete request responded with error(s):\n%s', pformat(response)
        )
    _log.info(
        'Deletion was successful. Response from S3:\n%s', pformat(response)
    )


def delete_excess_backups_from_s3(
    s3_client: client.BaseClient, config: Dict
) -> None:
    """Deletes backups in excess of the allowed max from S3.

    If there are more backups stored in S3 than the allowed max, deletes
    the oldest backups until the backup count is equal to the allowed max.

    Args:
        s3_client: Client to use for S3 operations.
        config: Complete config for the script.
    """
    response = s3_client.list_objects_v2(
        Bucket=config['aws_s3_backup_bucket'],
        Prefix=config['aws_s3_backup_bucket_prefix']
    )

    backup_objs = []
    for obj in response['Contents']:
        if obj['Key'].endswith(_BACKUP_FILENAME_SUFFIX):
            backup_objs.append(obj)

    backup_uri_prefix = 's3://{}/{}'.format(
        config['aws_s3_backup_bucket'], config['aws_s3_backup_bucket_prefix']
    )
    if len(backup_objs) <= config['max_allowed_backups']:
        _log.info(
            'The current number of backups stored under "%s" (%s) is within '
            'the allowable max (%s)',
            backup_uri_prefix, len(backup_objs), config['max_allowed_backups']
        )
        return

    delete_count = len(backup_objs) - config['max_allowed_backups']
    _log.info(
        'The current number of backups stored under "%s" (%s) is greater than '
        'the allowable max (%s), so will delete %s backup(s)',
        backup_uri_prefix, len(backup_objs), config['max_allowed_backups'],
        delete_count
    )
    delete_backups_from_s3(
        sorted(backup_objs, key=itemgetter('LastModified'))[:delete_count],
        s3_client, config
    )


def main() -> None:
    """Runs the full mongo backup to AWS S3 script."""
    _log.info('Started mongo backup to S3 script')

    config = load_script_config()
    s3_client = setup_aws_s3_client(config)

    backup_path = create_local_backup(config)
    upload_backup_to_s3(backup_path, s3_client, config)
    delete_excess_backups_from_s3(s3_client, config)

    _log.info('Finished mongo backup to S3 script')


if __name__ == '__main__':
    _log = setup_logger()
    try:
        main()
    except BaseException:
        _log.exception('Unhandled exception in main')
        raise
