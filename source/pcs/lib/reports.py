from __future__ import (
    absolute_import,
    division,
    print_function,
)

from functools import partial

from pcs.common import report_codes
from pcs.lib.errors import ReportItem, ReportItemSeverity

def forceable_error(force_code, report_creator, *args, **kwargs):
    """
    Return ReportItem created by report_creator.

    This is experimental shortcut for common pattern. It is intended to
    cooperate with functions "error" and  "warning".
    the pair with function "warning".

    string force_code is code for forcing error
    callable report_creator is function that produce ReportItem. It must take
        parameters forceable (None or force code) and severity
        (from ReportItemSeverity)
    rest of args are for the report_creator
    """
    return report_creator(
        *args,
        forceable=force_code,
        severity=ReportItemSeverity.ERROR,
        **kwargs
    )

def warning(report_creator, *args, **kwargs):
    """
    Return ReportItem created by report_creator.

    This is experimental shortcut for common pattern. It is intended to
    cooperate with functions "error" and  "forceable_error".

    callable report_creator is function that produce ReportItem. It must take
        parameters forceable (None or force code) and severity
        (from ReportItemSeverity)
    rest of args are for the report_creator
    """
    return report_creator(
        *args,
        forceable=None,
        severity=ReportItemSeverity.WARNING,
        **kwargs
    )

def error(report_creator, *args, **kwargs):
    """
    Return ReportItem created by report_creator.

    This is experimental shortcut for common pattern. It is intended to
    cooperate with functions "forceable_error" and "forceable_error".

    callable report_creator is function that produce ReportItem. It must take
        parameters forceable (None or force code) and severity
        (from ReportItemSeverity)
    rest of args are for the report_creator
    """
    return report_creator(
        *args,
        forceable=None,
        severity=ReportItemSeverity.ERROR,
        **kwargs
    )

def get_problem_creator(force_code=None, is_forced=False):
    """
    Returns report creator wraper (forceable_error or warning).

    This is experimental shortcut for decision if ReportItem will be
    either forceable_error or warning.

    string force_code is code for forcing error. It could be usefull to prepare
        it for whole module by using functools.partial.
    bool warn_only is flag for selecting wrapper
    """
    if not force_code:
        return error
    if is_forced:
        return warning
    return partial(forceable_error, force_code)

def common_error(text):
    # TODO replace by more specific reports
    """
    unspecified error with text message, do not use unless absolutely necessary
    """
    return ReportItem.error(
        report_codes.COMMON_ERROR,
        info={"text": text}
    )

def common_info(text):
    # TODO replace by more specific reports
    """
    unspecified info with text message, do not use unless absolutely necessary
    """
    return ReportItem.info(
        report_codes.COMMON_INFO,
        info={"text": text}
    )

def resource_for_constraint_is_multiinstance(
    resource_id, parent_type, parent_id,
    severity=ReportItemSeverity.ERROR, forceable=None
):
    """
    when setting up a constraint a resource in a clone or a master was specified
    resource_id string specified resource
    parent_type string "clone" or "master"
    parent_id clone or master resource id
    severity report item severity
    forceable is this report item forceable? by what category?
    """
    return ReportItem(
        report_codes.RESOURCE_FOR_CONSTRAINT_IS_MULTIINSTANCE,
        severity,
        info={
            "resource_id": resource_id,
            "parent_type": parent_type,
            "parent_id": parent_id,
        },
        forceable=forceable
    )

def duplicate_constraints_exist(
    constraint_type, constraint_info_list,
    severity=ReportItemSeverity.ERROR, forceable=None
):
    """
    when creating a constraint it was detected the constraint already exists
    constraint_type string "rsc_colocation", "rsc_order", "rsc_ticket"
    constraint_info_list list of structured constraint data according to type
    severity report item severity
    forceable is this report item forceable? by what category?
    """
    return ReportItem(
        report_codes.DUPLICATE_CONSTRAINTS_EXIST,
        severity,
        info={
            "constraint_type": constraint_type,
            "constraint_info_list": constraint_info_list,
        },
        forceable=forceable
    )

def empty_resource_set_list():
    """
    an empty resource set has been specified, which is not allowed by cib schema
    """
    return ReportItem.error(
        report_codes.EMPTY_RESOURCE_SET_LIST,
    )

def required_option_is_missing(
    option_names, option_type=None,
    severity=ReportItemSeverity.ERROR, forceable=None
):
    """
    required option has not been specified, command cannot continue
    list name is/are required but was not entered
    option_type describes the option
    severity report item severity
    forceable is this report item forceable? by what category?
    """
    return ReportItem(
        report_codes.REQUIRED_OPTION_IS_MISSING,
        severity,
        forceable=forceable,
        info={
            "option_names": option_names,
            "option_type": option_type,
        }
    )

def prerequisite_option_is_missing(
    option_name, prerequisite_name, option_type="", prerequisite_type=""
):
    """
    if the option_name is specified, the prerequisite_option must be specified
    string option_name -- an option which depends on the prerequisite_option
    string prerequisite_name -- the prerequisite option
    string option_type -- describes the option
    string prerequisite_type -- describes the prerequisite_option
    """
    return ReportItem.error(
        report_codes.PREREQUISITE_OPTION_IS_MISSING,
        info={
            "option_name": option_name,
            "option_type": option_type,
            "prerequisite_name": prerequisite_name,
            "prerequisite_type": prerequisite_type,
        }
    )

def required_option_of_alternatives_is_missing(
    option_names, option_type=None
):
    """
    at least one option has to be specified
    iterable option_names -- options from which at least one has to be specified
    string option_type -- describes the option
    """
    severity = ReportItemSeverity.ERROR
    forceable = None
    return ReportItem(
        report_codes.REQUIRED_OPTION_OF_ALTERNATIVES_IS_MISSING,
        severity,
        forceable=forceable,
        info={
            "option_names": option_names,
            "option_type": option_type,
        }
    )

def invalid_options(
    option_names, allowed_options, option_type, allowed_option_patterns=None,
    severity=ReportItemSeverity.ERROR, forceable=None
):
    """
    specified option names are not valid, usualy an error or a warning

    list option_names -- specified invalid option names
    list allowed_options -- possible allowed option names
    string option_type -- describes the option
    list allowed_option_patterns -- allowed user defind options patterns
    string severity -- report item severity
    mixed forceable -- is this report item forceable? by what category?
    """
    return ReportItem(
        report_codes.INVALID_OPTIONS,
        severity,
        forceable,
        info={
            "option_names": option_names,
            "option_type": option_type,
            "allowed": sorted(allowed_options),
            "allowed_patterns": sorted(allowed_option_patterns or []),
        }
    )

def invalid_userdefined_options(
    option_names, allowed_description, option_type,
    severity=ReportItemSeverity.ERROR, forceable=None
):
    """
    specified option names defined by a user are not valid

    This is different than invalid_options. In this case, the options are
    supposed to be defined by a user. This report carries information that the
    option names do not meet requirements, i.e. contain not allowed characters.
    Invalid_options is used when the options are predefined by pcs (or
    underlying tools).

    list option_names -- specified invalid option names
    string allowed_description -- describes what option names should look like
    string option_type -- describes the option
    string severity -- report item severity
    mixed forceable -- is this report item forceable? by what category?
    """
    return ReportItem(
        report_codes.INVALID_USERDEFINED_OPTIONS,
        severity,
        forceable,
        info={
            "option_names": sorted(option_names),
            "option_type": option_type,
            "allowed_description": allowed_description,
        }
    )

def invalid_option_type(option_name, allowed_types):
    """
    specified value is not of a valid type for the option
    string option_name -- option name whose value is not of a valid type
    list|string allowed_types -- list of allowed types or string description
    """
    return ReportItem.error(
        report_codes.INVALID_OPTION_TYPE,
        info={
            "option_name": option_name,
            "allowed_types": allowed_types,
        },
    )

def invalid_option_value(
    option_name, option_value, allowed_values,
    severity=ReportItemSeverity.ERROR, forceable=None
):
    """
    specified value is not valid for the option, usualy an error or a warning
    option_name specified option name whose value is not valid
    option_value specified value which is not valid
    allowed_options list of allowed values or string description
    severity report item severity
    forceable is this report item forceable? by what category?
    """
    return ReportItem(
        report_codes.INVALID_OPTION_VALUE,
        severity,
        info={
            "option_value": option_value,
            "option_name": option_name,
            "allowed_values": allowed_values,
        },
        forceable=forceable
    )

def deprecated_option(
    option_name, replaced_by_options, option_type,
    severity=ReportItemSeverity.ERROR, forceable=None
):
    """
    Specified option name is deprecated and has been replaced by other option(s)

    string option_name -- the deprecated option
    iterable or string replaced_by_options -- new option(s) to be used instead
    string option_type -- option description
    string severity -- report item severity
    string forceable -- a category by which the report is forceable
    """
    return ReportItem(
        report_codes.DEPRECATED_OPTION,
        severity,
        info={
            "option_name": option_name,
            "option_type": option_type,
            "replaced_by": sorted(replaced_by_options),
        },
        forceable=forceable
    )

