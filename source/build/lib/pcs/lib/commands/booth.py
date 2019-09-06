from __future__ import (
    absolute_import,
    division,
    print_function,
)

import base64
import os.path
from functools import partial

from pcs import settings
from pcs.common.tools import join_multilines
from pcs.lib import external, reports, tools
from pcs.lib.cib.resource import primitive, group
from pcs.lib.booth import (
    config_exchange,
    config_files,
    config_structure,
    reports as booth_reports,
    resource,
    status,
)
from pcs.lib.booth.config_parser import parse, build
from pcs.lib.booth.env import get_config_file_name
from pcs.lib.cib.tools import get_resources
from pcs.lib.communication.booth import (
    BoothGetConfig,
    BoothSendConfig,
)
from pcs.lib.communication.tools import run_and_raise
from pcs.lib.errors import LibraryError, ReportItemSeverity
from pcs.lib.resource_agent import find_valid_resource_agent_by_name


def config_setup(env, booth_configuration, overwrite_existing=False):
    """
    create boot configuration
    list site_list contains site adresses of multisite
    list arbitrator_list contains arbitrator adresses of multisite
    """

    config_content = config_exchange.from_exchange_format(booth_configuration)
    config_structure.validate_peers(
        *config_structure.take_peers(config_content)
    )

    env.booth.create_key(tools.generate_key(), overwrite_existing)
    config_content = config_structure.set_authfile(
        config_content,
        env.booth.key_path
    )
    env.booth.create_config(build(config_content), overwrite_existing)

def config_destroy(env, ignore_config_load_problems=False):
    env.booth.command_expect_live_env()
    env.command_expect_live_corosync_env()

    name = env.booth.name
    config_is_used = partial(booth_reports.booth_config_is_used, name)

    report_list = []

    if(env.is_node_in_cluster() and resource.find_for_config(
        get_resources(env.get_cib()),
        get_config_file_name(name),
    )):
        report_list.append(config_is_used("in cluster resource"))

    #Only systemd is currently supported. Initd does not supports multiple
    #instances (here specified by name)
    if external.is_systemctl():
        if external.is_service_running(env.cmd_runner(), "booth", name):
            report_list.append(config_is_used("(running in systemd)"))

        if external.is_service_enabled(env.cmd_runner(), "booth", name):
            report_list.append(config_is_used("(enabled in systemd)"))

    if report_list:
        raise LibraryError(*report_list)

    authfile_path = None
    try:
        authfile_path = config_structure.get_authfile(
            parse(env.booth.get_config_content())
        )
    except LibraryError:
        if not ignore_config_load_problems:
            raise LibraryError(booth_reports.booth_cannot_identify_keyfile())

        #if content not received, not valid,... still remove config needed
        env.report_processor.process(
            booth_reports.booth_cannot_identify_keyfile(
                severity=ReportItemSeverity.WARNING
            )
        )

    if(
        authfile_path
        and
        os.path.dirname(authfile_path) == settings.booth_config_dir
    ):
        env.booth.set_key_path(authfile_path)
        env.booth.remove_key()
    env.booth.remove_config()


def config_text(env, name, node_name=None):
    """
    get configuration in raw format
    string name -- name of booth instance whose config should be returned
    string node_name -- get the config from specified node or local host if None
    """
    if node_name is None:
        # TODO add name support
        return env.booth.get_config_content()

    com_cmd = BoothGetConfig(env.report_processor, name)
    com_cmd.set_targets([
        env.get_node_target_factory().get_target_from_hostname(node_name)
    ])
    remote_data = run_and_raise(env.get_node_communicator(), com_cmd)[0][1]
    try:
        return remote_data["config"]["data"]
    except KeyError:
        raise LibraryError(reports.invalid_response_format(node_name))


def config_ticket_add(env, ticket_name, options, allow_unknown_options):
    """
    add ticket to booth configuration
    dict options contains options for ticket
    bool allow_unknown_options decide if can be used options not listed in
        ticket options nor global options
    """
    booth_configuration = config_structure.add_ticket(
        env.report_processor,
        parse(env.booth.get_config_content()),
        ticket_name,
        options,
        allow_unknown_options,
    )
    env.booth.push_config(build(booth_configuration))

