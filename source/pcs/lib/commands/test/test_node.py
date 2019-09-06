from __future__ import (
    absolute_import,
    division,
    print_function,
)

from functools import partial
from contextlib import contextmanager

from lxml import etree
import logging

from pcs.test.tools.assertions import assert_raise_library_error
from pcs.test.tools.custom_mock import MockLibraryReportProcessor
from pcs.test.tools.pcs_unittest import mock, TestCase
from pcs.test.tools.misc import create_patcher

from pcs.common import report_codes
from pcs.lib.env import LibraryEnvironment
from pcs.lib.errors import ReportItemSeverity as severity, LibraryError

from pcs.lib.commands import node as lib


mocked_cib = etree.fromstring("<cib />")

patch_env = partial(mock.patch.object, LibraryEnvironment)
patch_command = create_patcher("pcs.lib.commands.node")

create_env = partial(
    LibraryEnvironment,
    mock.MagicMock(logging.Logger),
    MockLibraryReportProcessor()
)

def fixture_node(order_num):
    node = mock.MagicMock(attrs=mock.MagicMock())
    node.attrs.name = "node-{0}".format(order_num)
    return node

class StandbyMaintenancePassParameters(TestCase):
    def setUp(self):
        self.lib_env = "lib_env"
        self.nodes = "nodes"
        self.wait = "wait"
        self.standby_on = {"standby": "on"}
        self.standby_off = {"standby": ""}
        self.maintenance_on = {"maintenance": "on"}
        self.maintenance_off = {"maintenance": ""}

@patch_command("_set_instance_attrs_local_node")
class StandbyMaintenancePassParametersLocal(StandbyMaintenancePassParameters):
    def test_standby(self, mock_doer):
        lib.standby_unstandby_local(self.lib_env, True, self.wait)
        mock_doer.assert_called_once_with(
            self.lib_env,
            self.standby_on,
            self.wait
        )

    def test_unstandby(self, mock_doer):
        lib.standby_unstandby_local(self.lib_env, False, self.wait)
        mock_doer.assert_called_once_with(
            self.lib_env,
            self.standby_off,
            self.wait
        )

    def test_maintenance(self, mock_doer):
        lib.maintenance_unmaintenance_local(self.lib_env, True, self.wait)
        mock_doer.assert_called_once_with(
            self.lib_env,
            self.maintenance_on,
            self.wait
        )

    def test_unmaintenance(self, mock_doer):
        lib.maintenance_unmaintenance_local(self.lib_env, False, self.wait)
        mock_doer.assert_called_once_with(
            self.lib_env,
            self.maintenance_off,
            self.wait
        )

@patch_command("_set_instance_attrs_node_list")
class StandbyMaintenancePassParametersList(StandbyMaintenancePassParameters):
    def test_standby(self, mock_doer):
        lib.standby_unstandby_list(self.lib_env, True, self.nodes, self.wait)
        mock_doer.assert_called_once_with(
            self.lib_env,
            self.standby_on,
            self.nodes,
            self.wait
        )

    def test_unstandby(self, mock_doer):
        lib.standby_unstandby_list(self.lib_env, False, self.nodes, self.wait)
        mock_doer.assert_called_once_with(
            self.lib_env,
            self.standby_off,
            self.nodes,
            self.wait
        )

    def test_maintenance(self, mock_doer):
        lib.maintenance_unmaintenance_list(
            self.lib_env, True, self.nodes, self.wait
        )
        mock_doer.assert_called_once_with(
            self.lib_env,
            self.maintenance_on,
            self.nodes,
            self.wait
        )

    def test_unmaintenance(self, mock_doer):
        lib.maintenance_unmaintenance_list(
            self.lib_env, False, self.nodes, self.wait
        )
        mock_doer.assert_called_once_with(
            self.lib_env,
            self.maintenance_off,
            self.nodes,
            self.wait
        )

@patch_command("_set_instance_attrs_all_nodes")
class StandbyMaintenancePassParametersAll(StandbyMaintenancePassParameters):
    def test_standby(self, mock_doer):
        lib.standby_unstandby_all(self.lib_env, True, self.wait)
        mock_doer.assert_called_once_with(
            self.lib_env,
            self.standby_on,
            self.wait
        )

    def test_unstandby(self, mock_doer):
        lib.standby_unstandby_all(self.lib_env, False, self.wait)
        mock_doer.assert_called_once_with(
            self.lib_env,
            self.standby_off,
            self.wait
        )

    def test_maintenance(self, mock_doer):
        lib.maintenance_unmaintenance_all(self.lib_env, True, self.wait)
        mock_doer.assert_called_once_with(
            self.lib_env,
            self.maintenance_on,
            self.wait
        )

    def test_unmaintenance(self, mock_doer):
        lib.maintenance_unmaintenance_all(self.lib_env, False, self.wait)
        mock_doer.assert_called_once_with(
            self.lib_env,
            self.maintenance_off,
            self.wait
        )

