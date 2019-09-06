from __future__ import (
    absolute_import,
    division,
    print_function,
)

from pcs.test.tools.pcs_unittest import TestCase
import logging
from functools import partial
from lxml import etree

from pcs.test.tools import fixture
from pcs.test.tools.assertions import (
    assert_raise_library_error,
    assert_xml_equal,
)
from pcs.test.tools.command_env import get_env_tools
from pcs.test.tools.custom_mock import MockLibraryReportProcessor
from pcs.test.tools.misc import get_test_resource as rc, create_patcher
from pcs.test.tools.pcs_unittest import mock

from pcs.lib.env import LibraryEnvironment
from pcs.common import report_codes
from pcs.lib.node import NodeAddresses, NodeAddressesList
from pcs.lib.cluster_conf_facade import ClusterConfFacade
from pcs.lib.corosync.config_facade import ConfigFacade as CorosyncConfigFacade
from pcs.lib.errors import ReportItemSeverity as severity


patch_env = create_patcher("pcs.lib.env")
patch_env_object = partial(mock.patch.object, LibraryEnvironment)


class LibraryEnvironmentTest(TestCase):
    def setUp(self):
        self.mock_logger = mock.MagicMock(logging.Logger)
        self.mock_reporter = MockLibraryReportProcessor()

    def test_logger(self):
        env = LibraryEnvironment(self.mock_logger, self.mock_reporter)
        self.assertEqual(self.mock_logger, env.logger)

    def test_report_processor(self):
        env = LibraryEnvironment(self.mock_logger, self.mock_reporter)
        self.assertEqual(self.mock_reporter, env.report_processor)

    def test_user_set(self):
        user = "testuser"
        env = LibraryEnvironment(
            self.mock_logger,
            self.mock_reporter,
            user_login=user
        )
        self.assertEqual(user, env.user_login)

    def test_user_not_set(self):
        env = LibraryEnvironment(self.mock_logger, self.mock_reporter)
        self.assertEqual(None, env.user_login)

    def test_usergroups_set(self):
        groups = ["some", "group"]
        env = LibraryEnvironment(
            self.mock_logger,
            self.mock_reporter,
            user_groups=groups
        )
        self.assertEqual(groups, env.user_groups)

    def test_usergroups_not_set(self):
        env = LibraryEnvironment(self.mock_logger, self.mock_reporter)
        self.assertEqual([], env.user_groups)

    @patch_env("is_cman_cluster")
    def test_is_cman_cluster(self, mock_is_cman):
        mock_is_cman.return_value = True
        env = LibraryEnvironment(self.mock_logger, self.mock_reporter)
        self.assertTrue(env.is_cman_cluster)
        self.assertTrue(env.is_cman_cluster)
        self.assertEqual(1, mock_is_cman.call_count)


    @patch_env("get_local_cluster_conf")
    def test_get_cluster_conf_live(self, mock_get_local_cluster_conf):
        env = LibraryEnvironment(
            self.mock_logger, self.mock_reporter, cluster_conf_data=None
        )
        mock_get_local_cluster_conf.return_value = "cluster.conf data"
        self.assertEqual("cluster.conf data", env.get_cluster_conf_data())
        mock_get_local_cluster_conf.assert_called_once_with()

    @patch_env("get_local_cluster_conf")
    def test_get_cluster_conf_not_live(self, mock_get_local_cluster_conf):
        env = LibraryEnvironment(
            self.mock_logger, self.mock_reporter, cluster_conf_data="data"
        )
        self.assertEqual("data", env.get_cluster_conf_data())
        self.assertEqual(0, mock_get_local_cluster_conf.call_count)

    @mock.patch.object(
        LibraryEnvironment,
        "get_cluster_conf_data",
        lambda self: "<cluster/>"
    )
    def test_get_cluster_conf(self):
        env = LibraryEnvironment(self.mock_logger, self.mock_reporter)
        facade_obj = env.get_cluster_conf()
        self.assertTrue(isinstance(facade_obj, ClusterConfFacade))
        assert_xml_equal(
            '<cluster/>', etree.tostring(facade_obj._config).decode()
        )

    def test_is_cluster_conf_live_live(self):
        env = LibraryEnvironment(self.mock_logger, self.mock_reporter)
        self.assertTrue(env.is_cluster_conf_live)

    def test_is_cluster_conf_live_not_live(self):
        env = LibraryEnvironment(
            self.mock_logger, self.mock_reporter, cluster_conf_data="data"
        )
        self.assertFalse(env.is_cluster_conf_live)