def mutually_exclusive_options(option_names, option_type):
    """
    entered options can not coexist
    set option_names contain entered mutually exclusive options
    string option_type describes the option
    """
    return ReportItem.error(
        report_codes.MUTUALLY_EXCLUSIVE_OPTIONS,
        info={
            "option_names": option_names,
            "option_type": option_type,
        },
    )

def invalid_cib_content(report):
    """
    Given cib content is not valid.
    string report -- is human readable explanation of a cib invalidity. For
        example a stderr of `crm_verify`.
    """
    return ReportItem.error(
        report_codes.INVALID_CIB_CONTENT,
        info={
            "report": report,
        }
    )



def invalid_id_is_empty(id, id_description):
    """
    empty string was specified as an id, which is not valid
    id string specified id
    id_description string decribe id's role
    """
    return ReportItem.error(
        report_codes.EMPTY_ID,
        info={
            "id": id,
            "id_description": id_description,
        }
    )

def invalid_id_bad_char(id, id_description, bad_char, is_first_char):
    """
    specified id is not valid as it contains a forbidden character
    id string specified id
    id_description string decribe id's role
    bad_char forbidden character
    is_first_char is it the first character which is forbidden?
    """
    return ReportItem.error(
        report_codes.INVALID_ID,
        info={
            "id": id,
            "id_description": id_description,
            "is_first_char": is_first_char,
            "invalid_character": bad_char,
        }
    )

def invalid_timeout(timeout):
    """
    specified timeout is not valid (number or other format e.g. 2min)
    timeout string specified invalid timeout
    """
    return ReportItem.error(
        report_codes.INVALID_TIMEOUT_VALUE,
        info={"timeout": timeout}
    )

def invalid_score(score):
    """
    specified score value is not valid
    score specified score value
    """
    return ReportItem.error(
        report_codes.INVALID_SCORE,
        info={
            "score": score,
        }
    )

def multiple_score_options():
    """
    more than one of mutually exclusive score options has been set
    (score, score-attribute, score-attribute-mangle in rules or colocation sets)
    """
    return ReportItem.error(
        report_codes.MULTIPLE_SCORE_OPTIONS,
    )

def run_external_process_started(command, stdin, environment):
    """
    information about running an external process
    command string the external process command
    stdin string passed to the external process via its stdin
    """
    return ReportItem.debug(
        report_codes.RUN_EXTERNAL_PROCESS_STARTED,
        info={
            "command": command,
            "stdin": stdin,
            "environment": environment,
        }
    )

def run_external_process_finished(command, retval, stdout, stderr):
    """
    information about result of running an external process
    command string the external process command
    retval external process's return (exit) code
    stdout string external process's stdout
    stderr string external process's stderr
    """
    return ReportItem.debug(
        report_codes.RUN_EXTERNAL_PROCESS_FINISHED,
        info={
            "command": command,
            "return_value": retval,
            "stdout": stdout,
            "stderr": stderr,
        }
    )

def run_external_process_error(command, reason):
    """
    attempt to run an external process failed
    command string the external process command
    reason string error description
    """
    return ReportItem.error(
        report_codes.RUN_EXTERNAL_PROCESS_ERROR,
        info={
            "command": command,
            "reason": reason
        }
    )

def node_communication_started(target, data):
    """
    request is about to be sent to a remote node, debug info
    target string where the request is about to be sent to
    data string request's data
    """
    return ReportItem.debug(
        report_codes.NODE_COMMUNICATION_STARTED,
        info={
            "target": target,
            "data": data,
        }
    )

def node_communication_finished(target, retval, data):
    """
    remote node request has been finished, debug info
    target string where the request was sent to
    retval response return code
    data response data
    """
    return ReportItem.debug(
        report_codes.NODE_COMMUNICATION_FINISHED,
        info={
            "target": target,
            "response_code": retval,
            "response_data": data
        }
    )


def node_communication_debug_info(target, data):
    """
    Node communication debug info from pycurl
    """
    return ReportItem.debug(
        report_codes.NODE_COMMUNICATION_DEBUG_INFO,
        info={
            "target": target,
            "data": data,
        }
    )


def node_communication_not_connected(node, reason):
    """
    an error occured when connecting to a remote node, debug info
    node string node address / name
    reason string decription of the error
    """
    return ReportItem.debug(
        report_codes.NODE_COMMUNICATION_NOT_CONNECTED,
        info={
            "node": node,
            "reason": reason,
        }
    )


def node_communication_no_more_addresses(node, request):
    """
    request failed and there are no more addresses to try it again
    """
    return ReportItem.warning(
        report_codes.NODE_COMMUNICATION_NO_MORE_ADDRESSES,
        info={
            "node": node,
            "request": request,
        }
    )


def node_communication_error_not_authorized(
    node, command, reason,
    severity=ReportItemSeverity.ERROR, forceable=None
):
    """
    node rejected a request as we are not authorized
    node string node address / name
    reason string decription of the error
    """
    return ReportItem(
        report_codes.NODE_COMMUNICATION_ERROR_NOT_AUTHORIZED,
        severity,
        info={
            "node": node,
            "command": command,
            "reason": reason,
        },
        forceable=forceable
    )

def node_communication_error_permission_denied(
    node, command, reason,
    severity=ReportItemSeverity.ERROR, forceable=None
):
    """
    node rejected a request as we do not have permissions to run the request
    node string node address / name
    reason string decription of the error
    """
    return ReportItem(
        report_codes.NODE_COMMUNICATION_ERROR_PERMISSION_DENIED,
        severity,
        info={
            "node": node,
            "command": command,
            "reason": reason,
        },
        forceable=forceable
    )

def node_communication_error_unsupported_command(
    node, command, reason,
    severity=ReportItemSeverity.ERROR, forceable=None
):
    """
    node rejected a request as it does not support the request
    node string node address / name
    reason string decription of the error
    """
    return ReportItem(
        report_codes.NODE_COMMUNICATION_ERROR_UNSUPPORTED_COMMAND,
        severity,
        info={
            "node": node,
            "command": command,
            "reason": reason,
        },
        forceable=forceable
    )

def node_communication_command_unsuccessful(
    node, command, reason, severity=ReportItemSeverity.ERROR, forceable=None
):
    """
    node rejected a request for another reason with a plain text explanation
    node string node address / name
    reason string decription of the error
    """
    return ReportItem(
        report_codes.NODE_COMMUNICATION_COMMAND_UNSUCCESSFUL,
        severity,
        info={
            "node": node,
            "command": command,
            "reason": reason,
        },
        forceable=forceable
    )


def node_communication_error_other_error(
    node, command, reason,
    severity=ReportItemSeverity.ERROR, forceable=None
):
    """
    node rejected a request for another reason (may be faulty node)
    node string node address / name
    reason string decription of the error
    """
    return ReportItem(
        report_codes.NODE_COMMUNICATION_ERROR,
        severity,
        info={
            "node": node,
            "command": command,
            "reason": reason,
        },
        forceable=forceable
    )

def node_communication_error_unable_to_connect(
    node, command, reason,
    severity=ReportItemSeverity.ERROR, forceable=None
):
    """
    we were unable to connect to a node
    node string node address / name
    reason string decription of the error
    """
    return ReportItem(
        report_codes.NODE_COMMUNICATION_ERROR_UNABLE_TO_CONNECT,
        severity,
        info={
            "node": node,
            "command": command,
            "reason": reason,
        },
        forceable=forceable
    )


def node_communication_error_timed_out(
    node, command, reason,
    severity=ReportItemSeverity.ERROR, forceable=None
):
    """
    Communication with node timed out.
    """
    return ReportItem(
        report_codes.NODE_COMMUNICATION_ERROR_TIMED_OUT,
        severity,
        info={
            "node": node,
            "command": command,
            "reason": reason,
        },
        forceable=forceable
    )

def node_communication_proxy_is_set(node=None, address=None):
    """
    Warning when connection failed and there is proxy set in environment
    variables
    """
    return ReportItem.warning(
        report_codes.NODE_COMMUNICATION_PROXY_IS_SET,
        info={
            "node": node,
            "address": address,
        }
    )


def node_communication_retrying(node, failed_address, next_address, request):
    """
    Request failed due communication error connecting via specified address,
    therefore trying another address if there is any.
    """
    return ReportItem.warning(
        report_codes.NODE_COMMUNICATION_RETRYING,
        info={
            "node": node,
            "failed_address": failed_address,
            "next_address": next_address,
            "request": request,
        }
    )


def cannot_add_node_is_in_cluster(node):
    """
    Node is in cluster. It is not possible to add it as a new cluster node.
    """
    return ReportItem.error(
        report_codes.CANNOT_ADD_NODE_IS_IN_CLUSTER,
        info={"node": node}
    )

def cannot_add_node_is_running_service(node, service):
    """
    Node is running service. It is not possible to add it as a new cluster node.
    string node address of desired node
    string service name of service (pacemaker, pacemaker_remote)
    """
    return ReportItem.error(
        report_codes.CANNOT_ADD_NODE_IS_RUNNING_SERVICE,
        info={
            "node": node,
            "service": service,
        }
    )

