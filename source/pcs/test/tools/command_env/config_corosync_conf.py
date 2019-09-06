from __future__ import (
    absolute_import,
    division,
    print_function,
)

from pcs.test.tools.command_env.mock_get_local_corosync_conf import Call
from pcs.lib.corosync.config_facade import ConfigFacade
from pcs.lib.corosync.config_parser import Section
from pcs.test.tools.misc import get_test_resource as rc

class CorosyncConf(object):
    def __init__(self, call_collection):
        self.__calls = call_collection

    def load_content(self, content, name="corosync_conf.load_content"):
        self.__calls.place(name, Call(content))

    def load(
        self, node_name_list=None, name="corosync_conf.load",
        filename="corosync.conf", auto_tie_breaker=None
    ):
        content = open(rc(filename)).read()
        corosync_conf = None
        if node_name_list:
            corosync_conf = ConfigFacade.from_string(content).config
            for nodelist in corosync_conf.get_sections(name="nodelist"):
                corosync_conf.del_section(nodelist)

            nodelist_section = Section("nodelist")
            corosync_conf.add_section(nodelist_section)
            for i, node_name in enumerate(node_name_list):
                node_section = Section("node")
                node_section.add_attribute("ring0_addr", node_name)
                node_section.add_attribute("nodeid", i)
                nodelist_section.add_section(node_section)


        if auto_tie_breaker is not None:
            corosync_conf = (
                corosync_conf if corosync_conf
                else ConfigFacade.from_string(content).config
            )
            for quorum in corosync_conf.get_sections(name="quorum"):
                quorum.set_attribute(
                    "auto_tie_breaker",
                    "1" if auto_tie_breaker else  "0"
                )

        if corosync_conf:
            content = corosync_conf.export()

        self.load_content(content, name)