@patch_env("CommandRunner")
class CmdRunner(TestCase):
    def setUp(self):
        self.mock_logger = mock.MagicMock(logging.Logger)
        self.mock_reporter = MockLibraryReportProcessor()

    def test_no_options(self, mock_runner):
        expected_runner = mock.MagicMock()
        mock_runner.return_value = expected_runner
        env = LibraryEnvironment(self.mock_logger, self.mock_reporter)
        runner = env.cmd_runner()
        self.assertEqual(expected_runner, runner)
        mock_runner.assert_called_once_with(
            self.mock_logger,
            self.mock_reporter,
            {
                "LC_ALL": "C",
            }
        )

    def test_user(self, mock_runner):
        expected_runner = mock.MagicMock()
        mock_runner.return_value = expected_runner
        user = "testuser"
        env = LibraryEnvironment(
            self.mock_logger,
            self.mock_reporter,
            user_login=user
        )
        runner = env.cmd_runner()
        self.assertEqual(expected_runner, runner)
        mock_runner.assert_called_once_with(
            self.mock_logger,
            self.mock_reporter,
            {
                "CIB_user": user,
                "LC_ALL": "C",
            }
        )

    @patch_env("write_tmpfile")
    def test_dump_cib_file(self, mock_tmpfile, mock_runner):
        expected_runner = mock.MagicMock()
        mock_runner.return_value = expected_runner
        mock_instance = mock.MagicMock()
        mock_instance.name = rc("file.tmp")
        mock_tmpfile.return_value = mock_instance
        env = LibraryEnvironment(
            self.mock_logger,
            self.mock_reporter,
            cib_data="<cib />"
        )
        runner = env.cmd_runner()
        self.assertEqual(expected_runner, runner)
        mock_runner.assert_called_once_with(
            self.mock_logger,
            self.mock_reporter,
            {
                "LC_ALL": "C",
                "CIB_file": rc("file.tmp"),
            }
        )
        mock_tmpfile.assert_called_once_with("<cib />")


@patch_env_object("cmd_runner", lambda self: "runner")
class EnsureValidWait(TestCase):
    def setUp(self):
        self.create_env = partial(
            LibraryEnvironment,
            mock.MagicMock(logging.Logger),
            MockLibraryReportProcessor()
        )

    @property
    def env_live(self):
        return self.create_env()

    @property
    def env_fake(self):
        return self.create_env(cib_data="<cib/>")

    def test_not_raises_if_waiting_false_no_matter_if_env_is_live(self):
        self.env_live.ensure_wait_satisfiable(False)
        self.env_fake.ensure_wait_satisfiable(False)

    def test_raises_when_is_not_live(self):
        env = self.env_fake
        assert_raise_library_error(
            lambda: env.ensure_wait_satisfiable(10),
            (
                severity.ERROR,
                report_codes.WAIT_FOR_IDLE_NOT_LIVE_CLUSTER,
                {},
                None
            )
        )

    @patch_env("get_valid_timeout_seconds")
    @patch_env("ensure_wait_for_idle_support")
    def test_do_checks(self, ensure_wait_for_idle_support, get_valid_timeout):
        env = self.env_live
        env.ensure_wait_satisfiable(10)
        ensure_wait_for_idle_support.assert_called_once_with(env.cmd_runner())
        get_valid_timeout.assert_called_once_with(10)