def defaults_can_be_overriden():
    """
    Warning when settings defaults (op_defaults, rsc_defaults...)
    """
    return ReportItem.warning(report_codes.DEFAULTS_CAN_BE_OVERRIDEN)

def corosync_config_distribution_started():
    """
    corosync configuration is about to be sent to nodes
    """
    return ReportItem.info(
        report_codes.COROSYNC_CONFIG_DISTRIBUTION_STARTED,
    )

def corosync_config_accepted_by_node(node):
    """
    corosync configuration has been accepted by a node
    node string node address / name
    """
    return ReportItem.info(
        report_codes.COROSYNC_CONFIG_ACCEPTED_BY_NODE,
        info={"node": node}
    )

def corosync_config_distribution_node_error(
    node,
    severity=ReportItemSeverity.ERROR, forceable=None
):
    """
    communication error occured when saving corosync configuration to a node
    node string faulty node address / name
    """
    return ReportItem(
        report_codes.COROSYNC_CONFIG_DISTRIBUTION_NODE_ERROR,
        severity,
        info={"node": node},
        forceable=forceable
    )

def corosync_not_running_check_started():
    """
    we are about to make sure corosync is not running on nodes
    """
    return ReportItem.info(
        report_codes.COROSYNC_NOT_RUNNING_CHECK_STARTED,
    )

def corosync_not_running_check_node_error(
    node,
    severity=ReportItemSeverity.ERROR, forceable=None
):
    """
    communication error occured when checking corosync is not running on a node
    node string faulty node address / name
    """
    return ReportItem(
        report_codes.COROSYNC_NOT_RUNNING_CHECK_NODE_ERROR,
        severity,
        info={"node": node},
        forceable=forceable
    )

def corosync_not_running_on_node_ok(node):
    """
    corosync is not running on a node, which is ok
    node string node address / name
    """
    return ReportItem.info(
        report_codes.COROSYNC_NOT_RUNNING_ON_NODE,
        info={"node": node}
    )

def corosync_running_on_node_fail(node):
    """
    corosync is running on a node, which is not ok
    node string node address / name
    """
    return ReportItem.error(
        report_codes.COROSYNC_RUNNING_ON_NODE,
        info={"node": node}
    )

def corosync_quorum_get_status_error(reason):
    """
    unable to get runtime status of quorum on local node
    string reason an error message
    """
    return ReportItem.error(
        report_codes.COROSYNC_QUORUM_GET_STATUS_ERROR,
        info={
            "reason": reason,
        }
    )

def corosync_quorum_heuristics_enabled_with_no_exec():
    """
    no exec_ is specified, therefore heuristics are effectively disabled
    """
    return ReportItem.warning(
        report_codes.COROSYNC_QUORUM_HEURISTICS_ENABLED_WITH_NO_EXEC
    )

def corosync_quorum_set_expected_votes_error(reason):
    """
    unable to set expcted votes in a live cluster
    string reason an error message
    """
    return ReportItem.error(
        report_codes.COROSYNC_QUORUM_SET_EXPECTED_VOTES_ERROR,
        info={
            "reason": reason,
        }
    )

def corosync_config_reloaded():
    """
    corosync configuration has been reloaded
    """
    return ReportItem.info(
        report_codes.COROSYNC_CONFIG_RELOADED,
    )

def corosync_config_reload_error(reason):
    """
    an error occured when reloading corosync configuration
    reason string an error message
    """
    return ReportItem.error(
        report_codes.COROSYNC_CONFIG_RELOAD_ERROR,
        info={"reason": reason}
    )

def corosync_config_read_error(path, reason):
    """
    an error occured when reading corosync configuration file from disk
    reason string an error message
    """
    return ReportItem.error(
        report_codes.UNABLE_TO_READ_COROSYNC_CONFIG,
        info={
            "path": path,
            "reason": reason,
        }
    )

def corosync_config_parser_missing_closing_brace():
    """
    corosync config cannot be parsed due to missing closing brace
    """
    return ReportItem.error(
        report_codes.PARSE_ERROR_COROSYNC_CONF_MISSING_CLOSING_BRACE,
    )

def corosync_config_parser_unexpected_closing_brace():
    """
    corosync config cannot be parsed due to unexpected closing brace
    """
    return ReportItem.error(
        report_codes.PARSE_ERROR_COROSYNC_CONF_UNEXPECTED_CLOSING_BRACE,
    )

def corosync_config_parser_other_error():
    """
    corosync config cannot be parsed, the cause is not specified
    It is better to use more specific error if possible.
    """
    return ReportItem.error(
        report_codes.PARSE_ERROR_COROSYNC_CONF,
    )

def corosync_options_incompatible_with_qdevice(options):
    """
    cannot set specified corosync options when qdevice is in use
    iterable options incompatible options names
    """
    return ReportItem.error(
        report_codes.COROSYNC_OPTIONS_INCOMPATIBLE_WITH_QDEVICE,
        info={
            "options_names": options,
        }
    )

def qdevice_already_defined():
    """
    qdevice is already set up in a cluster, when it was expected not to be
    """
    return ReportItem.error(
        report_codes.QDEVICE_ALREADY_DEFINED,
    )

def qdevice_not_defined():
    """
    qdevice is not set up in a cluster, when it was expected to be
    """
    return ReportItem.error(
        report_codes.QDEVICE_NOT_DEFINED,
    )

def qdevice_remove_or_cluster_stop_needed():
    """
    operation cannot be executed, qdevice removal or cluster stop is needed
    """
    return ReportItem.error(
        report_codes.QDEVICE_REMOVE_OR_CLUSTER_STOP_NEEDED,
    )

def qdevice_client_reload_started():
    """
    qdevice client configuration is about to be reloaded on nodes
    """
    return ReportItem.info(
        report_codes.QDEVICE_CLIENT_RELOAD_STARTED,
    )

def qdevice_already_initialized(model):
    """
    cannot create qdevice on local host, it has been already created
    string model qdevice model
    """
    return ReportItem.error(
        report_codes.QDEVICE_ALREADY_INITIALIZED,
        info={
            "model": model,
        }
    )

def qdevice_not_initialized(model):
    """
    cannot work with qdevice on local host, it has not been created yet
    string model qdevice model
    """
    return ReportItem.error(
        report_codes.QDEVICE_NOT_INITIALIZED,
        info={
            "model": model,
        }
    )

def qdevice_initialization_success(model):
    """
    qdevice was successfully initialized on local host
    string model qdevice model
    """
    return ReportItem.info(
        report_codes.QDEVICE_INITIALIZATION_SUCCESS,
        info={
            "model": model,
        }
    )

def qdevice_initialization_error(model, reason):
    """
    an error occured when creating qdevice on local host
    string model qdevice model
    string reason an error message
    """
    return ReportItem.error(
        report_codes.QDEVICE_INITIALIZATION_ERROR,
        info={
            "model": model,
            "reason": reason,
        }
    )

def qdevice_certificate_distribution_started():
    """
    Qdevice certificates are about to be set up on nodes
    """
    return ReportItem.info(
        report_codes.QDEVICE_CERTIFICATE_DISTRIBUTION_STARTED,
    )

def qdevice_certificate_accepted_by_node(node):
    """
    Qdevice certificates have been saved to a node
    string node node on which certificates have been saved
    """
    return ReportItem.info(
        report_codes.QDEVICE_CERTIFICATE_ACCEPTED_BY_NODE,
        info={"node": node}
    )

def qdevice_certificate_removal_started():
    """
    Qdevice certificates are about to be removed from nodes
    """
    return ReportItem.info(
        report_codes.QDEVICE_CERTIFICATE_REMOVAL_STARTED,
    )

def qdevice_certificate_removed_from_node(node):
    """
    Qdevice certificates have been removed from a node
    string node node on which certificates have been deleted
    """
    return ReportItem.info(
        report_codes.QDEVICE_CERTIFICATE_REMOVED_FROM_NODE,
        info={"node": node}
    )

def qdevice_certificate_import_error(reason):
    """
    an error occured when importing qdevice certificate to a node
    string reason an error message
    """
    return ReportItem.error(
        report_codes.QDEVICE_CERTIFICATE_IMPORT_ERROR,
        info={
            "reason": reason,
        }
    )

def qdevice_certificate_sign_error(reason):
    """
    an error occured when signing qdevice certificate
    string reason an error message
    """
    return ReportItem.error(
        report_codes.QDEVICE_CERTIFICATE_SIGN_ERROR,
        info={
            "reason": reason,
        }
    )

def qdevice_destroy_success(model):
    """
    qdevice configuration successfully removed from local host
    string model qdevice model
    """
    return ReportItem.info(
        report_codes.QDEVICE_DESTROY_SUCCESS,
        info={
            "model": model,
        }
    )

def qdevice_destroy_error(model, reason):
    """
    an error occured when removing qdevice configuration from local host
    string model qdevice model
    string reason an error message
    """
    return ReportItem.error(
        report_codes.QDEVICE_DESTROY_ERROR,
        info={
            "model": model,
            "reason": reason,
        }
    )

