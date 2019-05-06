from __future__ import (
    absolute_import,
    division,
    print_function,
)

from contextlib import contextmanager

from pcs.lib import reports
from pcs.lib.cib.node import update_node_instance_attrs
from pcs.lib.errors import LibraryError
from pcs.lib.pacemaker.live import (
    get_cluster_status_xml,
    get_local_node_name,
)
from pcs.lib.pacemaker.state import ClusterState


@contextmanager
def cib_runner_nodes(lib_env, wait):
    lib_env.ensure_wait_satisfiable(wait)
    runner = lib_env.cmd_runner()

    state_nodes = ClusterState(
        get_cluster_status_xml(runner)
    ).node_section.nodes

    yield (lib_env.get_cib(), runner, state_nodes)
    lib_env.push_cib(wait=wait)


def standby_unstandby_local(lib_env, standby, wait=False):
    """
    Change local node standby mode

    LibraryEnvironment lib_env
    bool standby -- True: enable standby, False: disable standby
    mixed wait -- False: no wait, None: wait with default timeout, str or int:
        wait with specified timeout
    """
    return _set_instance_attrs_local_node(
        lib_env,
        _create_standby_unstandby_dict(standby),
        wait
    )

def standby_unstandby_list(lib_env, standby, node_names, wait=False):
    """
    Change specified nodes standby mode

    LibraryEnvironment lib_env
    bool standby -- True: enable standby, False: disable standby
    iterable node_names -- nodes to apply the change to
    mixed wait -- False: no wait, None: wait with default timeout, str or int:
        wait with specified timeout
    """
    return _set_instance_attrs_node_list(
        lib_env,
        _create_standby_unstandby_dict(standby),
        node_names,
        wait
    )

def standby_unstandby_all(lib_env, standby, wait=False):
    """
    Change all nodes standby mode

    LibraryEnvironment lib_env
    bool standby -- True: enable standby, False: disable standby
    mixed wait -- False: no wait, None: wait with default timeout, str or int:
        wait with specified timeout
    """
    return _set_instance_attrs_all_nodes(
        lib_env,
        _create_standby_unstandby_dict(standby),
        wait
    )

def maintenance_unmaintenance_local(lib_env, maintenance, wait=False):
    """
    Change local node maintenance mode

    LibraryEnvironment lib_env
    bool maintenance -- True: enable maintenance, False: disable maintenance
    mixed wait -- False: no wait, None: wait with default timeout, str or int:
        wait with specified timeout
    """
    return _set_instance_attrs_local_node(
        lib_env,
        _create_maintenance_unmaintenance_dict(maintenance),
        wait
    )

def maintenance_unmaintenance_list(
    lib_env, maintenance, node_names, wait=False
):
    """
    Change specified nodes maintenance mode

    LibraryEnvironment lib_env
    bool maintenance -- True: enable maintenance, False: disable maintenance
    iterable node_names -- nodes to apply the change to
    mixed wait -- False: no wait, None: wait with default timeout, str or int:
        wait with specified timeout
    """
    return _set_instance_attrs_node_list(
        lib_env,
        _create_maintenance_unmaintenance_dict(maintenance),
        node_names,
        wait
    )

def maintenance_unmaintenance_all(lib_env, maintenance, wait=False):
    """
    Change all nodes maintenance mode

    LibraryEnvironment lib_env
    bool maintenance -- True: enable maintenance, False: disable maintenance
    mixed wait -- False: no wait, None: wait with default timeout, str or int:
        wait with specified timeout
    """
    return _set_instance_attrs_all_nodes(
        lib_env,
        _create_maintenance_unmaintenance_dict(maintenance),
        wait
    )

def _create_standby_unstandby_dict(standby):
    return {"standby": "on" if standby else ""}

def _create_maintenance_unmaintenance_dict(maintenance):
    return {"maintenance": "on" if maintenance else ""}

def _set_instance_attrs_local_node(lib_env, attrs, wait):
    if not lib_env.is_cib_live:
        # If we are not working with a live cluster we cannot get the local node
        # name.
        raise LibraryError(reports.live_environment_required_for_local_node())

    with cib_runner_nodes(lib_env, wait) as (cib, runner, state_nodes):
        update_node_instance_attrs(
            cib,
            get_local_node_name(runner),
            attrs,
            state_nodes
        )

def _set_instance_attrs_node_list(lib_env, attrs, node_names, wait):
    with cib_runner_nodes(lib_env, wait) as (cib, dummy_runner, state_nodes):
        known_nodes = [node.attrs.name for node in state_nodes]
        report = []
        for node in node_names:
            if node not in known_nodes:
                report.append(reports.node_not_found(node))
        if report:
            raise LibraryError(*report)

        for node in node_names:
            update_node_instance_attrs(cib, node, attrs, state_nodes)

def _set_instance_attrs_all_nodes(lib_env, attrs, wait):
    with cib_runner_nodes(lib_env, wait) as (cib, dummy_runner, state_nodes):
        for node in [node.attrs.name for node in state_nodes]:
            update_node_instance_attrs(cib, node, attrs, state_nodes)