def config_ticket_remove(env, ticket_name):
    """
    remove ticket from booth configuration
    """
    booth_configuration = config_structure.remove_ticket(
        parse(env.booth.get_config_content()),
        ticket_name
    )
    env.booth.push_config(build(booth_configuration))

def create_in_cluster(env, name, ip, allow_absent_resource_agent=False):
    """
    Create group with ip resource and booth resource

    LibraryEnvironment env provides all for communication with externals
    string name identifies booth instance
    string ip determines float ip for the operation of the booth
    bool allow_absent_resource_agent is flag allowing create booth resource even
        if its agent is not installed
    """
    resources_section = get_resources(env.get_cib())

    booth_config_file_path = get_config_file_name(name)
    if resource.find_for_config(resources_section, booth_config_file_path):
        raise LibraryError(booth_reports.booth_already_in_cib(name))

    create_id = partial(
        resource.create_resource_id,
        resources_section,
        name
    )
    get_agent = partial(
        find_valid_resource_agent_by_name,
        env.report_processor,
        env.cmd_runner(),
        allowed_absent=allow_absent_resource_agent
    )
    create_primitive = partial(
        primitive.create,
        env.report_processor,
        resources_section,
    )
    into_booth_group = partial(
        group.place_resource,
        group.provide_group(resources_section, create_id("group")),
    )

    into_booth_group(create_primitive(
        create_id("ip"),
        get_agent("ocf:heartbeat:IPaddr2"),
        instance_attributes={"ip": ip},
    ))
    into_booth_group(create_primitive(
        create_id("service"),
        get_agent("ocf:pacemaker:booth-site"),
        instance_attributes={"config": booth_config_file_path},
    ))

    env.push_cib()

def remove_from_cluster(env, name, resource_remove, allow_remove_multiple):
    #TODO resource_remove is provisional hack until resources are not moved to
    #lib
    resource.get_remover(resource_remove)(
        _find_resource_elements_for_operation(env, name, allow_remove_multiple)
    )

def restart(env, name, resource_restart, allow_multiple):
    #TODO resource_restart is provisional hack until resources are not moved to
    #lib
    for booth_element in _find_resource_elements_for_operation(
        env, name, allow_multiple
    ):
        resource_restart([booth_element.attrib["id"]])

def ticket_operation(operation, env, name, ticket, site_ip):
    if not site_ip:
        site_ip_list = resource.find_bound_ip(
            get_resources(env.get_cib()),
            get_config_file_name(name)
        )
        if len(site_ip_list) != 1:
            raise LibraryError(
                booth_reports.booth_cannot_determine_local_site_ip()
            )
        site_ip = site_ip_list[0]

    stdout, stderr, return_code = env.cmd_runner().run([
        settings.booth_binary, operation,
        "-s", site_ip,
        ticket
    ])

    if return_code != 0:
        raise LibraryError(
            booth_reports.booth_ticket_operation_failed(
                operation,
                join_multilines([stderr, stdout]),
                site_ip,
                ticket
            )
        )

ticket_grant = partial(ticket_operation, "grant")
ticket_revoke = partial(ticket_operation, "revoke")

def config_sync(env, name, skip_offline_nodes=False):
    """
    Send specified local booth configuration to all nodes in cluster.

    env -- LibraryEnvironment
    name -- booth instance name
    skip_offline_nodes -- if True offline nodes will be skipped
    """
    config = env.booth.get_config_content()
    authfile_path = config_structure.get_authfile(parse(config))
    authfile_content = config_files.read_authfile(
        env.report_processor, authfile_path
    )
    com_cmd = BoothSendConfig(
        env.report_processor,
        name,
        config,
        authfile=authfile_path,
        authfile_data=authfile_content,
        skip_offline_targets=skip_offline_nodes
    )
    com_cmd.set_targets(
        env.get_node_target_factory().get_target_list(
            env.get_corosync_conf().get_nodes()
        )
    )
    run_and_raise(env.get_node_communicator(), com_cmd)


