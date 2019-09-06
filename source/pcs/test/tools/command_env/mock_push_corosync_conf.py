from __future__ import (
    absolute_import,
    division,
    print_function,
)

from pcs.lib.corosync.config_facade import ConfigFacade
from pcs.test.tools.assertions import prepare_diff

CALL_TYPE_PUSH_COROSYNC_CONF = "CALL_TYPE_PUSH_COROSYNC_CONF"

class Call(object):
    type = CALL_TYPE_PUSH_COROSYNC_CONF

    def __init__(self, corosync_conf_text, skip_offline_targets):
        self.corosync_conf_text = corosync_conf_text
        self.skip_offline_targets = skip_offline_targets

    def __repr__(self):
        return str("<CorosyncConfPush skip-offline='{0}'>").format(
            self.skip_offline_targets
        )

def get_push_corosync_conf(call_queue):
    def push_corosync_conf(
        lib_env, corosync_conf_facade, skip_offline_nodes=False
    ):
        i, expected_call = call_queue.take(CALL_TYPE_PUSH_COROSYNC_CONF)

        if not isinstance(corosync_conf_facade, ConfigFacade):
            raise AssertionError(
                (
                    "Trying to call env.push_corosync_conf (call no. {0}) with"
                    " {1} instead of lib.corosync.config_facade.ConfigFacade"
                ).format(i, type(corosync_conf_facade))
            )

        to_push = corosync_conf_facade.config.export()
        if to_push != expected_call.corosync_conf_text:
            raise AssertionError(
                "Trying to call env.push_corosync_conf but the pushed "
                "corosync.conf is not as expected:\n{0}".format(
                    prepare_diff(to_push, expected_call.corosync_conf_text)
                )
            )

    return push_corosync_conf

def is_push_corosync_conf_call_in(call_queue):
    return call_queue.has_type(CALL_TYPE_PUSH_COROSYNC_CONF)