class SetInstaceAttrsBase(TestCase):
    node_count = 2
    def setUp(self):
        self.cluster_nodes = [fixture_node(i) for i in range(self.node_count)]

        self.launch = {"pre": False, "post": False}
        @contextmanager
        def cib_runner_nodes_contextmanager(env, wait):
            self.launch["pre"] = True
            yield ("cib", "mock_runner", self.cluster_nodes)
            self.launch["post"] = True

        patcher = patch_command('cib_runner_nodes')
        self.addCleanup(patcher.stop)
        patcher.start().side_effect = cib_runner_nodes_contextmanager

    def assert_context_manager_launched(self, pre=False, post=False):
        self.assertEqual(self.launch, {"pre": pre, "post": post})

@patch_command("update_node_instance_attrs")
@patch_command("get_local_node_name")
class SetInstaceAttrsLocal(SetInstaceAttrsBase):
    node_count = 2

    def test_not_possible_with_cib_file(self, mock_name, mock_attrs):
        assert_raise_library_error(
            lambda: lib._set_instance_attrs_local_node(
                create_env(cib_data="<cib />"),
                "attrs",
                "wait"
            ),
            (
                severity.ERROR,
                report_codes.LIVE_ENVIRONMENT_REQUIRED_FOR_LOCAL_NODE,
                {}
            )
        )
        self.assert_context_manager_launched(pre=False, post=False)
        mock_name.assert_not_called()
        mock_attrs.assert_not_called()

    def test_success(self, mock_name, mock_attrs):
        mock_name.return_value = "node-1"

        lib._set_instance_attrs_local_node(create_env(), "attrs", False)

        self.assert_context_manager_launched(pre=True, post=True)
        mock_name.assert_called_once_with("mock_runner")
        mock_attrs.assert_called_once_with(
            "cib", "node-1", "attrs", self.cluster_nodes
        )

@patch_command("update_node_instance_attrs")
class SetInstaceAttrsAll(SetInstaceAttrsBase):
    node_count = 2

    def test_success(self, mock_attrs):
        lib._set_instance_attrs_all_nodes(create_env(), "attrs", False)

        self.assertEqual(2, len(mock_attrs.mock_calls))
        mock_attrs.assert_has_calls([
            mock.call("cib", "node-0", "attrs", self.cluster_nodes),
            mock.call("cib", "node-1", "attrs", self.cluster_nodes),
        ])

@patch_command("update_node_instance_attrs")
class SetInstaceAttrsList(SetInstaceAttrsBase):
    node_count = 4

    def test_success(self, mock_attrs):
        lib._set_instance_attrs_node_list(
            create_env(), "attrs", ["node-1", "node-2"], False
        )

        self.assert_context_manager_launched(pre=True, post=True)
        self.assertEqual(2, len(mock_attrs.mock_calls))
        mock_attrs.assert_has_calls([
            mock.call("cib", "node-1", "attrs", self.cluster_nodes),
            mock.call("cib", "node-2", "attrs", self.cluster_nodes),
        ])

    def test_bad_node(self, mock_attrs):
        assert_raise_library_error(
            lambda: lib._set_instance_attrs_node_list(
                create_env(), "attrs", ["node-1", "node-9"], False
            ),
            (
                severity.ERROR,
                report_codes.NODE_NOT_FOUND,
                {
                    "node": "node-9",
                }
            )
        )
        mock_attrs.assert_not_called()

@patch_env("push_cib")
class CibRunnerNodes(TestCase):
    def setUp(self):
        self.env = create_env()

    @patch_env("get_cib", lambda self: "mocked cib")
    @patch_env("cmd_runner", lambda self: "mocked cmd_runner")
    @patch_env("ensure_wait_satisfiable")
    @patch_command("ClusterState")
    @patch_command("get_cluster_status_xml")
    def test_wire_together_all_expected_dependecies(
        self, get_cluster_status_xml, ClusterState, ensure_wait_satisfiable,
        push_cib
    ):
        ClusterState.return_value = mock.MagicMock(
            node_section=mock.MagicMock(nodes="nodes")
        )
        get_cluster_status_xml.return_value = "mock get_cluster_status_xml"
        wait = 10

        with lib.cib_runner_nodes(self.env, wait) as (cib, runner, nodes):
            self.assertEqual(cib, "mocked cib")
            self.assertEqual(runner, "mocked cmd_runner")
            self.assertEqual(nodes, "nodes")
            ensure_wait_satisfiable.assert_called_once_with(wait)
            get_cluster_status_xml.assert_called_once_with("mocked cmd_runner")
            ClusterState.assert_called_once_with("mock get_cluster_status_xml")

        push_cib.assert_called_once_with(wait=wait)

    @patch_env("ensure_wait_satisfiable", mock.Mock(side_effect=LibraryError))
    def test_raises_when_wait_is_not_satisfiable(self, push_cib):
        def run():
            #pylint: disable=unused-variable
            with lib.cib_runner_nodes(self.env, "wait") as (cib, runner, nodes):
                pass

        self.assertRaises(LibraryError, run)
        push_cib.assert_not_called()
