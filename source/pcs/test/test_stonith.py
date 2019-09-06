from __future__ import (
    absolute_import,
    division,
    print_function,
)

import shutil

from pcs import utils
from pcs.cli.common.console_report import indent
from pcs.test.bin_mock import get_mock_settings
from pcs.test.tools.assertions import AssertPcsMixin
from pcs.test.tools.misc import (
    get_test_resource as rc,
    is_minimum_pacemaker_version,
    skip_unless_pacemaker_version,
    outdent,
)
from pcs.test.tools.pcs_runner import (
    pcs,
    PcsRunner,
)
from pcs.test.tools.pcs_unittest import TestCase


empty_cib = rc("cib-empty.xml")
temp_cib = rc("temp-cib.xml")

# target-pattern attribute was added in pacemaker 1.1.13 with validate-with 2.3.
# However in pcs this was implemented much later together with target-attribute
# support. In that time pacemaker 1.1.12 was quite old. To keep tests simple we
# do not run fencing topology tests on pacemaker older that 1.1.13 even if it
# supports targeting by node names.
skip_unless_fencing_level_supported = skip_unless_pacemaker_version(
    (1, 1, 13),
    "fencing levels"
)
# target-attribute and target-value attributes were added in pacemaker 1.1.14
# with validate-with 2.4.
fencing_level_attribute_supported = is_minimum_pacemaker_version(1, 1, 14)
skip_unless_fencing_level_attribute_supported = skip_unless_pacemaker_version(
    (1, 1, 14),
    "fencing levels with attribute targets"
)


class StonithDescribeTest(TestCase, AssertPcsMixin):
    def setUp(self):
        self.pcs_runner = PcsRunner(temp_cib)
        self.pcs_runner.mock_settings = get_mock_settings("crm_resource_binary")

    def test_success(self):
        self.assert_pcs_success(
            "stonith describe fence_apc",
            stdout_start="""\
fence_apc - Fence agent for APC over telnet/ssh

fence_apc is an I/O Fencing agent which can be used with the APC network power switch. It logs into device via telnet/ssh  and reboots a specified outlet. Lengthy telnet/ssh connections should be avoided while a GFS cluster  is  running  because  the  connection will block any necessary fencing actions.

Stonith options:
"""
        )

    def test_full(self):
        stdout, pcs_returncode = self.pcs_runner.run(
            "stonith describe fence_apc --full",
        )
        self.assertEqual(0, pcs_returncode)
        self.assertTrue("pcmk_list_retries" in stdout)

    def test_nonextisting_agent(self):
        self.assert_pcs_fail(
            "stonith describe absent",
            "Error: Agent 'absent' is not installed or does not provide valid "
            "metadata: Agent absent not found or does not support meta-data: "
            "Invalid argument (22)\nMetadata query for stonith:absent failed: "
            "Input/output error\n"
        )

    def test_not_enough_params(self):
        self.assert_pcs_fail(
            "stonith describe",
            stdout_start="\nUsage: pcs stonith describe...\n"
        )

    def test_too_many_params(self):
        self.assert_pcs_fail(
            "stonith describe agent1 agent2",
            stdout_start="\nUsage: pcs stonith describe...\n"
        )