class PushCorosyncConfLiveBase(TestCase):
    def setUp(self):
        self.env_assistant, self.config = get_env_tools(self)
        self.corosync_conf_facade = mock.MagicMock(CorosyncConfigFacade)
        self.corosync_conf_text = "corosync conf"
        self.corosync_conf_facade.config.export.return_value = (
            self.corosync_conf_text
        )
        self.corosync_conf_facade.get_nodes.return_value = NodeAddressesList([
            NodeAddresses("node-1"),
            NodeAddresses("node-2"),
        ])
        self.corosync_conf_facade.need_stopped_cluster = False
        self.corosync_conf_facade.need_qdevice_reload = False
        self.node_labels = ["node-1", "node-2"]


@mock.patch("pcs.lib.external.is_systemctl", lambda: True)
class PushCorosyncConfLiveNoQdeviceTest(PushCorosyncConfLiveBase):
    def test_dont_need_stopped_cluster(self):
        (self.config
            .http.corosync.set_corosync_conf(
                self.corosync_conf_text,
                node_labels=self.node_labels
            )
            .runner.systemctl.is_active("corosync")
            .runner.corosync.reload()
        )
        self.env_assistant.get_env().push_corosync_conf(
            self.corosync_conf_facade
        )
        self.env_assistant.assert_reports([
            fixture.info(report_codes.COROSYNC_CONFIG_DISTRIBUTION_STARTED),
            fixture.info(
                report_codes.COROSYNC_CONFIG_ACCEPTED_BY_NODE,
                node="node-1",
            ),
            fixture.info(
                report_codes.COROSYNC_CONFIG_ACCEPTED_BY_NODE,
                node="node-2",
            ),
            fixture.info(report_codes.COROSYNC_CONFIG_RELOADED)
        ])

    def test_dont_need_stopped_cluster_error(self):
        (self.config
            .http.corosync.set_corosync_conf(
                self.corosync_conf_text,
                communication_list=[
                    {
                        "label": "node-1",
                    },
                    {
                        "label": "node-2",
                        "response_code": 400,
                        "output": "Failed"
                    },
                ]
            )
        )
        env = self.env_assistant.get_env()
        self.env_assistant.assert_raise_library_error(
            lambda: env.push_corosync_conf(self.corosync_conf_facade),
            []
        )
        self.env_assistant.assert_reports([
            fixture.info(report_codes.COROSYNC_CONFIG_DISTRIBUTION_STARTED),
            fixture.info(
                report_codes.COROSYNC_CONFIG_ACCEPTED_BY_NODE,
                node="node-1",
            ),
            fixture.error(
                report_codes.NODE_COMMUNICATION_COMMAND_UNSUCCESSFUL,
                force_code=report_codes.SKIP_OFFLINE_NODES,
                node="node-2",
                command="remote/set_corosync_conf",
                reason="Failed",
            ),
            fixture.error(
                report_codes.COROSYNC_CONFIG_DISTRIBUTION_NODE_ERROR,
                force_code=report_codes.SKIP_OFFLINE_NODES,
                node="node-2",
            ),
        ])

    def test_dont_need_stopped_cluster_error_skip_offline(self):
        (self.config
            .http.corosync.set_corosync_conf(
                self.corosync_conf_text,
                communication_list=[
                    {
                        "label": "node-1",
                    },
                    {
                        "label": "node-2",
                        "response_code": 400,
                        "output": "Failed"
                    },
                ]
            )
            .runner.systemctl.is_active("corosync")
            .runner.corosync.reload()
        )
        self.env_assistant.get_env().push_corosync_conf(
            self.corosync_conf_facade, skip_offline_nodes=True
        )
        self.env_assistant.assert_reports([
            fixture.info(report_codes.COROSYNC_CONFIG_DISTRIBUTION_STARTED),
            fixture.info(
                report_codes.COROSYNC_CONFIG_ACCEPTED_BY_NODE,
                node="node-1",
            ),
            fixture.warn(
                report_codes.NODE_COMMUNICATION_COMMAND_UNSUCCESSFUL,
                node="node-2",
                command="remote/set_corosync_conf",
                reason="Failed",
            ),
            fixture.warn(
                report_codes.COROSYNC_CONFIG_DISTRIBUTION_NODE_ERROR,
                node="node-2",
            ),
            fixture.info(report_codes.COROSYNC_CONFIG_RELOADED)
        ])

    def test_need_stopped_cluster(self):
        self.corosync_conf_facade.need_stopped_cluster = True
        (self.config
            .http.corosync.check_corosync_offline(
                node_labels=self.node_labels
            )
            .http.corosync.set_corosync_conf(
                self.corosync_conf_text,
                node_labels=self.node_labels
            )
            .runner.systemctl.is_active("corosync", is_active=False)
        )
        self.env_assistant.get_env().push_corosync_conf(
            self.corosync_conf_facade
        )
        self.env_assistant.assert_reports([
            fixture.info(report_codes.COROSYNC_NOT_RUNNING_CHECK_STARTED),
            fixture.info(
                report_codes.COROSYNC_NOT_RUNNING_ON_NODE,
                node="node-1",
            ),
            fixture.info(
                report_codes.COROSYNC_NOT_RUNNING_ON_NODE,
                node="node-2",
            ),
            fixture.info(report_codes.COROSYNC_CONFIG_DISTRIBUTION_STARTED),
            fixture.info(
                report_codes.COROSYNC_CONFIG_ACCEPTED_BY_NODE,
                node="node-1",
            ),
            fixture.info(
                report_codes.COROSYNC_CONFIG_ACCEPTED_BY_NODE,
                node="node-2",
            ),
        ])

    def test_need_stopped_cluster_not_stopped(self):
        self.corosync_conf_facade.need_stopped_cluster = True
        (self.config
            .http.corosync.check_corosync_offline(
                communication_list=[
                    {
                        "label": node,
                        "output": '{"corosync":true}'
                    }
                    for node in self.node_labels
                ]
            )
        )
        env = self.env_assistant.get_env()
        self.env_assistant.assert_raise_library_error(
            lambda: env.push_corosync_conf(self.corosync_conf_facade),
            []
        )
        self.env_assistant.assert_reports([
            fixture.info(report_codes.COROSYNC_NOT_RUNNING_CHECK_STARTED),
            fixture.error(
                report_codes.COROSYNC_RUNNING_ON_NODE,
                node="node-1",
            ),
            fixture.error(
                report_codes.COROSYNC_RUNNING_ON_NODE,
                node="node-2",
            ),
        ])

    def test_need_stopped_cluster_not_stopped_skip_offline(self):
        # If we know for sure that corosync is running, skip_offline doesn't
        # matter.
        self.corosync_conf_facade.need_stopped_cluster = True
        (self.config
            .http.corosync.check_corosync_offline(
                communication_list=[
                    dict(
                        label="node-1",
                        output='{"corosync":true}',
                    ),
                    dict(
                        label="node-2",
                    ),
                ]
            )
        )
        env = self.env_assistant.get_env()
        self.env_assistant.assert_raise_library_error(
            lambda: env.push_corosync_conf(
                self.corosync_conf_facade, skip_offline_nodes=True
            ),
            []
        )
        self.env_assistant.assert_reports([
            fixture.info(report_codes.COROSYNC_NOT_RUNNING_CHECK_STARTED),
            fixture.error(
                report_codes.COROSYNC_RUNNING_ON_NODE,
                node="node-1",
            ),
            fixture.info(
                report_codes.COROSYNC_NOT_RUNNING_ON_NODE,
                node="node-2",
            )
        ])

    def test_need_stopped_cluster_json_error(self):
        self.corosync_conf_facade.need_stopped_cluster = True
        (self.config
            .http.corosync.check_corosync_offline(
                communication_list=[
                    dict(
                        label="node-1",
                        output="{" # not valid json
                    ),
                    dict(
                        label="node-2",
                        # The expected key (/corosync) is missing, we don't
                        # care about version 2 status key
                        # (/services/corosync/running)
                        output='{"services":{"corosync":{"running":true}}}'
                    ),
                ]
            )
        )
        env = self.env_assistant.get_env()
        self.env_assistant.assert_raise_library_error(
            lambda: env.push_corosync_conf(self.corosync_conf_facade),
            []
        )
        self.env_assistant.assert_reports([
            fixture.info(report_codes.COROSYNC_NOT_RUNNING_CHECK_STARTED),
            fixture.error(
                report_codes.COROSYNC_NOT_RUNNING_CHECK_NODE_ERROR,
                force_code=report_codes.SKIP_OFFLINE_NODES,
                node="node-1",
            ),
            fixture.error(
                report_codes.COROSYNC_NOT_RUNNING_CHECK_NODE_ERROR,
                force_code=report_codes.SKIP_OFFLINE_NODES,
                node="node-2",
            ),
        ])

    def test_need_stopped_cluster_comunnication_failure(self):
        self.corosync_conf_facade.need_stopped_cluster = True
        (self.config
            .http.corosync.check_corosync_offline(
                communication_list=[
                    dict(
                        label="node-1",
                    ),
                    dict(
                        label="node-2",
                        response_code=401,
                        output="""{"notauthorized":"true"}"""
                    ),
                ]
            )
        )
        env = self.env_assistant.get_env()
        self.env_assistant.assert_raise_library_error(
            lambda: env.push_corosync_conf(self.corosync_conf_facade),
            []
        )
        self.env_assistant.assert_reports([
            fixture.info(report_codes.COROSYNC_NOT_RUNNING_CHECK_STARTED),
            fixture.info(
                report_codes.COROSYNC_NOT_RUNNING_ON_NODE,
                node="node-1",
            ),
            fixture.error(
                report_codes.NODE_COMMUNICATION_ERROR_NOT_AUTHORIZED,
                force_code=report_codes.SKIP_OFFLINE_NODES,
                node="node-2",
            ),
            fixture.error(
                report_codes.COROSYNC_NOT_RUNNING_CHECK_NODE_ERROR,
                force_code=report_codes.SKIP_OFFLINE_NODES,
                node="node-2",
            ),
        ])

    def test_need_stopped_cluster_comunnication_failures_skip_offline(self):
        # If we don't know if corosync is running, skip_offline matters.
        self.corosync_conf_facade.need_stopped_cluster = True
        (self.config
            .http.corosync.check_corosync_offline(
                communication_list=[
                    dict(
                        label="node-1",
                        output="{" # not valid json
                    ),
                    dict(
                        label="node-2",
                        response_code=401,
                        output="""{"notauthorized":"true"}"""
                    ),
                ]
            )
            .http.corosync.set_corosync_conf(
                self.corosync_conf_text,
                communication_list=[
                    dict(
                        label="node-1",
                    ),
                    dict(
                        label="node-2",
                        response_code=401,
                        output="""{"notauthorized":"true"}""",
                    )
                ]
            )
            .runner.systemctl.is_active("corosync", is_active=False)
        )
        self.env_assistant.get_env().push_corosync_conf(
            self.corosync_conf_facade, skip_offline_nodes=True
        )
        self.env_assistant.assert_reports([
            fixture.info(report_codes.COROSYNC_NOT_RUNNING_CHECK_STARTED),
            fixture.warn(
                report_codes.COROSYNC_NOT_RUNNING_CHECK_NODE_ERROR,
                node="node-1",
            ),
            fixture.warn(
                report_codes.NODE_COMMUNICATION_ERROR_NOT_AUTHORIZED,
                node="node-2",
                reason="HTTP error: 401",
                command="remote/status",
            ),
            fixture.warn(
                report_codes.COROSYNC_NOT_RUNNING_CHECK_NODE_ERROR,
                node="node-2",
            ),
            fixture.info(report_codes.COROSYNC_CONFIG_DISTRIBUTION_STARTED),
            fixture.info(
                report_codes.COROSYNC_CONFIG_ACCEPTED_BY_NODE,
                node="node-1",
            ),
            fixture.warn(
                report_codes.NODE_COMMUNICATION_ERROR_NOT_AUTHORIZED,
                node="node-2",
                reason="HTTP error: 401",
                command="remote/set_corosync_conf",
            ),
            fixture.warn(
                report_codes.COROSYNC_CONFIG_DISTRIBUTION_NODE_ERROR,
                node="node-2",
            ),
        ])