def qdevice_not_running(model):
    """
    qdevice is expected to be running but is not running
    string model qdevice model
    """
    return ReportItem.error(
        report_codes.QDEVICE_NOT_RUNNING,
        info={
            "model": model,
        }
    )

def qdevice_get_status_error(model, reason):
    """
    unable to get runtime status of qdevice
    string model qdevice model
    string reason an error message
    """
    return ReportItem.error(
        report_codes.QDEVICE_GET_STATUS_ERROR,
        info={
            "model": model,
            "reason": reason,
        }
    )

def qdevice_used_by_clusters(
    clusters, severity=ReportItemSeverity.ERROR, forceable=None
):
    """
    Qdevice is currently being used by clusters, cannot stop it unless forced
    """
    return ReportItem(
        report_codes.QDEVICE_USED_BY_CLUSTERS,
        severity,
        info={
            "clusters": clusters,
        },
        forceable=forceable
    )

def cman_unsupported_command():
    """
    requested library command is not available as local cluster is CMAN based
    """
    return ReportItem.error(
        report_codes.CMAN_UNSUPPORTED_COMMAND,
    )

def id_already_exists(id):
    """
    specified id already exists in CIB and cannot be used for a new CIB object
    id string existing id
    """
    return ReportItem.error(
        report_codes.ID_ALREADY_EXISTS,
        info={"id": id}
    )

def id_belongs_to_unexpected_type(id, expected_types, current_type):
    """
    Specified id exists but for another element than expected.
    For example user wants to create resource in group that is specifies by id.
    But id does not belong to group.
    """
    return ReportItem.error(
        report_codes.ID_BELONGS_TO_UNEXPECTED_TYPE,
        info={
            "id": id,
            "expected_types": expected_types,
            "current_type": current_type,
        }
    )

def object_with_id_in_unexpected_context(
    object_type, object_id, expected_context_type, expected_context_id
):
    """
    Object specified by object_type (tag) and object_id exists but not inside
    given context (expected_context_type, expected_context_id).
    """
    return ReportItem.error(
        report_codes.OBJECT_WITH_ID_IN_UNEXPECTED_CONTEXT,
        info={
            "type": object_type,
            "id": object_id,
            "expected_context_type": expected_context_type,
            "expected_context_id": expected_context_id,
        }
    )


def id_not_found(id, expected_types, context_type="", context_id=""):
    """
    specified id does not exist in CIB, user referenced a nonexisting id

    string id -- specified id
    list expected_types -- list of id's roles - expected types with the id
    string context_type -- context_id's role / type
    string context_id -- specifies the search area
    """
    return ReportItem.error(
        report_codes.ID_NOT_FOUND,
        info={
            "id": id,
            "expected_types": sorted(expected_types),
            "context_type": context_type,
            "context_id": context_id,
        }
    )

def resource_bundle_already_contains_a_resource(bundle_id, resource_id):
    """
    The bundle already contains a resource, another one caanot be added

    string bundle_id -- id of the bundle
    string resource_id -- id of the resource already contained in the bundle
    """
    return ReportItem.error(
        report_codes.RESOURCE_BUNDLE_ALREADY_CONTAINS_A_RESOURCE,
        info={
            "bundle_id": bundle_id,
            "resource_id": resource_id,
        }
    )

def cannot_group_resource_next_to_itself(resource_id, group_id):
    """
    Cannot put resource(id=resource_id) into group(id=group_id) next to itself:
        resource(id=resource_id).
    """
    return ReportItem.error(
        report_codes.CANNOT_GROUP_RESOURCE_NEXT_TO_ITSELF,
        info={
            "resource_id": resource_id,
            "group_id": group_id,
        }
    )

def stonith_resources_do_not_exist(
    stonith_ids, severity=ReportItemSeverity.ERROR, forceable=None
):
    """
    specified stonith resource doesn't exist (e.g. when creating in constraints)
    iterable stoniths -- list of specified stonith id
    """
    return ReportItem(
        report_codes.STONITH_RESOURCES_DO_NOT_EXIST,
        severity,
        info={
            "stonith_ids": stonith_ids,
        },
        forceable=forceable
    )

def resource_running_on_nodes(
    resource_id, roles_with_nodes, severity=ReportItemSeverity.INFO
):
    """
    Resource is running on some nodes. Taken from cluster state.

    string resource_id represent the resource
    list of tuple roles_with_nodes contain pairs (role, node)
    """
    return ReportItem(
        report_codes.RESOURCE_RUNNING_ON_NODES,
        severity,
        info={
            "resource_id": resource_id,
            "roles_with_nodes": roles_with_nodes,
        }
    )

def resource_does_not_run(resource_id, severity=ReportItemSeverity.INFO):
    """
    Resource is not running on any node. Taken from cluster state.

    string resource_id represent the resource
    """
    return ReportItem(
        report_codes.RESOURCE_DOES_NOT_RUN,
        severity,
        info={
            "resource_id": resource_id,
        }
    )

def resource_is_guest_node_already(resource_id):
    """
    The resource is already used as guest node (i.e. has meta attribute
    remote-node).

    string resource_id -- id of the resource that is guest node
    """
    return ReportItem.error(
        report_codes.RESOURCE_IS_GUEST_NODE_ALREADY,
        info={
            "resource_id": resource_id,
        }
    )

def resource_is_unmanaged(resource_id):
    """
    The resource the user works with is unmanaged (e.g. in enable/disable)

    string resource_id -- id of the unmanaged resource
    """
    return ReportItem.warning(
        report_codes.RESOURCE_IS_UNMANAGED,
        info={
            "resource_id": resource_id,
        }
    )

def resource_managed_no_monitor_enabled(resource_id):
    """
    The resource which was set to managed mode has no monitor operations enabled

    string resource_id -- id of the resource
    """
    return ReportItem.warning(
        report_codes.RESOURCE_MANAGED_NO_MONITOR_ENABLED,
        info={
            "resource_id": resource_id,
        }
    )

def cib_load_error(reason):
    """
    cannot load cib from cibadmin, cibadmin exited with non-zero code
    string reason error description
    """
    return ReportItem.error(
        report_codes.CIB_LOAD_ERROR,
        info={
            "reason": reason,
        }
    )

def cib_load_error_scope_missing(scope, reason):
    """
    cannot load cib from cibadmin, specified scope is missing in the cib
    scope string requested cib scope
    string reason error description
    """
    return ReportItem.error(
        report_codes.CIB_LOAD_ERROR_SCOPE_MISSING,
        info={
            "scope": scope,
            "reason": reason,
        }
    )

def cib_load_error_invalid_format(reason):
    """
    cib does not conform to the schema
    """
    return ReportItem.error(
        report_codes.CIB_LOAD_ERROR_BAD_FORMAT,
        info={
            "reason": reason,
        }
    )

def cib_missing_mandatory_section(section_name):
    """
    CIB is missing a section which is required to be present
    section_name string name of the missing section (element name or path)
    """
    return ReportItem.error(
        report_codes.CIB_CANNOT_FIND_MANDATORY_SECTION,
        info={
            "section": section_name,
        }
    )

def cib_push_error(reason, pushed_cib):
    """
    cannot push cib to cibadmin, cibadmin exited with non-zero code
    string reason error description
    string pushed_cib cib which failed to be pushed
    """
    return ReportItem.error(
        report_codes.CIB_PUSH_ERROR,
        info={
            "reason": reason,
            "pushed_cib": pushed_cib,
        }
    )

def cib_save_tmp_error(reason):
    """
    cannot save CIB into a temporary file
    string reason error description
    """
    return ReportItem.error(
        report_codes.CIB_SAVE_TMP_ERROR,
        info={
            "reason": reason,
        }
    )

def cib_diff_error(reason, cib_old, cib_new):
    """
    cannot obtain a diff of CIBs
    string reason -- error description
    string cib_old -- the CIB to be diffed against
    string cib_new -- the CIB diffed against the old cib
    """
    return ReportItem.error(
        report_codes.CIB_DIFF_ERROR,
        info={
            "reason": reason,
            "cib_old": cib_old,
            "cib_new": cib_new,
        }
    )

def cib_push_forced_full_due_to_crm_feature_set(required_set, current_set):
    """
    Pcs uses the "push full CIB" approach so race conditions may occur.

    pcs.common.tools.Version required_set -- crm_feature_set required for diff
    pcs.common.tools.Version current_set -- actual CIB crm_feature_set
    """
    return ReportItem.warning(
        report_codes.CIB_PUSH_FORCED_FULL_DUE_TO_CRM_FEATURE_SET,
        info={
            "required_set": str(required_set),
            "current_set": str(current_set),
        }
    )

def cluster_state_cannot_load(reason):
    """
    cannot load cluster status from crm_mon, crm_mon exited with non-zero code
    string reason error description
    """
    return ReportItem.error(
        report_codes.CRM_MON_ERROR,
        info={
            "reason": reason,
        }
    )

def cluster_state_invalid_format():
    """
    crm_mon xml output does not conform to the schema
    """
    return ReportItem.error(
        report_codes.BAD_CLUSTER_STATE_FORMAT,
    )

def wait_for_idle_not_supported():
    """
    crm_resource does not support --wait
    """
    return ReportItem.error(
        report_codes.WAIT_FOR_IDLE_NOT_SUPPORTED,
    )