def enable_booth(env, name=None):
    """
    Enable specified instance of booth service. Currently it is supported only
    systemd systems.

    env -- LibraryEnvironment
    name -- string, name of booth instance
    """
    external.ensure_is_systemd()
    try:
        external.enable_service(env.cmd_runner(), "booth", name)
    except external.EnableServiceError as e:
        raise LibraryError(reports.service_enable_error(
            "booth", e.message, instance=name
        ))
    env.report_processor.process(reports.service_enable_success(
        "booth", instance=name
    ))


def disable_booth(env, name=None):
    """
    Disable specified instance of booth service. Currently it is supported only
    systemd systems.

    env -- LibraryEnvironment
    name -- string, name of booth instance
    """
    external.ensure_is_systemd()
    try:
        external.disable_service(env.cmd_runner(), "booth", name)
    except external.DisableServiceError as e:
        raise LibraryError(reports.service_disable_error(
            "booth", e.message, instance=name
        ))
    env.report_processor.process(reports.service_disable_success(
        "booth", instance=name
    ))


def start_booth(env, name=None):
    """
    Start specified instance of booth service. Currently it is supported only
    systemd systems. On non systems it can be run like this:
        BOOTH_CONF_FILE=<booth-file-path> /etc/initd/booth-arbitrator

    env -- LibraryEnvironment
    name -- string, name of booth instance
    """
    external.ensure_is_systemd()
    try:
        external.start_service(env.cmd_runner(), "booth", name)
    except external.StartServiceError as e:
        raise LibraryError(reports.service_start_error(
            "booth", e.message, instance=name
        ))
    env.report_processor.process(reports.service_start_success(
        "booth", instance=name
    ))


def stop_booth(env, name=None):
    """
    Stop specified instance of booth service. Currently it is supported only
    systemd systems.

    env -- LibraryEnvironment
    name -- string, name of booth instance
    """
    external.ensure_is_systemd()
    try:
        external.stop_service(env.cmd_runner(), "booth", name)
    except external.StopServiceError as e:
        raise LibraryError(reports.service_stop_error(
            "booth", e.message, instance=name
        ))
    env.report_processor.process(reports.service_stop_success(
        "booth", instance=name
    ))


def pull_config(env, node_name, name):
    """
    Get config from specified node and save it on local system. It will
    rewrite existing files.

    env -- LibraryEnvironment
    node_name -- string, name of node from which config should be fetched
    name -- string, name of booth instance of which config should be fetched
    """
    env.report_processor.process(
        booth_reports.booth_fetching_config_from_node_started(node_name, name)
    )
    com_cmd = BoothGetConfig(env.report_processor, name)
    com_cmd.set_targets([
        env.get_node_target_factory().get_target_from_hostname(node_name)
    ])
    output = run_and_raise(env.get_node_communicator(), com_cmd)[0][1]
    try:
        env.booth.create_config(output["config"]["data"], True)
        if (
            output["authfile"]["name"] is not None and
            output["authfile"]["data"]
        ):
            env.booth.set_key_path(os.path.join(
                settings.booth_config_dir, output["authfile"]["name"]
            ))
            env.booth.create_key(
                base64.b64decode(
                    output["authfile"]["data"].encode("utf-8")
                ),
                True
            )
        env.report_processor.process(
            booth_reports.booth_config_accepted_by_node(name_list=[name])
        )
    except KeyError:
        raise LibraryError(reports.invalid_response_format(node_name))


def get_status(env, name=None):
    return {
        "status": status.get_daemon_status(env.cmd_runner(), name),
        "ticket": status.get_tickets_status(env.cmd_runner(), name),
        "peers": status.get_peers_status(env.cmd_runner(), name),
    }

def _find_resource_elements_for_operation(env, name, allow_multiple):
    booth_element_list = resource.find_for_config(
        get_resources(env.get_cib()),
        get_config_file_name(name),
    )

    if not booth_element_list:
        raise LibraryError(booth_reports.booth_not_exists_in_cib(name))

    if len(booth_element_list) > 1:
        if not allow_multiple:
            raise LibraryError(booth_reports.booth_multiple_times_in_cib(name))
        env.report_processor.process(
            booth_reports.booth_multiple_times_in_cib(
                name,
                severity=ReportItemSeverity.WARNING,
            )
        )

    return booth_element_list