@mock.patch("pcs.lib.external.is_systemctl", lambda: True)
class PushCorosyncConfLiveWithQdeviceTest(PushCorosyncConfLiveBase):
    def test_qdevice_reload(self):
        self.corosync_conf_facade.need_qdevice_reload = True
        (self.config
            .http.corosync.set_corosync_conf(
                self.corosync_conf_text,
                node_labels=self.node_labels
            )
            .runner.systemctl.is_active("corosync", is_active=False)
            .http.corosync.qdevice_client_stop(
                node_labels=self.node_labels
            )
            .http.corosync.qdevice_client_start(
                node_labels=self.node_labels
            )
        )

        self.env_assistant.get_env().push_corosync_conf(
            self.corosync_conf_facade
        )

        self.env_assistant.assert_reports([
            fixture.info(report_codes.COROSYNC_CONFIG_DISTRIBUTION_STARTED),
            fixture.info(
                report_codes.COROSYNC_CONFIG_ACCEPTED_BY_NODE,
                node="node-1",
            ),
            fixture.info(
                report_codes.COROSYNC_CONFIG_ACCEPTED_BY_NODE,
                node="node-2",
            ),
            fixture.info(report_codes.QDEVICE_CLIENT_RELOAD_STARTED),
            fixture.info(
                report_codes.SERVICE_STOP_SUCCESS,
                node="node-1",
                service="corosync-qdevice",
                instance=None,
            ),
            fixture.info(
                report_codes.SERVICE_STOP_SUCCESS,
                node="node-2",
                service="corosync-qdevice",
                instance=None,
            ),
            fixture.info(
                report_codes.SERVICE_START_SUCCESS,
                node="node-1",
                service="corosync-qdevice",
                instance=None,
            ),
            fixture.info(
                report_codes.SERVICE_START_SUCCESS,
                node="node-2",
                service="corosync-qdevice",
                instance=None,
            ),
        ])

    def test_qdevice_reload_corosync_stopped(self):
        self.corosync_conf_facade.need_qdevice_reload = True
        (self.config
            .http.corosync.set_corosync_conf(
                self.corosync_conf_text,
                node_labels=self.node_labels
            )
            .runner.systemctl.is_active("corosync", is_active=False)
            .http.corosync.qdevice_client_stop(
                node_labels=self.node_labels
            )
            .http.corosync.qdevice_client_start(
                communication_list=[
                    {
                        "label": label,
                        "output": "corosync is not running, skipping",
                    }
                    for label in self.node_labels
                ]
            )
        )

        self.env_assistant.get_env().push_corosync_conf(
            self.corosync_conf_facade
        )

        self.env_assistant.assert_reports([
            fixture.info(report_codes.COROSYNC_CONFIG_DISTRIBUTION_STARTED),
            fixture.info(
                report_codes.COROSYNC_CONFIG_ACCEPTED_BY_NODE,
                node="node-1",
            ),
            fixture.info(
                report_codes.COROSYNC_CONFIG_ACCEPTED_BY_NODE,
                node="node-2",
            ),
            fixture.info(report_codes.QDEVICE_CLIENT_RELOAD_STARTED),
            fixture.info(
                report_codes.SERVICE_STOP_SUCCESS,
                node="node-1",
                service="corosync-qdevice",
                instance=None,
            ),
            fixture.info(
                report_codes.SERVICE_STOP_SUCCESS,
                node="node-2",
                service="corosync-qdevice",
                instance=None,
            ),
            fixture.info(
                report_codes.SERVICE_START_SKIPPED,
                node="node-1",
                service="corosync-qdevice",
                instance=None,
                reason="corosync is not running",
            ),
            fixture.info(
                report_codes.SERVICE_START_SKIPPED,
                node="node-2",
                service="corosync-qdevice",
                instance=None,
                reason="corosync is not running",
            ),
        ])

    def test_qdevice_reload_failures(self):
        # This also tests that failing to stop qdevice on a node doesn't prevent
        # starting qdevice on the same node.
        self.corosync_conf_facade.need_qdevice_reload = True
        (self.config
            .http.corosync.set_corosync_conf(
                self.corosync_conf_text,
                node_labels=self.node_labels
            )
            .runner.systemctl.is_active("corosync", is_active=False)
            .http.corosync.qdevice_client_stop(
                communication_list=[
                    dict(
                        label="node-1",
                    ),
                    dict(
                        label="node-2",
                        response_code=400,
                        output="error",
                    ),
                ]
            )
            .http.corosync.qdevice_client_start(
                communication_list=[
                    dict(
                        label="node-1",
                        errno=8,
                        error_msg="failure",
                        was_connected=False,
                    ),
                    dict(
                        label="node-2",
                    ),
                ]
            )
        )

        env = self.env_assistant.get_env()
        self.env_assistant.assert_raise_library_error(
            lambda: env.push_corosync_conf(self.corosync_conf_facade),
            []
        )

        self.env_assistant.assert_reports([
            fixture.info(report_codes.COROSYNC_CONFIG_DISTRIBUTION_STARTED),
            fixture.info(
                report_codes.COROSYNC_CONFIG_ACCEPTED_BY_NODE,
                node="node-1",
            ),
            fixture.info(
                report_codes.COROSYNC_CONFIG_ACCEPTED_BY_NODE,
                node="node-2",
            ),
            fixture.info(report_codes.QDEVICE_CLIENT_RELOAD_STARTED),
            fixture.info(
                report_codes.SERVICE_STOP_SUCCESS,
                node="node-1",
                service="corosync-qdevice",
                instance=None,
            ),
            fixture.error(
                report_codes.NODE_COMMUNICATION_COMMAND_UNSUCCESSFUL,
                force_code=report_codes.SKIP_OFFLINE_NODES,
                node="node-2",
                reason="error",
                command="remote/qdevice_client_stop",
            ),
            fixture.error(
                report_codes.NODE_COMMUNICATION_ERROR_UNABLE_TO_CONNECT,
                force_code=report_codes.SKIP_OFFLINE_NODES,
                node="node-1",
                reason="failure",
                command="remote/qdevice_client_start",
            ),
            fixture.info(
                report_codes.SERVICE_START_SUCCESS,
                node="node-2",
                service="corosync-qdevice",
                instance=None,
            ),
        ])

    def test_qdevice_reload_failures_skip_offline(self):
        self.corosync_conf_facade.need_qdevice_reload = True
        (self.config
            .http.corosync.set_corosync_conf(
                self.corosync_conf_text,
                communication_list=[
                    dict(
                        label="node-1",
                    ),
                    dict(
                        label="node-2",
                        errno=8,
                        error_msg="failure",
                        was_connected=False,
                    ),
                ]
            )
            .runner.systemctl.is_active("corosync", is_active=False)
            .http.corosync.qdevice_client_stop(
                communication_list=[
                    dict(
                        label="node-1",
                    ),
                    dict(
                        label="node-2",
                        response_code=400,
                        output="error",
                    ),
                ]
            )
            .http.corosync.qdevice_client_start(
                communication_list=[
                    dict(
                        label="node-1",
                        errno=8,
                        error_msg="failure",
                        was_connected=False,
                    ),
                    dict(
                        label="node-2",
                    ),
                ]
            )
        )

        env = self.env_assistant.get_env()
        env.push_corosync_conf(
            self.corosync_conf_facade, skip_offline_nodes=True
        )

        self.env_assistant.assert_reports([
            fixture.info(report_codes.COROSYNC_CONFIG_DISTRIBUTION_STARTED),
            fixture.info(
                report_codes.COROSYNC_CONFIG_ACCEPTED_BY_NODE,
                node="node-1",
            ),
            fixture.warn(
                report_codes.NODE_COMMUNICATION_ERROR_UNABLE_TO_CONNECT,
                node="node-2",
                reason="failure",
                command="remote/set_corosync_conf",
            ),
            fixture.warn(
                report_codes.COROSYNC_CONFIG_DISTRIBUTION_NODE_ERROR,
                node="node-2",
            ),
            fixture.info(report_codes.QDEVICE_CLIENT_RELOAD_STARTED),
            fixture.info(
                report_codes.SERVICE_STOP_SUCCESS,
                node="node-1",
                service="corosync-qdevice",
                instance=None,
            ),
            fixture.warn(
                report_codes.NODE_COMMUNICATION_COMMAND_UNSUCCESSFUL,
                node="node-2",
                reason="error",
                command="remote/qdevice_client_stop",
            ),
            fixture.warn(
                report_codes.NODE_COMMUNICATION_ERROR_UNABLE_TO_CONNECT,
                node="node-1",
                reason="failure",
                command="remote/qdevice_client_start",
            ),
            fixture.info(
                report_codes.SERVICE_START_SUCCESS,
                node="node-2",
                service="corosync-qdevice",
                instance=None,
            ),
        ])