class StonithTest(TestCase, AssertPcsMixin):
    def setUp(self):
        self.pcs_runner = PcsRunner(temp_cib)
        self.pcs_runner.mock_settings = get_mock_settings("crm_resource_binary")
        shutil.copy(empty_cib, temp_cib)

    def testStonithCreation(self):
        self.assert_pcs_fail(
            "stonith create test1 absent",
            "Error: Agent 'absent' is not installed or does not provide valid "
            "metadata: Agent absent not found or does not support meta-data: "
            "Invalid argument (22)\nMetadata query for stonith:absent failed: "
            "Input/output error, use --force to override\n"
        )

        self.assert_pcs_success(
            "stonith create test1 absent --force",
            "Warning: Agent 'absent' is not installed or does not provide valid "
            "metadata: Agent absent not found or does not support meta-data: "
            "Invalid argument (22)\nMetadata query for stonith:absent failed: "
            "Input/output error\n"
        )

        self.assert_pcs_fail(
            "stonith create test2 fence_apc",
            "Error: required stonith options 'ipaddr', 'login' are missing, use --force to override\n"
        )

        self.assert_pcs_success(
            "stonith create test2 fence_apc --force",
            "Warning: required stonith options 'ipaddr', 'login' are missing\n"
        )

        self.assert_pcs_fail(
            "stonith create test3 fence_apc bad_argument=test",
            stdout_start="Error: invalid stonith option 'bad_argument',"
                " allowed options are:"
        )

        self.assert_pcs_fail(
            "stonith create test9 fence_apc pcmk_status_action=xxx",
            "Error: required stonith options 'ipaddr', 'login' are missing, use --force to override\n"
        )

        self.assert_pcs_success(
             "stonith create test9 fence_apc pcmk_status_action=xxx --force",
            "Warning: required stonith options 'ipaddr', 'login' are missing\n"
        )

        self.assert_pcs_success("stonith show test9", outdent(
            """\
             Resource: test9 (class=stonith type=fence_apc)
              Attributes: pcmk_status_action=xxx
              Operations: monitor interval=60s (test9-monitor-interval-60s)
            """
        ))

        self.assert_pcs_success(
            "stonith delete test9",
            "Deleting Resource - test9\n"
        )

        self.assert_pcs_fail(
            "stonith create test3 fence_ilo ipaddr=test",
            "Error: required stonith option 'login' is missing, use --force to override\n"
        )

        self.assert_pcs_success(
             "stonith create test3 fence_ilo ipaddr=test --force",
            "Warning: required stonith option 'login' is missing\n"
        )

        # Testing that pcmk_host_check, pcmk_host_list & pcmk_host_map are
        # allowed for stonith agents
        self.assert_pcs_success(
            'stonith create apc-fencing fence_apc ipaddr="morph-apc" login="apc" passwd="apc" switch="1" pcmk_host_map="buzz-01:1;buzz-02:2;buzz-03:3;buzz-04:4;buzz-05:5" pcmk_host_check="static-list" pcmk_host_list="buzz-01,buzz-02,buzz-03,buzz-04,buzz-05"',
        )

        self.assert_pcs_fail(
            "resource show apc-fencing",
            "Error: unable to find resource 'apc-fencing'\n"
        )

        self.assert_pcs_success("stonith show apc-fencing", outdent(
            """\
             Resource: apc-fencing (class=stonith type=fence_apc)
              Attributes: ipaddr="morph-apc" login="apc" passwd="apc" pcmk_host_check="static-list" pcmk_host_list="buzz-01,buzz-02,buzz-03,buzz-04,buzz-05" pcmk_host_map="buzz-01:1;buzz-02:2;buzz-03:3;buzz-04:4;buzz-05:5" switch="1"
              Operations: monitor interval=60s (apc-fencing-monitor-interval-60s)
            """
        ))

        self.assert_pcs_success(
            "stonith delete apc-fencing",
            "Deleting Resource - apc-fencing\n"
        )

        self.assert_pcs_fail(
            "stonith update test3 bad_ipaddr=test",
            stdout_regexp=(
                "^Error: invalid stonith option 'bad_ipaddr', allowed options"
                " are: [^\n]+, use --force to override\n$"
            )
        )

        self.assert_pcs_success("stonith update test3 login=testA")

        self.assert_pcs_success("stonith show test2", outdent(
            """\
             Resource: test2 (class=stonith type=fence_apc)
              Operations: monitor interval=60s (test2-monitor-interval-60s)
            """
        ))

        self.assert_pcs_success("stonith show --full", outdent(
            """\
             Resource: test1 (class=stonith type=absent)
              Operations: monitor interval=60s (test1-monitor-interval-60s)
             Resource: test2 (class=stonith type=fence_apc)
              Operations: monitor interval=60s (test2-monitor-interval-60s)
             Resource: test3 (class=stonith type=fence_ilo)
              Attributes: ipaddr=test login=testA
              Operations: monitor interval=60s (test3-monitor-interval-60s)
            """
        ))

        self.assert_pcs_success(
            "stonith create test-fencing fence_apc 'pcmk_host_list=rhel7-node1 rhel7-node2' op monitor interval=61s --force",
            "Warning: required stonith options 'ipaddr', 'login' are missing\n"
        )

        self.assert_pcs_success("config show", outdent(
            """\
            Cluster Name: test99
            Corosync Nodes:
             rh7-1 rh7-2
            Pacemaker Nodes:

            Resources:

            Stonith Devices:
             Resource: test1 (class=stonith type=absent)
              Operations: monitor interval=60s (test1-monitor-interval-60s)
             Resource: test2 (class=stonith type=fence_apc)
              Operations: monitor interval=60s (test2-monitor-interval-60s)
             Resource: test3 (class=stonith type=fence_ilo)
              Attributes: ipaddr=test login=testA
              Operations: monitor interval=60s (test3-monitor-interval-60s)
             Resource: test-fencing (class=stonith type=fence_apc)
              Attributes: pcmk_host_list="rhel7-node1 rhel7-node2"
              Operations: monitor interval=61s (test-fencing-monitor-interval-61s)
            Fencing Levels:

            Location Constraints:
            Ordering Constraints:
            Colocation Constraints:
            Ticket Constraints:

            Alerts:
             No alerts defined

            Resources Defaults:
             No defaults set
            Operations Defaults:
             No defaults set

            Cluster Properties:

            Quorum:
              Options:
            """
        ))

    def test_stonith_create_provides_unfencing(self):
        if utils.is_rhel6():
            return

        self.assert_pcs_success("stonith create f1 fence_scsi")

        self.assert_pcs_success(
            "stonith create f2 fence_scsi meta provides=unfencing"
        )

        self.assert_pcs_success(
            "stonith create f3 fence_scsi meta provides=something"
        )

        self.assert_pcs_success(
            "stonith create f4 fence_xvm meta provides=something"
        )

        self.assert_pcs_success("stonith show --full", outdent(
            """\
             Resource: f1 (class=stonith type=fence_scsi)
              Meta Attrs: provides=unfencing
              Operations: monitor interval=60s (f1-monitor-interval-60s)
             Resource: f2 (class=stonith type=fence_scsi)
              Meta Attrs: provides=unfencing
              Operations: monitor interval=60s (f2-monitor-interval-60s)
             Resource: f3 (class=stonith type=fence_scsi)
              Meta Attrs: provides=unfencing
              Operations: monitor interval=60s (f3-monitor-interval-60s)
             Resource: f4 (class=stonith type=fence_xvm)
              Meta Attrs: provides=something
              Operations: monitor interval=60s (f4-monitor-interval-60s)
            """
        ))

    def test_stonith_create_provides_unfencing_rhel6(self):
        if not utils.is_rhel6():
            return

        self.assert_pcs_success(
            "stonith create f1 fence_mpath key=abc"
        )

        self.assert_pcs_success(
            "stonith create f2 fence_mpath key=abc meta provides=unfencing"
        )

        self.assert_pcs_success(
            "stonith create f3 fence_mpath key=abc meta provides=something"
        )

        self.assert_pcs_success(
            "stonith create f4 fence_xvm meta provides=something"
        )

        self.assert_pcs_success("stonith show --full", outdent(
            """\
             Resource: f1 (class=stonith type=fence_mpath)
              Attributes: key=abc
              Meta Attrs: provides=unfencing
              Operations: monitor interval=60s (f1-monitor-interval-60s)
             Resource: f2 (class=stonith type=fence_mpath)
              Attributes: key=abc
              Meta Attrs: provides=unfencing
              Operations: monitor interval=60s (f2-monitor-interval-60s)
             Resource: f3 (class=stonith type=fence_mpath)
              Attributes: key=abc
              Meta Attrs: provides=unfencing
              Operations: monitor interval=60s (f3-monitor-interval-60s)
             Resource: f4 (class=stonith type=fence_xvm)
              Meta Attrs: provides=something
              Operations: monitor interval=60s (f4-monitor-interval-60s)
            """
        ))

    def test_stonith_create_action(self):
        self.assert_pcs_fail(
            "stonith create test fence_apc ipaddr=i login=l action=a",
            "Error: stonith option 'action' is deprecated and should not be"
                " used, use pcmk_off_action, pcmk_reboot_action instead,"
                " use --force to override\n"
        )

        self.assert_pcs_success(
            "stonith create test fence_apc ipaddr=i login=l action=a --force",
            "Warning: stonith option 'action' is deprecated and should not be"
                " used, use pcmk_off_action, pcmk_reboot_action instead\n"
        )

        self.assert_pcs_success(
            "stonith show --full",
            outdent(
                """\
                 Resource: test (class=stonith type=fence_apc)
                  Attributes: action=a ipaddr=i login=l
                  Operations: monitor interval=60s (test-monitor-interval-60s)
                """
            )
        )

    def test_stonith_create_action_empty(self):
        self.assert_pcs_success(
            "stonith create test fence_apc ipaddr=i login=l action="
        )

        self.assert_pcs_success(
            "stonith show --full",
            # TODO fix code and test - there should be no action in the attribs
            outdent(
                """\
                 Resource: test (class=stonith type=fence_apc)
                  Attributes: action= ipaddr=i login=l
                  Operations: monitor interval=60s (test-monitor-interval-60s)
                """
            )
        )

    def test_stonith_update_action(self):
        self.assert_pcs_success(
            "stonith create test fence_apc ipaddr=i login=l"
        )

        self.assert_pcs_success(
            "stonith show --full",
            outdent(
                """\
                 Resource: test (class=stonith type=fence_apc)
                  Attributes: ipaddr=i login=l
                  Operations: monitor interval=60s (test-monitor-interval-60s)
                """
            )
        )

        self.assert_pcs_fail(
            "stonith update test action=a",
            "Error: stonith option 'action' is deprecated and should not be"
                " used, use pcmk_off_action, pcmk_reboot_action instead,"
                " use --force to override\n"
        )

        self.assert_pcs_success(
            "stonith update test action=a --force",
            "Warning: stonith option 'action' is deprecated and should not be"
                " used, use pcmk_off_action, pcmk_reboot_action instead\n"
        )

        self.assert_pcs_success(
            "stonith show --full",
            outdent(
                """\
                 Resource: test (class=stonith type=fence_apc)
                  Attributes: action=a ipaddr=i login=l
                  Operations: monitor interval=60s (test-monitor-interval-60s)
                """
            )
        )

        self.assert_pcs_success(
            "stonith update test action="
        )

        self.assert_pcs_success(
            "stonith show --full",
            outdent(
                """\
                 Resource: test (class=stonith type=fence_apc)
                  Attributes: ipaddr=i login=l
                  Operations: monitor interval=60s (test-monitor-interval-60s)
                """
            )
        )

    def test_stonith_compute_evacuate_always_allowed_parameters(self):
        self.assert_pcs_success(
            "stonith create test1 fence_compute auth_url=test1 project_domain=val1 project-domain=val2 user_domain=val3 user-domain=val4 compute_domain=val5 compute-domain=val6",
        )
        self.assert_pcs_success(
            "stonith show --full",
            outdent(
                """\
                 Resource: test1 (class=stonith type=fence_compute)
                  Attributes: auth_url=test1 compute-domain=val6 compute_domain=val5 project-domain=val2 project_domain=val1 user-domain=val4 user_domain=val3
                  Operations: monitor interval=60s (test1-monitor-interval-60s)
                """
            )
        )
        self.assert_pcs_success(
            "stonith create test2 fence_evacuate auth_url=test2 project_domain=val0 project-domain=val1 user_domain=val2 user-domain=val3 compute_domain=val4 compute-domain=val5",
        )
        self.assert_pcs_success(
            "stonith show --full",
            outdent(
                """\
                 Resource: test1 (class=stonith type=fence_compute)
                  Attributes: auth_url=test1 compute-domain=val6 compute_domain=val5 project-domain=val2 project_domain=val1 user-domain=val4 user_domain=val3
                  Operations: monitor interval=60s (test1-monitor-interval-60s)
                 Resource: test2 (class=stonith type=fence_evacuate)
                  Attributes: auth_url=test2 compute-domain=val5 compute_domain=val4 project-domain=val1 project_domain=val0 user-domain=val3 user_domain=val2
                  Operations: monitor interval=60s (test2-monitor-interval-60s)
                """
            )
        )
        self.assert_pcs_success(
            "stonith update test1 auth_url=new0 project_domain=new1 project-domain=new2 user_domain=new3 user-domain=new4 compute_domain=new5 compute-domain=new6",
        )
        self.assert_pcs_success(
            "stonith show --full",
            outdent(
                """\
                 Resource: test1 (class=stonith type=fence_compute)
                  Attributes: auth_url=new0 compute-domain=new6 compute_domain=new5 project-domain=new2 project_domain=new1 user-domain=new4 user_domain=new3
                  Operations: monitor interval=60s (test1-monitor-interval-60s)
                 Resource: test2 (class=stonith type=fence_evacuate)
                  Attributes: auth_url=test2 compute-domain=val5 compute_domain=val4 project-domain=val1 project_domain=val0 user-domain=val3 user_domain=val2
                  Operations: monitor interval=60s (test2-monitor-interval-60s)
                """
            )
        )
        self.assert_pcs_success(
            "stonith update test2 auth_url=new1 project_domain=new2 project-domain=new3 user_domain=new4 user-domain=new5 compute_domain=new6 compute-domain=new7",
        )
        self.assert_pcs_success(
            "stonith show --full",
            outdent(
                """\
                 Resource: test1 (class=stonith type=fence_compute)
                  Attributes: auth_url=new0 compute-domain=new6 compute_domain=new5 project-domain=new2 project_domain=new1 user-domain=new4 user_domain=new3
                  Operations: monitor interval=60s (test1-monitor-interval-60s)
                 Resource: test2 (class=stonith type=fence_evacuate)
                  Attributes: auth_url=new1 compute-domain=new7 compute_domain=new6 project-domain=new3 project_domain=new2 user-domain=new5 user_domain=new4
                  Operations: monitor interval=60s (test2-monitor-interval-60s)
                """
            )
        )

    def testStonithFenceConfirm(self):
        output, returnVal = pcs(temp_cib, "stonith fence blah blah")
        assert returnVal == 1
        assert output == "Error: must specify one (and only one) node to fence\n"

        output, returnVal = pcs(temp_cib, "stonith confirm blah blah")
        assert returnVal == 1
        assert output == "Error: must specify one (and only one) node to confirm fenced\n"

    def testPcmkHostList(self):
        self.assert_pcs_success(
            "stonith create F1 fence_apc 'pcmk_host_list=nodea nodeb' --force",
            "Warning: required stonith options 'ipaddr', 'login' are missing\n"
        )

        self.assert_pcs_success("stonith show F1", outdent(
            """\
             Resource: F1 (class=stonith type=fence_apc)
              Attributes: pcmk_host_list="nodea nodeb"
              Operations: monitor interval=60s (F1-monitor-interval-60s)
            """
        ))

    def testPcmkHostAllowsMissingPort(self):
        # Test that port is not required when pcmk_host_argument or
        # pcmk_host_list or pcmk_host_map is specified
        # Port is temporarily an optional parameter. Once we are getting
        # metadata from pacemaker, this will be reviewed and fixed.
        self.assert_pcs_success(
            'stonith create apc-1 fence_apc ipaddr="ip" login="apc"'
        )

        self.assert_pcs_success(
            'stonith create apc-2 fence_apc ipaddr="ip" login="apc" pcmk_host_map="buzz-01:1;buzz-02:2"'
        )

        self.assert_pcs_success(
            'stonith create apc-3 fence_apc ipaddr="ip" login="apc" pcmk_host_list="buzz-01,buzz-02"'
        )

        self.assert_pcs_success(
            'stonith create apc-4 fence_apc ipaddr="ip" login="apc" pcmk_host_argument="buzz-01"'
        )

    def testStonithDeleteRemovesLevel(self):
        shutil.copy(rc("cib-empty-with3nodes.xml"), temp_cib)

        self.assert_pcs_success(
            "stonith create n1-ipmi fence_apc --force",
            "Warning: required stonith options 'ipaddr', 'login' are missing\n"
        )
        self.assert_pcs_success(
            "stonith create n2-ipmi fence_apc --force",
            "Warning: required stonith options 'ipaddr', 'login' are missing\n"
        )
        self.assert_pcs_success(
            "stonith create n1-apc1 fence_apc --force",
            "Warning: required stonith options 'ipaddr', 'login' are missing\n"
        )
        self.assert_pcs_success(
            "stonith create n1-apc2 fence_apc --force",
            "Warning: required stonith options 'ipaddr', 'login' are missing\n"
        )
        self.assert_pcs_success(
            "stonith create n2-apc1 fence_apc --force",
            "Warning: required stonith options 'ipaddr', 'login' are missing\n"
        )
        self.assert_pcs_success(
            "stonith create n2-apc2 fence_apc --force",
            "Warning: required stonith options 'ipaddr', 'login' are missing\n"
        )
        self.assert_pcs_success(
            "stonith create n2-apc3 fence_apc --force",
            "Warning: required stonith options 'ipaddr', 'login' are missing\n"
        )
        self.assert_pcs_success_all([
            "stonith level add 1 rh7-1 n1-ipmi",
            "stonith level add 2 rh7-1 n1-apc1,n1-apc2,n2-apc2",
            "stonith level add 1 rh7-2 n2-ipmi",
            "stonith level add 2 rh7-2 n2-apc1,n2-apc2,n2-apc3",
        ])

        self.assert_pcs_success("stonith", outdent(
            """\
             n1-ipmi\t(stonith:fence_apc):\tStopped
             n2-ipmi\t(stonith:fence_apc):\tStopped
             n1-apc1\t(stonith:fence_apc):\tStopped
             n1-apc2\t(stonith:fence_apc):\tStopped
             n2-apc1\t(stonith:fence_apc):\tStopped
             n2-apc2\t(stonith:fence_apc):\tStopped
             n2-apc3\t(stonith:fence_apc):\tStopped
             Target: rh7-1
               Level 1 - n1-ipmi
               Level 2 - n1-apc1,n1-apc2,n2-apc2
             Target: rh7-2
               Level 1 - n2-ipmi
               Level 2 - n2-apc1,n2-apc2,n2-apc3
            """
        ))

        self.assert_pcs_success(
            "stonith delete n2-apc2",
            "Deleting Resource - n2-apc2\n"
        )

        self.assert_pcs_success("stonith", outdent(
            """\
             n1-ipmi\t(stonith:fence_apc):\tStopped
             n2-ipmi\t(stonith:fence_apc):\tStopped
             n1-apc1\t(stonith:fence_apc):\tStopped
             n1-apc2\t(stonith:fence_apc):\tStopped
             n2-apc1\t(stonith:fence_apc):\tStopped
             n2-apc3\t(stonith:fence_apc):\tStopped
             Target: rh7-1
               Level 1 - n1-ipmi
               Level 2 - n1-apc1,n1-apc2
             Target: rh7-2
               Level 1 - n2-ipmi
               Level 2 - n2-apc1,n2-apc3
            """
        ))

        self.assert_pcs_success(
            "stonith delete n2-apc1",
            "Deleting Resource - n2-apc1\n"
        )

        self.assert_pcs_success("stonith", outdent(
            """\
             n1-ipmi\t(stonith:fence_apc):\tStopped
             n2-ipmi\t(stonith:fence_apc):\tStopped
             n1-apc1\t(stonith:fence_apc):\tStopped
             n1-apc2\t(stonith:fence_apc):\tStopped
             n2-apc3\t(stonith:fence_apc):\tStopped
             Target: rh7-1
               Level 1 - n1-ipmi
               Level 2 - n1-apc1,n1-apc2
             Target: rh7-2
               Level 1 - n2-ipmi
               Level 2 - n2-apc3
            """
        ))

        self.assert_pcs_success(
            "stonith delete n2-apc3",
            "Deleting Resource - n2-apc3\n"
        )

        self.assert_pcs_success("stonith", outdent(
            """\
             n1-ipmi\t(stonith:fence_apc):\tStopped
             n2-ipmi\t(stonith:fence_apc):\tStopped
             n1-apc1\t(stonith:fence_apc):\tStopped
             n1-apc2\t(stonith:fence_apc):\tStopped
             Target: rh7-1
               Level 1 - n1-ipmi
               Level 2 - n1-apc1,n1-apc2
             Target: rh7-2
               Level 1 - n2-ipmi
            """
        ))

        self.assert_pcs_success(
            "resource delete n1-apc1",
            "Deleting Resource - n1-apc1\n"
        )

        self.assert_pcs_success("stonith", outdent(
            """\
             n1-ipmi\t(stonith:fence_apc):\tStopped
             n2-ipmi\t(stonith:fence_apc):\tStopped
             n1-apc2\t(stonith:fence_apc):\tStopped
             Target: rh7-1
               Level 1 - n1-ipmi
               Level 2 - n1-apc2
             Target: rh7-2
               Level 1 - n2-ipmi
            """
        ))

        self.assert_pcs_success("resource delete n1-apc2", outdent(
            """\
            Deleting Resource - n1-apc2
            """
        ))

        self.assert_pcs_success("stonith", outdent(
            """\
             n1-ipmi\t(stonith:fence_apc):\tStopped
             n2-ipmi\t(stonith:fence_apc):\tStopped
             Target: rh7-1
               Level 1 - n1-ipmi
             Target: rh7-2
               Level 1 - n2-ipmi
            """
        ))

    def testNoStonithWarning(self):
        # pylint: disable=unused-variable
        o,r = pcs(temp_cib, "status")
        assert "No stonith devices and stonith-enabled is not false" in o

        self.assert_pcs_success(
            "stonith create test_stonith fence_apc ipaddr=ip login=lgn pcmk_host_argument=node1"
        )

        o,r = pcs(temp_cib, "status")
        assert "No stonith devices and stonith-enabled is not false" not in o

        self.assert_pcs_success(
            "stonith delete test_stonith",
            "Deleting Resource - test_stonith\n"
        )

        self.assert_pcs_success(
            "stonith create test_stonith fence_apc ipaddr=ip login=lgn pcmk_host_argument=node1"
        )

        o,r = pcs(temp_cib, "status")
        assert "No stonith devices and stonith-enabled is not false" not in o


