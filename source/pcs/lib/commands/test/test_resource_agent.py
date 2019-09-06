# coding=utf-8
from __future__ import (
    absolute_import,
    division,
    print_function,
)

import logging
from lxml import etree

from pcs.test.tools.assertions import assert_raise_library_error, start_tag_error_text
from pcs.test.tools.command_env import get_env_tools
from pcs.test.tools.custom_mock import MockLibraryReportProcessor
from pcs.test.tools.pcs_unittest import mock, TestCase

from pcs.common import report_codes
from pcs.lib import resource_agent as lib_ra
from pcs.lib.env import LibraryEnvironment
from pcs.lib.errors import ReportItemSeverity as severity

from pcs.lib.commands import resource_agent as lib


@mock.patch("pcs.lib.resource_agent.list_resource_agents_standards")
@mock.patch.object(
    LibraryEnvironment,
    "cmd_runner",
    lambda self: "mock_runner"
)
class TestListStandards(TestCase):
    def setUp(self):
        self.mock_logger = mock.MagicMock(logging.Logger)
        self.mock_reporter = MockLibraryReportProcessor()
        self.lib_env = LibraryEnvironment(self.mock_logger, self.mock_reporter)


    def test_success(self, mock_list_standards):
        standards = [
            "lsb",
            "nagios",
            "ocf",
            "service",
            "systemd",
        ]
        mock_list_standards.return_value = standards

        self.assertEqual(
            lib.list_standards(self.lib_env),
            standards
        )

        mock_list_standards.assert_called_once_with("mock_runner")


@mock.patch("pcs.lib.resource_agent.list_resource_agents_ocf_providers")
@mock.patch.object(
    LibraryEnvironment,
    "cmd_runner",
    lambda self: "mock_runner"
)
class TestListOcfProviders(TestCase):
    def setUp(self):
        self.mock_logger = mock.MagicMock(logging.Logger)
        self.mock_reporter = MockLibraryReportProcessor()
        self.lib_env = LibraryEnvironment(self.mock_logger, self.mock_reporter)


    def test_success(self, mock_list_providers):
        providers = [
            "booth",
            "heartbeat",
            "openstack",
            "pacemaker",
        ]
        mock_list_providers.return_value = providers

        self.assertEqual(
            lib.list_ocf_providers(self.lib_env),
            providers
        )

        mock_list_providers.assert_called_once_with("mock_runner")


@mock.patch("pcs.lib.resource_agent.list_resource_agents_standards")
@mock.patch("pcs.lib.resource_agent.list_resource_agents")
@mock.patch.object(
    LibraryEnvironment,
    "cmd_runner",
    lambda self: "mock_runner"
)
class TestListAgentsForStandardAndProvider(TestCase):
    def setUp(self):
        self.mock_logger = mock.MagicMock(logging.Logger)
        self.mock_reporter = MockLibraryReportProcessor()
        self.lib_env = LibraryEnvironment(self.mock_logger, self.mock_reporter)


    def test_standard_specified(self, mock_list_agents, mock_list_standards):
        agents = [
            "Delay",
            "Dummy",
            "Stateful",
        ]
        mock_list_agents.return_value = agents

        self.assertEqual(
            lib.list_agents_for_standard_and_provider(self.lib_env, "ocf:test"),
            agents
        )

        mock_list_agents.assert_called_once_with("mock_runner", "ocf:test")
        mock_list_standards.assert_not_called()


    def test_standard_not_specified(
        self, mock_list_agents, mock_list_standards
    ):
        agents_ocf = [
            "Delay",
            "Dummy",
            "Stateful",
        ]
        agents_service = [
            "corosync",
            "pacemaker",
            "pcsd",
        ]
        mock_list_standards.return_value = ["ocf:test", "service"]
        mock_list_agents.side_effect = [agents_ocf, agents_service]

        self.assertEqual(
            lib.list_agents_for_standard_and_provider(self.lib_env),
            sorted(agents_ocf + agents_service, key=lambda x: x.lower())
        )

        mock_list_standards.assert_called_once_with("mock_runner")
        self.assertEqual(2, len(mock_list_agents.mock_calls))
        mock_list_agents.assert_has_calls([
            mock.call("mock_runner", "ocf:test"),
            mock.call("mock_runner", "service"),
        ])