def wait_for_idle_timed_out(reason):
    """
    waiting for resources (crm_resource --wait) failed, timeout expired
    string reason error description
    """
    return ReportItem.error(
        report_codes.WAIT_FOR_IDLE_TIMED_OUT,
        info={
            "reason": reason,
        }
    )

def wait_for_idle_error(reason):
    """
    waiting for resources (crm_resource --wait) failed
    string reason error description
    """
    return ReportItem.error(
        report_codes.WAIT_FOR_IDLE_ERROR,
        info={
            "reason": reason,
        }
    )

def wait_for_idle_not_live_cluster():
    """
    cannot wait for the cluster if not running with a live cluster
    """
    return ReportItem.error(
        report_codes.WAIT_FOR_IDLE_NOT_LIVE_CLUSTER,
    )

def resource_cleanup_error(reason, resource=None, node=None):
    """
    An error occured when deleting resource failed operations in pacemaker

    string reason -- error description
    string resource -- resource which has been cleaned up
    string node -- node which has been cleaned up
    """
    return ReportItem.error(
        report_codes.RESOURCE_CLEANUP_ERROR,
        info={
            "reason": reason,
            "resource": resource,
            "node": node,
        }
    )

def resource_refresh_error(reason, resource=None, node=None):
    """
    An error occured when deleting resource history in pacemaker

    string reason -- error description
    string resource -- resource which has been cleaned up
    string node -- node which has been cleaned up
    """
    return ReportItem.error(
        report_codes.RESOURCE_REFRESH_ERROR,
        info={
            "reason": reason,
            "resource": resource,
            "node": node,
        }
    )

def resource_refresh_too_time_consuming(threshold):
    """
    Resource refresh would execute more than threshold operations in a cluster

    int threshold -- current threshold for trigerring this error
    """
    return ReportItem.error(
        report_codes.RESOURCE_REFRESH_TOO_TIME_CONSUMING,
        info={"threshold": threshold},
        forceable=report_codes.FORCE_LOAD_THRESHOLD
    )

def resource_operation_interval_duplication(duplications):
    """
    More operations with same name and same interval apeared.
    Each operation with the same name (e.g. monitoring) need to have unique
    interval.
    dict duplications see resource operation interval duplication
        in pcs/lib/exchange_formats.md
    """
    return ReportItem.error(
        report_codes.RESOURCE_OPERATION_INTERVAL_DUPLICATION,
        info={
            "duplications": duplications,
        }
    )

def resource_operation_interval_adapted(
    operation_name, original_interval, adapted_interval
):
    """
    Interval of resource operation was adopted to operation (with the same name)
        intervals were unique.
    Each operation with the same name (e.g. monitoring) need to have unique
    interval.

    """
    return ReportItem.warning(
        report_codes.RESOURCE_OPERATION_INTERVAL_ADAPTED,
        info={
            "operation_name": operation_name,
            "original_interval": original_interval,
            "adapted_interval": adapted_interval,
        }
    )

def node_not_found(
    node, searched_types=None, severity=ReportItemSeverity.ERROR, forceable=None
):
    """
    specified node does not exist
    node string specified node
    searched_types list|string
    """
    return ReportItem(
        report_codes.NODE_NOT_FOUND,
        severity,
        info={
            "node": node,
            "searched_types": searched_types if searched_types else []
        },
        forceable=forceable
    )

def node_to_clear_is_still_in_cluster(
    node, severity=ReportItemSeverity.ERROR, forceable=None
):
    """
    specified node is still in cluster and `crm_node --remove` should be not
    used

    node string specified node
    """
    return ReportItem(
        report_codes.NODE_TO_CLEAR_IS_STILL_IN_CLUSTER,
        severity,
        info={
            "node": node,
        },
        forceable=forceable
    )

def node_remove_in_pacemaker_failed(node_name, reason):
    """
    calling of crm_node --remove failed
    string reason is caught reason
    """
    return ReportItem.error(
        report_codes.NODE_REMOVE_IN_PACEMAKER_FAILED,
        info={
            "node_name": node_name,
            "reason": reason,
        }
    )

def multiple_result_found(
    result_type, result_identifier_list, search_description="",
    severity=ReportItemSeverity.ERROR, forceable=None
):
    """
    Multiple result was found when something was looked for. E.g. resource for
    remote node.

    string result_type specifies what was looked for, e.g. "resource"
    list result_identifier_list contains identifiers of results
        e.g. resource ids
    string search_description e.g. name of remote_node
    """
    return ReportItem(
        report_codes.MULTIPLE_RESULTS_FOUND,
        severity,
        info={
            "result_type": result_type,
            "result_identifier_list": result_identifier_list,
            "search_description": search_description,
        },
        forceable=forceable
    )


def pacemaker_local_node_name_not_found(reason):
    """
    we are unable to figure out pacemaker's local node's name
    reason string error message
    """
    return ReportItem.error(
        report_codes.PACEMAKER_LOCAL_NODE_NAME_NOT_FOUND,
        info={"reason": reason}
    )

def rrp_active_not_supported(warning=False):
    """
    active RRP mode is not supported, require user confirmation
    warning set to True if user confirmed he/she wants to proceed
    """
    return ReportItem(
        report_codes.RRP_ACTIVE_NOT_SUPPORTED,
        ReportItemSeverity.WARNING if warning else ReportItemSeverity.ERROR,
        forceable=(None if warning else report_codes.FORCE_ACTIVE_RRP)
    )

def cman_ignored_option(option):
    """
    specified option is ignored as CMAN clusters do not support it
    options string option name
    """
    return ReportItem.warning(
        report_codes.IGNORED_CMAN_UNSUPPORTED_OPTION,
        info={'option_name': option}
    )

def rrp_addresses_transport_mismatch():
    """
    RRP defined by network addresses is not allowed when udp transport is used
    """
    return ReportItem.error(
        report_codes.NON_UDP_TRANSPORT_ADDR_MISMATCH,
    )

def cman_udpu_restart_required():
    """
    warn user it is required to restart CMAN cluster for changes to take effect
    """
    return ReportItem.warning(
        report_codes.CMAN_UDPU_RESTART_REQUIRED,
    )

def cman_broadcast_all_rings():
    """
    broadcast enabled in all rings, CMAN doesn't support 1 ring only broadcast
    """
    return ReportItem.warning(
        report_codes.CMAN_BROADCAST_ALL_RINGS,
    )

def service_start_started(service, instance=None):
    """
    system service is being started
    string service service name or description
    string instance instance of service
    """
    return ReportItem.info(
        report_codes.SERVICE_START_STARTED,
        info={
            "service": service,
            "instance": instance,
        }
    )

def service_start_error(service, reason, node=None, instance=None):
    """
    system service start failed
    string service service name or description
    string reason error message
    string node node on which service has been requested to start
    string instance instance of service
    """
    return ReportItem.error(
        report_codes.SERVICE_START_ERROR,
        info={
            "service": service,
            "reason": reason,
            "node": node,
            "instance": instance,
        }
    )

def service_start_success(service, node=None, instance=None):
    """
    system service was started successfully
    string service service name or description
    string node node on which service has been requested to start
    string instance instance of service
    """
    return ReportItem.info(
        report_codes.SERVICE_START_SUCCESS,
        info={
            "service": service,
            "node": node,
            "instance": instance,
        }
    )

def service_start_skipped(service, reason, node=None, instance=None):
    """
    starting system service was skipped, no error occured
    string service service name or description
    string reason why the start has been skipped
    string node node on which service has been requested to start
    string instance instance of service
    """
    return ReportItem.info(
        report_codes.SERVICE_START_SKIPPED,
        info={
            "service": service,
            "reason": reason,
            "node": node,
            "instance": instance,
        }
    )

def service_stop_started(service, instance=None):
    """
    system service is being stopped
    string service service name or description
    string instance instance of service
    """
    return ReportItem.info(
        report_codes.SERVICE_STOP_STARTED,
        info={
            "service": service,
            "instance": instance,
        }
    )

def service_stop_error(service, reason, node=None, instance=None):
    """
    system service stop failed
    string service service name or description
    string reason error message
    string node node on which service has been requested to stop
    string instance instance of service
    """
    return ReportItem.error(
        report_codes.SERVICE_STOP_ERROR,
        info={
            "service": service,
            "reason": reason,
            "node": node,
            "instance": instance,
        }
    )

def service_stop_success(service, node=None, instance=None):
    """
    system service was stopped successfully
    string service service name or description
    string node node on which service has been requested to stop
    string instance instance of service
    """
    return ReportItem.info(
        report_codes.SERVICE_STOP_SUCCESS,
        info={
            "service": service,
            "node": node,
            "instance": instance,
        }
    )

def service_kill_error(services, reason):
    """
    system services kill failed
    iterable services services name or description
    string reason error message
    """
    return ReportItem.error(
        report_codes.SERVICE_KILL_ERROR,
        info={
            "services": sorted(services),
            "reason": reason,
        }
    )