class LevelTestsBase(TestCase, AssertPcsMixin):
    def setUp(self):
        if fencing_level_attribute_supported:
            shutil.copy(rc("cib-empty-2.5-withnodes.xml"), temp_cib)
        else:
            shutil.copy(rc("cib-empty-2.3-withnodes.xml"), temp_cib)
        self.pcs_runner = PcsRunner(temp_cib)
        self.pcs_runner.mock_settings = get_mock_settings("crm_resource_binary")
        self.config = ""
        self.config_lines = []

    def fixture_stonith_resource(self, name):
        self.assert_pcs_success(
            "stonith create {name} fence_apc 'pcmk_host_list=rh7-1 rh7-2', ipaddr=ip login=lgn"
            .format(name=name)
        )

    def fixture_full_configuration(self):
        self.fixture_stonith_resource("F1")
        self.fixture_stonith_resource("F2")
        self.fixture_stonith_resource("F3")

        self.assert_pcs_success("stonith level add 1 rh7-1 F1")
        self.assert_pcs_success("stonith level add 2 rh7-1 F2")
        self.assert_pcs_success("stonith level add 2 rh7-2 F1")
        self.assert_pcs_success("stonith level add 1 rh7-2 F2")
        self.assert_pcs_success("stonith level add 4 regexp%rh7-\d F3")
        self.assert_pcs_success("stonith level add 3 regexp%rh7-\d F2 F1")

        self.config = outdent(
            """\
            Target: rh7-1
              Level 1 - F1
              Level 2 - F2
            Target: rh7-2
              Level 1 - F2
              Level 2 - F1
            Target: rh7-\d
              Level 3 - F2,F1
              Level 4 - F3
            """
        )
        self.config_lines = self.config.splitlines()

        if not fencing_level_attribute_supported:
            return
        self.assert_pcs_success(
            "stonith level add 5 attrib%fencewith=levels1 F3 F2"
        )
        self.assert_pcs_success(
            "stonith level add 6 attrib%fencewith=levels2 F3 F1"
        )
        self.config += outdent(
            """\
            Target: fencewith=levels1
              Level 5 - F3,F2
            Target: fencewith=levels2
              Level 6 - F3,F1
            """)
        self.config_lines = self.config.splitlines()


