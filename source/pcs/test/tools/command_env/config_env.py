from __future__ import (
    absolute_import,
    division,
    print_function,
)

from pcs.test.tools.command_env.mock_push_cib import Call as PushCibCall
from pcs.test.tools.command_env.mock_push_corosync_conf import (
    Call as PushCorosyncConfCall,
)
from pcs.test.tools.fixture_cib import modify_cib


class EnvConfig(object):
    def __init__(self, call_collection):
        self.__calls = call_collection
        self.__cib_data = None
        self.__cib_tempfile = None
        self.__corosync_conf_data = None
        self.__booth = None


    def set_cib_data(self, cib_data, cib_tempfile="/fake/tmp/file"):
        self.__cib_data = cib_data
        self.__cib_tempfile = cib_tempfile


    @property
    def cib_data(self):
        return self.__cib_data

    @property
    def cib_tempfile(self):
        return self.__cib_tempfile

    def set_booth(self, booth):
        self.__booth = booth

    @property
    def booth(self):
        return self.__booth

    def set_corosync_conf_data(self, corosync_conf_data):
        self.__corosync_conf_data = corosync_conf_data

    @property
    def corosync_conf_data(self):
        return self.__corosync_conf_data

    def push_cib(
        self, modifiers=None, name="env.push_cib",
        load_key="runner.cib.load", wait=False, exception=None, instead=None,
        **modifier_shortcuts
    ):
        """
        Create call for pushing cib.

        string name -- key of the call
        list of callable modifiers -- every callable takes etree.Element and
            returns new etree.Element with desired modification.
        string load_key -- key of a call from which stdout can be cib taken
        string|False wait -- wait for pacemaker idle
        Exception|None exception -- exception that should raise env.push_cib
        string instead -- key of call instead of which this new call is to be
            placed
        dict modifier_shortcuts -- a new modifier is generated from each
            modifier shortcut.
            As key there can be keys of MODIFIER_GENERATORS.
            Value is passed into appropriate generator from MODIFIER_GENERATORS.
            For details see pcs.test.tools.fixture_cib (mainly the variable
            MODIFIER_GENERATORS - please refer it when you are adding params
            here)
        """
        cib_xml = modify_cib(
            self.__calls.get(load_key).stdout,
            modifiers,
            **modifier_shortcuts
        )
        self.__calls.place(
            name,
            PushCibCall(cib_xml, wait=wait, exception=exception),
            instead=instead
        )

    def push_cib_custom(
        self, name="env.push_cib_custom", custom_cib=None, wait=False,
        exception=None, instead=None
    ):
        self.__calls.place(
            name,
            PushCibCall(
                custom_cib, custom_cib=True, wait=wait, exception=exception
            ),
            instead=instead
        )

    def push_corosync_conf(
        self, name="env.push_corosync_conf", corosync_conf_text="",
        skip_offline_targets=False, before=None, instead=None
    ):
        self.__calls.place(
            name,
            PushCorosyncConfCall(corosync_conf_text, skip_offline_targets),
            instead=instead,
            before=before
        )