def service_kill_success(services):
    """
    system services were killed successfully
    iterable services services name or description
    """
    return ReportItem.info(
        report_codes.SERVICE_KILL_SUCCESS,
        info={
            "services": sorted(services),
        }
    )

def service_enable_started(service, instance=None):
    """
    system service is being enabled
    string service service name or description
    string instance instance of service
    """
    return ReportItem.info(
        report_codes.SERVICE_ENABLE_STARTED,
        info={
            "service": service,
            "instance": instance,
        }
    )

def service_enable_error(service, reason, node=None, instance=None):
    """
    system service enable failed
    string service service name or description
    string reason error message
    string node node on which service was enabled
    string instance instance of service
    """
    return ReportItem.error(
        report_codes.SERVICE_ENABLE_ERROR,
        info={
            "service": service,
            "reason": reason,
            "node": node,
            "instance": instance,
        }
    )

def service_enable_success(service, node=None, instance=None):
    """
    system service was enabled successfully
    string service service name or description
    string node node on which service has been enabled
    string instance instance of service
    """
    return ReportItem.info(
        report_codes.SERVICE_ENABLE_SUCCESS,
        info={
            "service": service,
            "node": node,
            "instance": instance,
        }
    )

def service_enable_skipped(service, reason, node=None, instance=None):
    """
    enabling system service was skipped, no error occured
    string service service name or description
    string reason why the enabling has been skipped
    string node node on which service has been requested to enable
    string instance instance of service
    """
    return ReportItem.info(
        report_codes.SERVICE_ENABLE_SKIPPED,
        info={
            "service": service,
            "reason": reason,
            "node": node,
            "instance": instance
        }
    )

def service_disable_started(service, instance=None):
    """
    system service is being disabled
    string service service name or description
    string instance instance of service
    """
    return ReportItem.info(
        report_codes.SERVICE_DISABLE_STARTED,
        info={
            "service": service,
            "instance": instance,
        }
    )

def service_disable_error(service, reason, node=None, instance=None):
    """
    system service disable failed
    string service service name or description
    string reason error message
    string node node on which service was disabled
    string instance instance of service
    """
    return ReportItem.error(
        report_codes.SERVICE_DISABLE_ERROR,
        info={
            "service": service,
            "reason": reason,
            "node": node,
            "instance": instance,
        }
    )

def service_disable_success(service, node=None, instance=None):
    """
    system service was disabled successfully
    string service service name or description
    string node node on which service was disabled
    string instance instance of service
    """
    return ReportItem.info(
        report_codes.SERVICE_DISABLE_SUCCESS,
        info={
            "service": service,
            "node": node,
            "instance": instance,
        }
    )


def unable_to_get_agent_metadata(
    agent, reason, severity=ReportItemSeverity.ERROR, forceable=None
):
    """
    There were some issues trying to get metadata of agent

    string agent agent which metadata were unable to obtain
    string reason reason of failure
    """
    return ReportItem(
        report_codes.UNABLE_TO_GET_AGENT_METADATA,
        severity,
        info={
            "agent": agent,
            "reason": reason
        },
        forceable=forceable
    )

def invalid_resource_agent_name(name):
    """
    The entered resource agent name is not valid.
    This name has the internal structure. The code needs to work with parts of
    this structure and fails if parts can not be obtained.

    string name is entered name
    """
    return ReportItem.error(
        report_codes.INVALID_RESOURCE_AGENT_NAME,
        info={
            "name": name,
        }
    )

def invalid_stonith_agent_name(name):
    """
    The entered stonith agent name is not valid.
    string name -- entered stonith agent name
    """
    return ReportItem.error(
        report_codes.INVALID_STONITH_AGENT_NAME,
        info={
            "name": name,
        }
    )

def agent_name_guessed(entered_name, guessed_name):
    """
    Resource agent name was deduced from the entered name.
    Pcs supports the using of abbreviated resource agent name (e.g.
    ocf:heartbeat:Delay => Delay) when it can be clearly deduced.

    string entered_name is entered name
    string guessed_name is deduced name
    """
    return ReportItem.info(
        report_codes.AGENT_NAME_GUESSED,
        info={
            "entered_name": entered_name,
            "guessed_name": guessed_name,
        }
    )

def agent_name_guess_found_more_than_one(agent, possible_agents):
    """
    More than one agents found based on the search string, specify one of them
    string agent searched name of an agent
    iterable possible_agents full names of agents matching the search
    """
    return ReportItem.error(
        report_codes.AGENT_NAME_GUESS_FOUND_MORE_THAN_ONE,
        info={
            "agent": agent,
            "possible_agents": possible_agents,
            "possible_agents_str": ", ".join(sorted(possible_agents)),
        }
    )


def agent_name_guess_found_none(agent):
    """
    Specified agent doesn't exist
    string agent name of the agent which doesn't exist
    """
    return ReportItem.error(
        report_codes.AGENT_NAME_GUESS_FOUND_NONE,
        info={"agent": agent}
    )


def omitting_node(node):
    """
    warning that specified node will be omitted in following actions

    node -- node name
    """
    return ReportItem.warning(
        report_codes.OMITTING_NODE,
        info={"node": node}
    )


def sbd_check_started():
    """
    info that SBD pre-enabling checks started
    """
    return ReportItem.info(
        report_codes.SBD_CHECK_STARTED,
    )


def sbd_check_success(node):
    """
    info that SBD pre-enabling check finished without issues on specified node

    node -- node name
    """
    return ReportItem.info(
        report_codes.SBD_CHECK_SUCCESS,
        info={"node": node}
    )


def sbd_config_distribution_started():
    """
    distribution of SBD configuration started
    """
    return ReportItem.info(
        report_codes.SBD_CONFIG_DISTRIBUTION_STARTED,
    )


def sbd_config_accepted_by_node(node):
    """
    info that SBD configuration has been saved successfully on specified node

    node -- node name
    """
    return ReportItem.info(
        report_codes.SBD_CONFIG_ACCEPTED_BY_NODE,
        info={"node": node}
    )


def unable_to_get_sbd_config(node, reason, severity=ReportItemSeverity.ERROR):
    """
    unable to get SBD config from specified node (communication or parsing
    error)

    node -- node name
    reason -- reason of failure
    """
    return ReportItem(
        report_codes.UNABLE_TO_GET_SBD_CONFIG,
        severity,
        info={
            "node": node,
            "reason": reason
        }
    )


def sbd_enabling_started():
    """
    enabling SBD service started
    """
    return ReportItem.info(
        report_codes.SBD_ENABLING_STARTED,
    )


def sbd_disabling_started():
    """
    disabling SBD service started
    """
    return ReportItem.info(
        report_codes.SBD_DISABLING_STARTED,
    )


def sbd_device_initialization_started(device_list):
    """
    initialization of SBD device(s) started
    """
    return ReportItem.info(
        report_codes.SBD_DEVICE_INITIALIZATION_STARTED,
        info={
            "device_list": device_list,
        }
    )


def sbd_device_initialization_success(device_list):
    """
    initialization of SBD device(s) successed
    """
    return ReportItem.info(
        report_codes.SBD_DEVICE_INITIALIZATION_SUCCESS,
        info={
            "device_list": device_list,
        }
    )


def sbd_device_initialization_error(device_list, reason):
    """
    initialization of SBD device failed
    """
    return ReportItem.error(
        report_codes.SBD_DEVICE_INITIALIZATION_ERROR,
        info={
            "device_list": device_list,
            "reason": reason,
        }
    )


def sbd_device_list_error(device, reason):
    """
    command 'sbd list' failed
    """
    return ReportItem.error(
        report_codes.SBD_DEVICE_LIST_ERROR,
        info={
            "device": device,
            "reason": reason,
        }
    )


def sbd_device_message_error(device, node, message, reason):
    """
    unable to set message 'message' on shared block device 'device'
    for node 'node'.
    """
    return ReportItem.error(
        report_codes.SBD_DEVICE_MESSAGE_ERROR,
        info={
            "device": device,
            "node": node,
            "message": message,
            "reason": reason,
        }
    )


def sbd_device_dump_error(device, reason):
    """
    command 'sbd dump' failed
    """
    return ReportItem.error(
        report_codes.SBD_DEVICE_DUMP_ERROR,
        info={
            "device": device,
            "reason": reason,
        }
    )

def files_distribution_started(file_list, node_list=None, description=None):
    """
    files is about to be sent to nodes
    """
    file_list = file_list if file_list else []
    return ReportItem.info(
        report_codes.FILES_DISTRIBUTION_STARTED,
        info={
            "file_list": file_list,
            "node_list": node_list,
            "description": description,
        }
    )

def file_distribution_success(node=None, file_description=None):
    """
    files was successfuly distributed on nodes

    string node -- name of destination node
    string file_description -- name (code) of sucessfully put files
    """
    return ReportItem.info(
        report_codes.FILE_DISTRIBUTION_SUCCESS,
        info={
            "node": node,
            "file_description": file_description,
        },
    )

def file_distribution_error(
    node=None, file_description=None, reason=None,
    severity=ReportItemSeverity.ERROR, forceable=None
):
    """
    cannot put files to specific nodes

    string node -- name of destination node
    string file_description -- is file code
    string reason -- is error message
    """
    return ReportItem(
        report_codes.FILE_DISTRIBUTION_ERROR,
        severity,
        info={
            "node": node,
            "file_description": file_description,
            "reason": reason,
        },
        forceable=forceable
    )