@skip_unless_fencing_level_supported
class LevelBadCommand(LevelTestsBase):
    def test_success(self):
        self.assert_pcs_fail(
            "stonith level nonsense",
            stdout_start="\nUsage: pcs stonith level ...\n"
        )


@skip_unless_fencing_level_supported
class LevelAddTargetUpgradesCib(LevelTestsBase):
    def setUp(self):
        shutil.copy(rc("cib-empty-withnodes.xml"), temp_cib)
        self.pcs_runner = PcsRunner(temp_cib)

    @skip_unless_fencing_level_attribute_supported
    def test_attribute(self):
        self.fixture_stonith_resource("F1")
        self.assert_pcs_success(
            "stonith level add 1 attrib%fencewith=levels F1",
            "CIB has been upgraded to the latest schema version.\n"
        )
        self.assert_pcs_success(
            "stonith level",
            outdent(
                """\
                Target: fencewith=levels
                  Level 1 - F1
                """
            )
        )

    def test_regexp(self):
        self.fixture_stonith_resource("F1")
        self.assert_pcs_success(
            "stonith level add 1 regexp%node-\d+ F1",
            "CIB has been upgraded to the latest schema version.\n"
        )
        self.assert_pcs_success(
            "stonith level",
            outdent(
                """\
                Target: node-\d+
                  Level 1 - F1
                """
            )
        )