class PushCorosyncConfFile(TestCase):
    def setUp(self):
        self.env_assistant, self.config = get_env_tools(test_case=self)
        self.config.env.set_corosync_conf_data("totem {\n    version: 2\n}\n")

    def test_success(self):
        new_corosync_conf_data = "totem {\n    version: 3\n}\n"
        self.config.env.push_corosync_conf(
            corosync_conf_text=new_corosync_conf_data
        )
        env = self.env_assistant.get_env()
        env.push_corosync_conf(
            CorosyncConfigFacade.from_string(new_corosync_conf_data)
        )


class GetCorosyncConfFile(TestCase):
    def setUp(self):
        self.corosync_conf_data = "totem {\n    version: 2\n}\n"
        self.env_assistant, self.config = get_env_tools(test_case=self)
        self.config.env.set_corosync_conf_data(self.corosync_conf_data)

    def test_success(self):
        env = self.env_assistant.get_env()
        self.assertFalse(env.is_corosync_conf_live)
        self.assertEqual(self.corosync_conf_data, env.get_corosync_conf_data())
        self.assertEqual(
            self.corosync_conf_data, env.get_corosync_conf().config.export()
        )


class GetCorosyncConfLive(TestCase):
    def setUp(self):
        self.env_assistant, self.config = get_env_tools(self)

    def test_success(self):
        corosync_conf_data = "totem {\n    version: 2\n}\n"
        self.config.corosync_conf.load_content(corosync_conf_data)
        env = self.env_assistant.get_env()
        self.assertTrue(env.is_corosync_conf_live)
        self.assertEqual(
            corosync_conf_data, env.get_corosync_conf().config.export()
        )