def files_remove_from_node_started(file_list, node_list=None, description=None):
    """
    files is about to be removed from nodes
    """
    file_list = file_list if file_list else []
    return ReportItem.info(
        report_codes.FILES_REMOVE_FROM_NODE_STARTED,
        info={
            "file_list": file_list,
            "node_list": node_list,
            "description": description,
        }
    )

def file_remove_from_node_success(node=None, file_description=None):
    """
    files was successfuly removed nodes

    string node -- name of destination node
    string file_description -- name (code) of sucessfully put files
    """
    return ReportItem.info(
        report_codes.FILE_REMOVE_FROM_NODE_SUCCESS,
        info={
            "node": node,
            "file_description": file_description,
        },
    )

def file_remove_from_node_error(
    node=None, file_description=None, reason=None,
    severity=ReportItemSeverity.ERROR, forceable=None
):
    """
    cannot remove files from specific nodes

    string node -- name of destination node
    string file_description -- is file code
    string reason -- is error message
    """
    return ReportItem(
        report_codes.FILE_REMOVE_FROM_NODE_ERROR,
        severity,
        info={
            "node": node,
            "file_description": file_description,
            "reason": reason,
        },
        forceable=forceable
    )

def service_commands_on_nodes_started(
    action_list, node_list=None, description=None
):
    """
    node was requested for actions
    """
    action_list = action_list if action_list else []
    return ReportItem.info(
        report_codes.SERVICE_COMMANDS_ON_NODES_STARTED,
        info={
            "action_list": action_list,
            "node_list": node_list,
            "description": description,
        }
    )

def service_command_on_node_success(
    node=None, service_command_description=None
):
    """
    files was successfuly distributed on nodes

    string service_command_description -- name (code) of sucessfully service
        command
    """
    return ReportItem.info(
        report_codes.SERVICE_COMMAND_ON_NODE_SUCCESS,
        info={
            "node": node,
            "service_command_description": service_command_description,
        },
    )

def service_command_on_node_error(
    node=None, service_command_description=None, reason=None,
    severity=ReportItemSeverity.ERROR, forceable=None
):
    """
    action on nodes failed

    string service_command_description -- name (code) of sucessfully service
        command
    string reason -- is error message
    """
    return ReportItem(
        report_codes.SERVICE_COMMAND_ON_NODE_ERROR,
        severity,
        info={
            "node": node,
            "service_command_description": service_command_description,
            "reason": reason,
        },
        forceable=forceable
    )


def invalid_response_format(node):
    """
    error message that response in invalid format has been received from
    specified node

    node -- node name
    """
    return ReportItem.error(
        report_codes.INVALID_RESPONSE_FORMAT,
        info={"node": node}
    )


def sbd_no_device_for_node(node):
    """
    there is no device defined for node when enabling sbd with device
    """
    return ReportItem.error(
        report_codes.SBD_NO_DEVICE_FOR_NODE,
        info={"node": node}
    )


def sbd_too_many_devices_for_node(node, device_list, max_devices):
    """
    More than 3 devices defined for node
    """
    return ReportItem.error(
        report_codes.SBD_TOO_MANY_DEVICES_FOR_NODE,
        info={
            "node": node,
            "device_list": device_list,
            "max_devices": max_devices,
        }
    )


def sbd_device_path_not_absolute(device, node=None):
    """
    path of SBD device is not absolute
    """
    return ReportItem.error(
        report_codes.SBD_DEVICE_PATH_NOT_ABSOLUTE,
        info={
            "device": device,
            "node": node,
        }
    )


def sbd_device_does_not_exist(device, node):
    """
    specified device on node doesn't exist
    """
    return ReportItem.error(
        report_codes.SBD_DEVICE_DOES_NOT_EXIST,
        info={
            "device": device,
            "node": node,
        }
    )


def sbd_device_is_not_block_device(device, node):
    """
    specified device on node is not block device
    """
    return ReportItem.error(
        report_codes.SBD_DEVICE_IS_NOT_BLOCK_DEVICE,
        info={
            "device": device,
            "node": node,
        }
    )


def sbd_not_installed(node):
    """
    sbd is not installed on specified node

    node -- node name
    """
    return ReportItem.error(
        report_codes.SBD_NOT_INSTALLED,
        info={"node": node}
    )


def watchdog_not_found(node, watchdog):
    """
    watchdog doesn't exist on specified node

    node -- node name
    watchdog -- watchdog device path
    """
    return ReportItem.error(
        report_codes.WATCHDOG_NOT_FOUND,
        info={
            "node": node,
            "watchdog": watchdog
        },
        forceable=report_codes.SKIP_WATCHDOG_VALIDATION,
    )


def invalid_watchdog_path(watchdog):
    """
    watchdog path is not absolut path

    watchdog -- watchdog device path
    """
    return ReportItem.error(
        report_codes.WATCHDOG_INVALID,
        info={"watchdog": watchdog}
    )


def unable_to_get_sbd_status(node, reason):
    """
    there was (communication or parsing) failure during obtaining status of SBD
    from specified node

    node -- node name
    reason -- reason of failure
    """
    return ReportItem.warning(
        report_codes.UNABLE_TO_GET_SBD_STATUS,
        info={
            "node": node,
            "reason": reason
        }
    )

def cluster_restart_required_to_apply_changes():
    """
    warn user a cluster needs to be manually restarted to use new configuration
    """
    return ReportItem.warning(
        report_codes.CLUSTER_RESTART_REQUIRED_TO_APPLY_CHANGES,
    )


def cib_alert_recipient_already_exists(
    alert_id, recipient_value, severity=ReportItemSeverity.ERROR, forceable=None
):
    """
    Recipient with specified value already exists in alert with id 'alert_id'

    alert_id -- id of alert to which recipient belongs
    recipient_value -- value of recipient
    """
    return ReportItem(
        report_codes.CIB_ALERT_RECIPIENT_ALREADY_EXISTS,
        severity,
        info={
            "recipient": recipient_value,
            "alert": alert_id
        },
        forceable=forceable
    )


def cib_alert_recipient_invalid_value(recipient_value):
    """
    Invalid recipient value.

    recipient_value -- recipient value
    """
    return ReportItem.error(
        report_codes.CIB_ALERT_RECIPIENT_VALUE_INVALID,
        info={"recipient": recipient_value}
    )

def cib_upgrade_successful():
    """
    Upgrade of CIB schema was successful.
    """
    return ReportItem.info(
        report_codes.CIB_UPGRADE_SUCCESSFUL,
    )


def cib_upgrade_failed(reason):
    """
    Upgrade of CIB schema failed.

    reason -- reason of failure
    """
    return ReportItem.error(
        report_codes.CIB_UPGRADE_FAILED,
        info={"reason": reason}
    )


def unable_to_upgrade_cib_to_required_version(
    current_version, required_version
):
    """
    Unable to upgrade CIB to minimal required schema version.

    pcs.common.tools.Version current_version -- current version of CIB schema
    pcs.common.tools.Version required_version -- required version of CIB schema
    """
    return ReportItem.error(
        report_codes.CIB_UPGRADE_FAILED_TO_MINIMAL_REQUIRED_VERSION,
        info={
            "required_version": str(required_version),
            "current_version": str(current_version)
        }
    )

def file_already_exists(
        file_role, file_path, severity=ReportItemSeverity.ERROR,
        forceable=None, node=None
    ):
    return ReportItem(
        report_codes.FILE_ALREADY_EXISTS,
        severity,
        info={
            "file_role": file_role,
            "file_path": file_path,
            "node": node,
        },
        forceable=forceable,
    )

def file_does_not_exist(file_role, file_path=""):
    return ReportItem.error(
        report_codes.FILE_DOES_NOT_EXIST,
        info={
            "file_role": file_role,
            "file_path": file_path,
        },
    )

def file_io_error(
    file_role, file_path="", reason="", operation="work with",
    severity=ReportItemSeverity.ERROR
):
    return ReportItem(
        report_codes.FILE_IO_ERROR,
        severity,
        info={
            "file_role": file_role,
            "file_path": file_path,
            "reason": reason,
            "operation": operation
        },
    )

def unable_to_determine_user_uid(user):
    return ReportItem.error(
        report_codes.UNABLE_TO_DETERMINE_USER_UID,
        info={
            "user": user
        }
    )

def unable_to_determine_group_gid(group):
    return ReportItem.error(
        report_codes.UNABLE_TO_DETERMINE_GROUP_GID,
        info={
            "group": group
        }
    )

def unsupported_operation_on_non_systemd_systems():
    return ReportItem.error(
        report_codes.UNSUPPORTED_OPERATION_ON_NON_SYSTEMD_SYSTEMS,
    )

def live_environment_required(forbidden_options):
    return ReportItem.error(
        report_codes.LIVE_ENVIRONMENT_REQUIRED,
        info={
            "forbidden_options": forbidden_options,
        }
    )