@skip_unless_fencing_level_supported
class LevelAdd(LevelTestsBase):
    def test_not_enough_params(self):
        self.assert_pcs_fail(
            "stonith level add",
            stdout_start="\nUsage: pcs stonith level add...\n"
        )

        self.assert_pcs_fail(
            "stonith level add 1",
            stdout_start="\nUsage: pcs stonith level add...\n"
        )

        self.assert_pcs_fail(
            "stonith level add 1 nodeA",
            stdout_start="\nUsage: pcs stonith level add...\n"
        )

    def test_add_wrong_target_type(self):
        self.assert_pcs_fail(
            "stonith level add 1 error%value F1",
            "Error: 'error' is not an allowed type for 'error%value', "
                "use attrib, node, regexp\n"
        )

    def test_add_bad_level(self):
        self.fixture_stonith_resource("F1")
        self.assert_pcs_fail(
            "stonith level add NaN rh7-1 F1",
            "Error: 'NaN' is not a valid level value, use a positive integer\n"
        )
        self.assert_pcs_fail(
            "stonith level add -10 rh7-1 F1",
            "Error: '-10' is not a valid level value, use a positive integer\n"
        )
        self.assert_pcs_fail(
            "stonith level add 10abc rh7-1 F1",
            "Error: '10abc' is not a valid level value, use a positive integer\n"
        )
        self.assert_pcs_fail(
            "stonith level add 0 rh7-1 F1",
            "Error: '0' is not a valid level value, use a positive integer\n"
        )
        self.assert_pcs_fail(
            "stonith level add 000 rh7-1 F1",
            "Error: '000' is not a valid level value, use a positive integer\n"
        )

    def test_add_bad_device(self):
        self.assert_pcs_fail(
            "stonith level add 1 rh7-1 dev@ce",
            "Error: invalid device id 'dev@ce', '@' is not a valid character "
                "for a device id\n"
        )

    def test_add_more_errors(self):
        self.assert_pcs_fail(
            "stonith level add x rh7-X F0 dev@ce",
            outdent(
                """\
                Error: 'x' is not a valid level value, use a positive integer
                Error: Node 'rh7-X' does not appear to exist in configuration, use --force to override
                Error: invalid device id 'dev@ce', '@' is not a valid character for a device id
                Error: Stonith resource(s) 'F0' do not exist, use --force to override
                """
            )
        )

        self.assert_pcs_fail(
            "stonith level add x rh7-X F0 dev@ce --force",
            outdent(
                """\
                Error: 'x' is not a valid level value, use a positive integer
                Error: invalid device id 'dev@ce', '@' is not a valid character for a device id
                Warning: Node 'rh7-X' does not appear to exist in configuration
                Warning: Stonith resource(s) 'F0' do not exist
                """
            )
        )

    def test_add_level_leading_zero(self):
        self.fixture_stonith_resource("F1")
        self.assert_pcs_success("stonith level add 0002 rh7-1 F1")
        self.assert_pcs_success(
            "stonith level",
            outdent(
                """\
                Target: rh7-1
                  Level 2 - F1
                """
            )
        )

    def test_add_node(self):
        self.fixture_stonith_resource("F1")
        self.assert_pcs_success("stonith level add 1 rh7-1 F1")
        self.assert_pcs_success(
            "stonith level",
            outdent(
                """\
                Target: rh7-1
                  Level 1 - F1
                """
            )
        )

        self.assert_pcs_fail(
            "stonith level add 1 rh7-1 F1",
            "Error: Fencing level for 'rh7-1' at level '1' with device(s) "
                "'F1' already exists\n"
        )
        self.assert_pcs_success(
            "stonith level",
            outdent(
                """\
                Target: rh7-1
                  Level 1 - F1
                """
            )
        )

    def test_add_node_pattern(self):
        self.fixture_stonith_resource("F1")
        self.assert_pcs_success("stonith level add 1 regexp%rh7-\d F1")
        self.assert_pcs_success(
            "stonith level",
            outdent(
                """\
                Target: rh7-\d
                  Level 1 - F1
                """
            )
        )

        self.assert_pcs_fail(
            "stonith level add 1 regexp%rh7-\d F1",
            "Error: Fencing level for 'rh7-\d' at level '1' with device(s) "
                "'F1' already exists\n"
        )
        self.assert_pcs_success(
            "stonith level",
            outdent(
                """\
                Target: rh7-\d
                  Level 1 - F1
                """
            )
        )

    @skip_unless_fencing_level_attribute_supported
    def test_add_node_attribute(self):
        self.fixture_stonith_resource("F1")
        self.assert_pcs_success(
            "stonith level add 1 attrib%fencewith=levels F1"
        )
        self.assert_pcs_success(
            "stonith level",
            outdent(
                """\
                Target: fencewith=levels
                  Level 1 - F1
                """
            )
        )

        self.assert_pcs_fail(
            "stonith level add 1 attrib%fencewith=levels F1",
            "Error: Fencing level for 'fencewith=levels' at level '1' with "
                "device(s) 'F1' already exists\n"
        )
        self.assert_pcs_success(
            "stonith level",
            outdent(
                """\
                Target: fencewith=levels
                  Level 1 - F1
                """
            )
        )

    def test_add_more_devices(self):
        self.fixture_stonith_resource("F1")
        self.fixture_stonith_resource("F2")
        self.assert_pcs_success("stonith level add 1 rh7-1 F1 F2")
        self.assert_pcs_success(
            "stonith level",
            outdent(
                """\
                Target: rh7-1
                  Level 1 - F1,F2
                """
            )
        )

    def test_add_more_devices_old_syntax(self):
        self.fixture_stonith_resource("F1")
        self.fixture_stonith_resource("F2")
        self.fixture_stonith_resource("F3")

        self.assert_pcs_success("stonith level add 1 rh7-1 F1,F2")
        self.assert_pcs_success(
            "stonith level",
            outdent(
                """\
                Target: rh7-1
                  Level 1 - F1,F2
                """
            )
        )

        self.assert_pcs_success("stonith level add 2 rh7-1 F1,F2 F3")
        self.assert_pcs_success(
            "stonith level",
            outdent(
                """\
                Target: rh7-1
                  Level 1 - F1,F2
                  Level 2 - F1,F2,F3
                """
            )
        )

        self.assert_pcs_success("stonith level add 3 rh7-1 F1 F2,F3")
        self.assert_pcs_success(
            "stonith level",
            outdent(
                """\
                Target: rh7-1
                  Level 1 - F1,F2
                  Level 2 - F1,F2,F3
                  Level 3 - F1,F2,F3
                """
            )
        )

    def test_nonexistant_node(self):
        self.fixture_stonith_resource("F1")
        self.assert_pcs_fail(
            "stonith level add 1 rh7-X F1",
            "Error: Node 'rh7-X' does not appear to exist in configuration"
                ", use --force to override\n"
        )
        self.assert_pcs_success(
            "stonith level add 1 rh7-X F1 --force",
            "Warning: Node 'rh7-X' does not appear to exist in configuration\n"
        )
        self.assert_pcs_success(
            "stonith level",
            outdent(
                """\
                Target: rh7-X
                  Level 1 - F1
                """
            )
        )

    def test_nonexistant_device(self):
        self.assert_pcs_fail(
            "stonith level add 1 rh7-1 F1",
            "Error: Stonith resource(s) 'F1' do not exist"
                ", use --force to override\n"
        )
        self.assert_pcs_success(
            "stonith level add 1 rh7-1 F1 --force",
            "Warning: Stonith resource(s) 'F1' do not exist\n"
        )
        self.assert_pcs_success(
            "stonith level",
            outdent(
                """\
                Target: rh7-1
                  Level 1 - F1
                """
            )
        )

    def test_nonexistant_devices(self):
        self.fixture_stonith_resource("F1")
        self.assert_pcs_fail(
            "stonith level add 1 rh7-1 F1 F2 F3",
            "Error: Stonith resource(s) 'F2', 'F3' do not exist"
                ", use --force to override\n"
        )
        self.assert_pcs_success(
            "stonith level add 1 rh7-1 F1 F2 F3 --force",
            "Warning: Stonith resource(s) 'F2', 'F3' do not exist\n"
        )
        self.assert_pcs_success(
            "stonith level",
            outdent(
                """\
                Target: rh7-1
                  Level 1 - F1,F2,F3
                """
            )
        )