@mock.patch(
    "pcs.lib.resource_agent.list_resource_agents_standards_and_providers",
    lambda runner: ["service", "ocf:test"]
)
@mock.patch(
    "pcs.lib.resource_agent.list_resource_agents",
    lambda runner, standard: {
        "ocf:test": [
            "Stateful",
            "Delay",
        ],
        "service": [
            "corosync",
            "pacemaker_remote",
        ],
    }.get(standard, [])
)
@mock.patch.object(
    LibraryEnvironment,
    "cmd_runner",
    lambda self: "mock_runner"
)
class TestListAgents(TestCase):
    def setUp(self):
        self.mock_logger = mock.MagicMock(logging.Logger)
        self.mock_reporter = MockLibraryReportProcessor()
        self.lib_env = LibraryEnvironment(self.mock_logger, self.mock_reporter)


    def test_list_all(self):
        self.assertEqual(
            lib.list_agents(self.lib_env, False, None),
            [
                {
                    "name": "ocf:test:Delay",
                    "shortdesc": "",
                    "longdesc": "",
                    "parameters": [],
                    "actions": [],
                },
                {
                    "name": "ocf:test:Stateful",
                    "shortdesc": "",
                    "longdesc": "",
                    "parameters": [],
                    "actions": [],
                },
                {
                    "name": "service:corosync",
                    "shortdesc": "",
                    "longdesc": "",
                    "parameters": [],
                    "actions": [],
                },
                {
                    "name": "service:pacemaker_remote",
                    "shortdesc": "",
                    "longdesc": "",
                    "parameters": [],
                    "actions": [],
                },
            ]
        )


    def test_search(self):
        self.assertEqual(
            lib.list_agents(self.lib_env, False, "te"),
            [
                {
                    "name": "ocf:test:Delay",
                    "shortdesc": "",
                    "longdesc": "",
                    "parameters": [],
                    "actions": [],
                },
                {
                    "name": "ocf:test:Stateful",
                    "shortdesc": "",
                    "longdesc": "",
                    "parameters": [],
                    "actions": [],
                },
                {
                    "name": "service:pacemaker_remote",
                    "shortdesc": "",
                    "longdesc": "",
                    "parameters": [],
                    "actions": [],
                },
            ]
        )


    @mock.patch.object(lib_ra.Agent, "_get_metadata", autospec=True)
    def test_describe(self, mock_metadata):
        def mock_metadata_func(self):
            if self.get_name() == "ocf:test:Stateful":
                raise lib_ra.UnableToGetAgentMetadata(
                    self.get_name(),
                    "test exception"
                )
            return etree.XML("""
                <resource-agent>
                    <shortdesc>short {name}</shortdesc>
                    <longdesc>long {name}</longdesc>
                    <parameters>
                    </parameters>
                    <actions>
                    </actions>
                </resource-agent>
            """.format(name=self.get_name()))
        mock_metadata.side_effect = mock_metadata_func

        # Stateful is missing as it does not provide valid metadata - see above
        self.assertEqual(
            lib.list_agents(self.lib_env, True, None),
            [
                {
                    "name": "ocf:test:Delay",
                    "shortdesc": "short ocf:test:Delay",
                    "longdesc": "long ocf:test:Delay",
                    "parameters": [],
                    "actions": [],
                },
                {
                    "name": "service:corosync",
                    "shortdesc": "short service:corosync",
                    "longdesc": "long service:corosync",
                    "parameters": [],
                    "actions": [],
                },
                {
                    "name": "service:pacemaker_remote",
                    "shortdesc": "short service:pacemaker_remote",
                    "longdesc": "long service:pacemaker_remote",
                    "parameters": [],
                    "actions": [],
                },
            ]
        )


class CompleteAgentList(TestCase):
    def test_skip_agent_name_when_InvalidResourceAgentName_raised(self):
        invalid_agent_name =  "systemd:lvm2-pvscan@252:2"#suppose it is invalid
        class Agent(object):
            def __init__(self, runner, name):
                if name == invalid_agent_name:
                    raise lib_ra.InvalidResourceAgentName(name)
                self.name = name

            def get_name_info(self):
                return self.name

        self.assertEqual(["ocf:heartbeat:Dummy"], lib._complete_agent_list(
            mock.MagicMock(),
            ["ocf:heartbeat:Dummy", invalid_agent_name],
            describe=False,
            search=False,
            metadata_class=Agent,
        ))