def live_environment_required_for_local_node():
    """
    The operation cannot be performed on CIB in file (not live cluster) if no
        node name is specified i.e. working with the local node
    """
    return ReportItem.error(
        report_codes.LIVE_ENVIRONMENT_REQUIRED_FOR_LOCAL_NODE,
    )

def nolive_skip_files_distribution(files_description, nodes):
    """
    When running action with e.g. -f the files was not distributed to nodes.
    list files_description -- contains description of files
    list nodes -- destinations where should be files distributed
    """
    return ReportItem.info(
        report_codes.NOLIVE_SKIP_FILES_DISTRIBUTION,
        info={
            "files_description": files_description,
            "nodes": nodes,
        }
    )

def nolive_skip_files_remove(files_description, nodes):
    """
    When running action with e.g. -f the files was not removed from nodes.
    list files_description -- contains description of files
    list nodes -- destinations from where should be files removed
    """
    return ReportItem.info(
        report_codes.NOLIVE_SKIP_FILES_REMOVE,
        info={
            "files_description": files_description,
            "nodes": nodes,
        }
    )

def nolive_skip_service_command_on_nodes(service, command, nodes):
    """
    When running action with e.g. -f the service command is not run on nodes.
    string service -- e.g. pacemaker, pacemaker_remote, corosync
    string command -- e.g. start, enable, stop, disable
    list nodes -- destinations where should be commad run
    """
    return ReportItem.info(
        report_codes.NOLIVE_SKIP_SERVICE_COMMAND_ON_NODES,
        info={
            "service": service,
            "command": command,
            "nodes": nodes,
        }
    )

def quorum_cannot_disable_atb_due_to_sbd(
    severity=ReportItemSeverity.ERROR, forceable=None
):
    """
    Quorum option auto_tie_breaker cannot be disbled due to SBD.
    """
    return ReportItem(
        report_codes.COROSYNC_QUORUM_CANNOT_DISABLE_ATB_DUE_TO_SBD,
        severity,
        forceable=forceable
    )


def sbd_requires_atb():
    """
    Warning that ATB will be enabled in order to make SBD fencing effective.
    """
    return ReportItem.warning(
        report_codes.SBD_REQUIRES_ATB,
    )


def acl_role_is_already_assigned_to_target(role_id, target_id):
    """
    Error that ACL target or group has already assigned role.
    """
    return ReportItem.error(
        report_codes.CIB_ACL_ROLE_IS_ALREADY_ASSIGNED_TO_TARGET,
        info={
            "role_id": role_id,
            "target_id": target_id,
        }
    )


def acl_role_is_not_assigned_to_target(role_id, target_id):
    """
    Error that acl role is not assigned to target or group
    """
    return ReportItem.error(
        report_codes.CIB_ACL_ROLE_IS_NOT_ASSIGNED_TO_TARGET,
        info={
            "role_id": role_id,
            "target_id": target_id,
        }
    )


def acl_target_already_exists(target_id):
    """
    Error that target with specified id aleready axists in configuration.
    """
    return ReportItem.error(
        report_codes.CIB_ACL_TARGET_ALREADY_EXISTS,
        info={
            "target_id": target_id,
        }
    )


def cluster_conf_invalid_format(reason):
    """
    cluster.conf parsing error
    """
    return ReportItem.error(
        report_codes.CLUSTER_CONF_LOAD_ERROR_INVALID_FORMAT,
        info={
            "reason": reason,
        }
    )


def cluster_conf_read_error(path, reason):
    """
    Unable to read cluster.conf
    """
    return ReportItem.error(
        report_codes.CLUSTER_CONF_READ_ERROR,
        info={
            "path": path,
            "reason": reason,
        }
    )

def fencing_level_already_exists(level, target_type, target_value, devices):
    """
    Fencing level already exists, it cannot be created
    """
    return ReportItem.error(
        report_codes.CIB_FENCING_LEVEL_ALREADY_EXISTS,
        info={
            "level": level,
            "target_type": target_type,
            "target_value": target_value,
            "devices": devices,
        }
    )

def fencing_level_does_not_exist(level, target_type, target_value, devices):
    """
    Fencing level does not exist, it cannot be updated or deleted
    """
    return ReportItem.error(
        report_codes.CIB_FENCING_LEVEL_DOES_NOT_EXIST,
        info={
            "level": level,
            "target_type": target_type,
            "target_value": target_value,
            "devices": devices,
        }
    )

def use_command_node_add_remote(
    severity=ReportItemSeverity.ERROR, forceable=None
):
    """
    Advise the user for more appropriate command.
    """
    return ReportItem(
        report_codes.USE_COMMAND_NODE_ADD_REMOTE,
        severity,
        info={},
        forceable=forceable
    )

def use_command_node_add_guest(
    severity=ReportItemSeverity.ERROR, forceable=None
):
    """
    Advise the user for more appropriate command.
    """
    return ReportItem(
        report_codes.USE_COMMAND_NODE_ADD_GUEST,
        severity,
        info={},
        forceable=forceable
    )

def use_command_node_remove_guest(
    severity=ReportItemSeverity.ERROR, forceable=None
):
    """
    Advise the user for more appropriate command.
    """
    return ReportItem(
        report_codes.USE_COMMAND_NODE_REMOVE_GUEST,
        severity,
        info={},
        forceable=forceable
    )

def tmp_file_write(file_path, content):
    """
    It has been written into a temporary file
    string file_path -- the file path
    string content -- content which has been written
    """
    return ReportItem.debug(
        report_codes.TMP_FILE_WRITE,
        info={
            "file_path": file_path,
            "content": content,
        }
    )


def unable_to_perform_operation_on_any_node():
    """
    This report is raised whenever
    pcs.lib.communication.tools.OneByOneStrategyMixin strategy mixin is used
    for network communication and operation failed on all available hosts and
    because of this it is not possible to continue.
    """
    return ReportItem.error(
        report_codes.UNABLE_TO_PERFORM_OPERATION_ON_ANY_NODE,
    )


def sbd_list_watchdog_error(reason):
    """
    Unable to get list of available watchdogs from sbd. Sbd cmd reutrned non 0.

    string reason -- stderr of command
    """
    return ReportItem.error(
        report_codes.SBD_LIST_WATCHDOG_ERROR,
        info=dict(
            reason=reason,
        )
    )


def sbd_watchdog_not_supported(node, watchdog):
    """
    Specified watchdog is not supported in sbd (softdog?).

    string node -- node name
    string watchdog -- watchdog path
    """
    return ReportItem.error(
        report_codes.SBD_WATCHDOG_NOT_SUPPORTED,
        info=dict(
            node=node,
            watchdog=watchdog,
        ),
        forceable=report_codes.SKIP_WATCHDOG_VALIDATION,
    )


def sbd_watchdog_validation_inactive():
    """
    Warning message about not validating watchdog.
    """
    return ReportItem.warning(
        report_codes.SBD_WATCHDOG_VALIDATION_INACTIVE,
    )


def sbd_watchdog_test_error(reason):
    """
    Sbd test watchdog exited with an error.
    """
    return ReportItem.error(
        report_codes.SBD_WATCHDOG_TEST_ERROR,
        info=dict(
            reason=reason,
        )
    )


def sbd_watchdog_test_multiple_devices():
    """
    No watchdog device has been specified for test. Because of multiple
    available watchdogs, watchdog device to test has to be specified.
    """
    return ReportItem.error(
        report_codes.SBD_WATCHDOG_TEST_MULTUPLE_DEVICES,
    )


def sbd_watchdog_test_failed():
    """
    System has not been reset.
    """
    return ReportItem.error(
        report_codes.SBD_WATCHDOG_TEST_FAILED,
    )


def system_will_reset():
    return ReportItem.info(
        report_codes.SYSTEM_WILL_RESET,
    )


def resource_in_bundle_not_accessible(
    bundle_id, inner_resource_id,
    severity=ReportItemSeverity.ERROR, forceable=report_codes.FORCE_OPTIONS,
):
    return ReportItem(
        report_codes.RESOURCE_IN_BUNDLE_NOT_ACCESSIBLE,
        severity,
        info=dict(
            bundle_id=bundle_id,
            inner_resource_id=inner_resource_id,
        ),
        forceable=forceable,
    )

def resource_instance_attr_value_not_unique(
    instance_attr_name, instance_attr_value, agent_name, resource_id_list,
    severity=ReportItemSeverity.ERROR, forceable=None
):
    """
    Value of a resource instance attribute is not unique in the configuration
    when creating/updating a resource

    instance_attr_name string -- name of attr which should be unique
    instance_attr_value string -- value which is already used by some resources
    agent_name string -- resource agent name of resource
    resource_id_list list of string -- resource ids which already have the
        instance_attr_name set to instance_attr_value
    severity string -- report item severity
    forceable mixed
    """
    return ReportItem(
        report_codes.RESOURCE_INSTANCE_ATTR_VALUE_NOT_UNIQUE,
        severity,
        info=dict(
            instance_attr_name=instance_attr_name,
            instance_attr_value=instance_attr_value,
            agent_name=agent_name,
            resource_id_list=resource_id_list,
        ),
        forceable=forceable,
    )