@skip_unless_fencing_level_supported
class LevelConfig(LevelTestsBase):
    full_config = outdent(
        """\
        Cluster Name: test99
        Corosync Nodes:
         rh7-1 rh7-2
        Pacemaker Nodes:
         rh7-1 rh7-2

        Resources:

        Stonith Devices:{devices}
        Fencing Levels:{levels}

        Location Constraints:
        Ordering Constraints:
        Colocation Constraints:
        Ticket Constraints:

        Alerts:
         No alerts defined

        Resources Defaults:
         No defaults set
        Operations Defaults:
         No defaults set

        Cluster Properties:

        Quorum:
          Options:
        """
    )

    def test_empty(self):
        self.assert_pcs_success("stonith level config", "")
        self.assert_pcs_success("stonith level", "")
        self.assert_pcs_success("stonith", "NO stonith devices configured\n")
        self.assert_pcs_success(
            "config",
            self.full_config.format(devices="", levels="")
        )

    def test_all_posibilities(self):
        self.fixture_full_configuration()
        self.assert_pcs_success("stonith level config", self.config)
        self.assert_pcs_success("stonith level", self.config)
        self.assert_pcs_success(
            "stonith",
            outdent(
                """\
                 F1\t(stonith:fence_apc):\tStopped
                 F2\t(stonith:fence_apc):\tStopped
                 F3\t(stonith:fence_apc):\tStopped
                """
            ) + "\n".join(indent(self.config_lines, 1)) + "\n"
        )
        self.assert_pcs_success(
            "config",
            self.full_config.format(
                devices="""
 Resource: F1 (class=stonith type=fence_apc)
  Attributes: ipaddr=ip login=lgn pcmk_host_list="rh7-1 rh7-2,"
  Operations: monitor interval=60s (F1-monitor-interval-60s)
 Resource: F2 (class=stonith type=fence_apc)
  Attributes: ipaddr=ip login=lgn pcmk_host_list="rh7-1 rh7-2,"
  Operations: monitor interval=60s (F2-monitor-interval-60s)
 Resource: F3 (class=stonith type=fence_apc)
  Attributes: ipaddr=ip login=lgn pcmk_host_list="rh7-1 rh7-2,"
  Operations: monitor interval=60s (F3-monitor-interval-60s)\
""",
                levels=("\n" + "\n".join(indent(self.config_lines, 2)))
            )
        )