@mock.patch.object(lib_ra.ResourceAgent, "_load_metadata", autospec=True)
@mock.patch("pcs.lib.resource_agent.guess_exactly_one_resource_agent_full_name")
@mock.patch.object(
    LibraryEnvironment,
    "cmd_runner",
    lambda self: "mock_runner"
)
class TestDescribeAgent(TestCase):
    def setUp(self):
        self.mock_logger = mock.MagicMock(logging.Logger)
        self.mock_reporter = MockLibraryReportProcessor()
        self.lib_env = LibraryEnvironment(self.mock_logger, self.mock_reporter)
        self.metadata = """
            <resource-agent>
                <shortdesc>short desc</shortdesc>
                <longdesc>long desc</longdesc>
                <parameters>
                </parameters>
                <actions>
                </actions>
            </resource-agent>
        """
        self.description = {
            "name": "ocf:test:Dummy",
            "shortdesc": "short desc",
            "longdesc": "long desc",
            "parameters": [],
            "actions": [],
            "default_actions": [{"interval": "60s", "name": "monitor"}],
        }


    def test_full_name_success(self, mock_guess, mock_metadata):
        mock_metadata.return_value = self.metadata

        self.assertEqual(
            lib.describe_agent(self.lib_env, "ocf:test:Dummy"),
            self.description
        )

        self.assertEqual(len(mock_metadata.mock_calls), 1)
        mock_guess.assert_not_called()


    def test_guess_success(self, mock_guess, mock_metadata):
        mock_metadata.return_value = self.metadata
        mock_guess.return_value = lib_ra.ResourceAgent(
            self.lib_env.cmd_runner(),
            "ocf:test:Dummy"
        )

        self.assertEqual(
            lib.describe_agent(self.lib_env, "dummy"),
            self.description
        )

        self.assertEqual(len(mock_metadata.mock_calls), 1)
        mock_guess.assert_called_once_with("mock_runner", "dummy")


    def test_full_name_fail(self, mock_guess, mock_metadata):
        mock_metadata.return_value = "invalid xml"

        assert_raise_library_error(
            lambda: lib.describe_agent(self.lib_env, "ocf:test:Dummy"),
            (
                severity.ERROR,
                report_codes.UNABLE_TO_GET_AGENT_METADATA,
                {
                    "agent": "ocf:test:Dummy",
                    "reason": start_tag_error_text(),
                }
            )
        )

        self.assertEqual(len(mock_metadata.mock_calls), 1)
        mock_guess.assert_not_called()


class DescribeAgentUtf8(TestCase):
    def setUp(self):
        self.env_assist, self.config = get_env_tools(test_case=self)
        self.config.runner.pcmk.load_agent(
            agent_filename="resource_agent_ocf_heartbeat_dummy_utf8.xml"
        )

    def test_describe(self):
        name = "ocf:heartbeat:Dummy"
        self.assertEqual(
            lib.describe_agent(self.env_assist.get_env(), name),
            {
                "name": name,
                "shortdesc": u"Example stateless resource agent: ®",
                "longdesc": u"This is a Dummy Resource Agent for testing utf-8"
                    u" in metadata: ®"
                ,
                "parameters": [
                    {
                        "advanced": False,
                        "default": u"/var/run/resource-agents/Dummy-®.state",
                        "deprecated": False,
                        "longdesc":
                            u"Location to store the resource state in: ®",
                        "name": u"state-®",
                        "obsoletes": None,
                        "pcs_deprecated_warning": "",
                        "required": False,
                        "shortdesc": u"State file: ®",
                        "type": "string",
                        "unique": True,
                    },
                    {
                        "advanced": True,
                        "default": 0,
                        "deprecated": False,
                        "longdesc": "Set to 1 to turn on resource agent tracing"
                            " (expect large output) The trace output will be "
                            "saved to trace_file, if set, or by default to "
                            "$HA_VARRUN/ra_trace/<type>/<id>.<action>."
                            "<timestamp> e.g. $HA_VARRUN/ra_trace/oracle/db."
                            "start.2012-11-27.08:37:08",
                        "name": "trace_ra",
                        "obsoletes": None,
                        "pcs_deprecated_warning": "",
                        "required": False,
                        "shortdesc": "Set to 1 to turn on resource agent "
                            "tracing (expect large output)",
                        "type": "integer",
                        "unique": False,
                    },
                    {
                        "advanced": True,
                        "default": "",
                        "deprecated": False,
                        "longdesc": "Path to a file to store resource agent "
                            "tracing log",
                        "name": "trace_file",
                        "obsoletes": None,
                        "pcs_deprecated_warning": "",
                        "required": False,
                        "shortdesc": "Path to a file to store resource agent "
                            "tracing log",
                        "type": "string",
                        "unique": False,
                    }
                ],
                "actions": [
                    {"name": "start", "timeout": "20"},
                    {"name": "stop", "timeout": "20"},
                    {"name": "monitor", "interval": "10", "timeout": "20"},
                    {"name": "meta-data", "timeout": "5"},
                    {"name": "validate-all", "timeout": "20"},
                    {"name": u"custom-®", "timeout": "20"},
                ],
                "default_actions": [
                    {"name": "start", "interval": "0s", "timeout": "20"},
                    {"name": "stop", "interval": "0s", "timeout": "20"},
                    {"name": "monitor", "interval": "10", "timeout": "20"},
                    {"name": u"custom-®", "interval": "0s", "timeout": "20"},
                ],
            }
        )
