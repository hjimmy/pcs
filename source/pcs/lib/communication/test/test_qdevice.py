from __future__ import (
    absolute_import,
    division,
    print_function,
)

from pcs.test.tools.pcs_unittest import TestCase

class Stop(TestCase):
    """
    tested in:
        pcs.lib.commands.test.test_quorum.RemoveDeviceNetTest
        pcs.lib.test.test_env.PushCorosyncConfLiveWithQdeviceTest
    """

class Start(TestCase):
    """
    tested in:
        pcs.lib.commands.test.test_quorum.AddDeviceNetTest
        pcs.lib.test.test_env.PushCorosyncConfLiveWithQdeviceTest
    """

class Enable(TestCase):
    """
    tested in:
        pcs.lib.commands.test.test_quorum.AddDeviceNetTest
    """

class Disable(TestCase):
    """
    tested in:
        pcs.lib.commands.test.test_quorum.RemoveDeviceNetTest
    """