@skip_unless_fencing_level_supported
class LevelClear(LevelTestsBase):
    def setUp(self):
        super(LevelClear, self).setUp()
        self.fixture_full_configuration()

    def test_clear_all(self):
        self.assert_pcs_success("stonith level clear")
        self.assert_pcs_success("stonith level config", "")

    def test_clear_nonexistant_node_or_device(self):
        self.assert_pcs_success("stonith level clear rh-X")
        self.assert_pcs_success("stonith level config", self.config)

    def test_clear_nonexistant_devices(self):
        self.assert_pcs_success("stonith level clear F1,F5")
        self.assert_pcs_success("stonith level config", self.config)

    def test_pattern_is_not_device(self):
        self.assert_pcs_success("stonith level clear regexp%F1")
        self.assert_pcs_success("stonith level config", self.config)

    def test_clear_node(self):
        self.assert_pcs_success("stonith level clear rh7-1")
        self.assert_pcs_success(
            "stonith level config",
            "\n".join(self.config_lines[3:]) + "\n"
        )

    def test_clear_pattern(self):
        self.assert_pcs_success("stonith level clear regexp%rh7-\d")
        self.assert_pcs_success(
            "stonith level config",
            "\n".join(self.config_lines[:6] + self.config_lines[9:]) + "\n"
        )

    @skip_unless_fencing_level_attribute_supported
    def test_clear_attribute(self):
        self.assert_pcs_success("stonith level clear attrib%fencewith=levels2")
        self.assert_pcs_success(
            "stonith level config",
            "\n".join(self.config_lines[:11]) + "\n"
        )

    def test_clear_device(self):
        self.assert_pcs_success("stonith level clear F1")
        self.assert_pcs_success(
            "stonith level config",
            "\n".join(
                self.config_lines[0:1]
                +
                self.config_lines[2:5]
                +
                self.config_lines[6:]
            ) + "\n"
        )

    def test_clear_devices(self):
        self.assert_pcs_success("stonith level clear F2,F1")
        self.assert_pcs_success(
            "stonith level config",
            "\n".join(self.config_lines[:7] + self.config_lines[8:]) + "\n"
        )


@skip_unless_fencing_level_supported
class LevelRemove(LevelTestsBase):
    def setUp(self):
        super(LevelRemove, self).setUp()
        self.fixture_full_configuration()

    def test_nonexisting_level_node_device(self):
        self.assert_pcs_fail(
            "stonith level remove 1 rh7-1 F3",
            outdent(
                """\
                Error: Fencing level for 'rh7-1' at level '1' with device(s) 'F3' does not exist
                Error: Fencing level at level '1' with device(s) 'rh7-1,F3' does not exist
                """
            )
        )
        self.assert_pcs_success("stonith level config", self.config)

    def test_nonexisting_level_pattern_device(self):
        self.assert_pcs_fail(
            "stonith level remove 1 regexp%rh7-\d F3",
            "Error: Fencing level for 'rh7-\d' at level '1' with device(s) 'F3' does not exist\n"
        )
        self.assert_pcs_success("stonith level config", self.config)

        self.assert_pcs_fail(
            "stonith level remove 3 regexp%rh7-\d F1,F2",
            "Error: Fencing level for 'rh7-\d' at level '3' with device(s) 'F1,F2' does not exist\n"
        )
        self.assert_pcs_success("stonith level config", self.config)

    def test_nonexisting_level(self):
        self.assert_pcs_fail(
            "stonith level remove 9",
            "Error: Fencing level at level '9' does not exist\n"
        )
        self.assert_pcs_success("stonith level config", self.config)

    def test_remove_level(self):
        self.assert_pcs_success("stonith level remove 1")
        self.assert_pcs_success(
            "stonith level config",
            "\n".join(
                self.config_lines[0:1]
                +
                self.config_lines[2:4]
                +
                self.config_lines[5:]
            ) + "\n"
        )

    def test_remove_level_node(self):
        self.assert_pcs_success("stonith level remove 1 rh7-2")
        self.assert_pcs_success(
            "stonith level config",
            "\n".join(self.config_lines[:4] + self.config_lines[5:]) + "\n"
        )

    def test_remove_level_pattern(self):
        self.assert_pcs_success("stonith level remove 3 regexp%rh7-\d")
        self.assert_pcs_success(
            "stonith level config",
            "\n".join(self.config_lines[:7] + self.config_lines[8:]) + "\n"
        )

    @skip_unless_fencing_level_attribute_supported
    def test_remove_level_attrib(self):
        self.assert_pcs_success(
            "stonith level remove 6 attrib%fencewith=levels2"
        )
        self.assert_pcs_success(
            "stonith level config",
            "\n".join(self.config_lines[:11]) + "\n"
        )

    def test_remove_level_device(self):
        self.assert_pcs_success("stonith level remove 1 F2")
        self.assert_pcs_success(
            "stonith level config",
            "\n".join(self.config_lines[:4] + self.config_lines[5:]) + "\n"
        )

    def test_remove_level_devices(self):
        self.assert_pcs_success("stonith level remove 3 F2 F1")
        self.assert_pcs_success(
            "stonith level config",
            "\n".join(self.config_lines[:7] + self.config_lines[8:]) + "\n"
        )

    def test_remove_level_devices_old_syntax(self):
        self.assert_pcs_success("stonith level remove 3 F2,F1")
        self.assert_pcs_success(
            "stonith level config",
            "\n".join(self.config_lines[:7] + self.config_lines[8:]) + "\n"
        )

    def test_remove_level_node_device(self):
        self.assert_pcs_success("stonith level remove 1 rh7-2 F2")
        self.assert_pcs_success(
            "stonith level config",
            "\n".join(self.config_lines[:4] + self.config_lines[5:]) + "\n"
        )

    def test_remove_level_pattern_device(self):
        self.assert_pcs_success("stonith level remove 3 regexp%rh7-\d F2 F1")
        self.assert_pcs_success(
            "stonith level config",
            "\n".join(self.config_lines[:7] + self.config_lines[8:]) + "\n"
        )

    @skip_unless_fencing_level_attribute_supported
    def test_remove_level_attrib_device(self):
        self.assert_pcs_success(
            "stonith level remove 6 attrib%fencewith=levels2 F3 F1"
        )
        self.assert_pcs_success(
            "stonith level config",
            "\n".join(self.config_lines[:11]) + "\n"
        )


@skip_unless_fencing_level_supported
class LevelVerify(LevelTestsBase):
    def test_success(self):
        self.fixture_full_configuration()
        self.assert_pcs_success("stonith level verify", "")

    def test_errors(self):
        self.fixture_stonith_resource("F1")

        self.assert_pcs_success("stonith level add 1 rh7-1 F1")
        self.assert_pcs_success(
            "stonith level add 2 rh7-1 FX --force",
            "Warning: Stonith resource(s) 'FX' do not exist\n"
        )
        self.assert_pcs_success(
            "stonith level add 1 rh7-X FX --force",
            outdent(
                """\
                Warning: Node 'rh7-X' does not appear to exist in configuration
                Warning: Stonith resource(s) 'FX' do not exist
                """
            )
        )
        self.assert_pcs_success(
            "stonith level add 2 rh7-Y FY --force",
            outdent(
                """\
                Warning: Node 'rh7-Y' does not appear to exist in configuration
                Warning: Stonith resource(s) 'FY' do not exist
                """
            )
        )
        self.assert_pcs_success(
            "stonith level add 4 regexp%rh7-\d FX --force",
            "Warning: Stonith resource(s) 'FX' do not exist\n"
        )
        self.assert_pcs_success(
            "stonith level add 3 regexp%rh7-\d FY FZ --force",
            "Warning: Stonith resource(s) 'FY', 'FZ' do not exist\n"
        )

        self.assert_pcs_fail(
            "stonith level verify",
            outdent(
                """\
                Error: Stonith resource(s) 'FX', 'FY', 'FZ' do not exist
                Error: Node 'rh7-X' does not appear to exist in configuration
                Error: Node 'rh7-Y' does not appear to exist in configuration
                """
            )
        )
