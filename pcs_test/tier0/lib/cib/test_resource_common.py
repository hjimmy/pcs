from unittest import TestCase
from lxml import etree

from pcs_test.tools.assertions import (
    assert_report_item_list_equal,
    assert_xml_equal,
)
from pcs_test.tools import fixture
from pcs_test.tools.xml import etree_to_str

from pcs.common import report_codes
from pcs.lib.cib.resource import common
from pcs.lib.cib.tools import IdProvider


fixture_cib = etree.fromstring("""
    <resources>
        <primitive id="A" />
        <clone id="B-clone">
            <primitive id="B" />
        </clone>
        <master id="C-master">
            <primitive id="C" />
        </master>
        <group id="D">
            <primitive id="D1" />
            <primitive id="D2" />
        </group>
        <clone id="E-clone">
            <group id="E">
                <primitive id="E1" />
                <primitive id="E2" />
            </group>
        </clone>
        <master id="F-master">
            <group id="F">
                <primitive id="F1" />
                <primitive id="F2" />
            </group>
        </master>
        <bundle id="G-bundle" />
        <bundle id="H-bundle">
            <primitive id="H" />
        </bundle>
    </resources>
""")


class AreMetaDisabled(TestCase):
    def test_detect_is_disabled(self):
        self.assertTrue(common.are_meta_disabled({"target-role": "Stopped"}))
        self.assertTrue(common.are_meta_disabled({"target-role": "stopped"}))

    def test_detect_is_not_disabled(self):
        self.assertFalse(common.are_meta_disabled({}))
        self.assertFalse(common.are_meta_disabled({"target-role": "any"}))


class IsCloneDeactivatedByMeta(TestCase):
    def assert_is_disabled(self, meta_attributes):
        self.assertTrue(common.is_clone_deactivated_by_meta(meta_attributes))

    def assert_is_not_disabled(self, meta_attributes):
        self.assertFalse(common.is_clone_deactivated_by_meta(meta_attributes))

    def test_detect_is_disabled(self):
        self.assert_is_disabled({"target-role": "Stopped"})
        self.assert_is_disabled({"target-role": "stopped"})
        self.assert_is_disabled({"clone-max": "0"})
        self.assert_is_disabled({"clone-max": "00"})
        self.assert_is_disabled({"clone-max": 0})
        self.assert_is_disabled({"clone-node-max": "0"})
        self.assert_is_disabled({"clone-node-max": "abc1"})

    def test_detect_is_not_disabled(self):
        self.assert_is_not_disabled({})
        self.assert_is_not_disabled({"target-role": "any"})
        self.assert_is_not_disabled({"clone-max": "1"})
        self.assert_is_not_disabled({"clone-max": "01"})
        self.assert_is_not_disabled({"clone-max": 1})
        self.assert_is_not_disabled({"clone-node-max": "1"})
        self.assert_is_not_disabled({"clone-node-max": 1})
        self.assert_is_not_disabled({"clone-node-max": "1abc"})
        self.assert_is_not_disabled({"clone-node-max": "1.1"})


class FindOneOrMoreResources(TestCase):
    def setUp(self):
        self.cib = etree.fromstring("""
            <resources>
                <primitive id="R1" />
                <primitive id="R2" />
                <primitive id="R3" />
                <primitive id="R1x" />
                <primitive id="R2x" />
            </resources>
        """)

        def searcher(resource_element):
            return [
                resource_element.getparent().find(
                    ".//*[@id='{0}x']".format(resource_element.get("id"))
                )
            ]
        self.additional_search = searcher

    def test_one_existing(self):
        report_list = []
        resource = common.find_one_resource_and_report(
            self.cib,
            "R1",
            report_list
        )
        self.assertEqual("R1", resource.attrib.get("id"))
        assert_report_item_list_equal(
            report_list,
            []
        )

    def test_one_nonexistant(self):
        report_list = []
        resource = common.find_one_resource_and_report(
            self.cib,
            "R-missing",
            report_list
        )
        self.assertIsNone(resource)
        assert_report_item_list_equal(
            report_list,
            [
                fixture.report_not_found("R-missing", context_type="resources"),
            ]
        )

    def test_one_additional_search(self):
        report_list = []
        resource = common.find_one_resource_and_report(
            self.cib,
            "R1",
            report_list,
            additional_search=self.additional_search,
        )
        self.assertEqual("R1x", resource.attrib.get("id"))
        assert_report_item_list_equal(
            report_list,
            []
        )

    def test_more_existing(self):
        report_list = []
        resource_list = common.find_resources_and_report(
            self.cib,
            ["R1", "R2"],
            report_list
        )
        self.assertEqual(
            ["R1", "R2"],
            [resource.attrib.get("id") for resource in resource_list]
        )
        assert_report_item_list_equal(
            report_list,
            []
        )

    def test_more_some_missing(self):
        report_list = []
        resource_list = common.find_resources_and_report(
            self.cib,
            ["R1", "R2", "RY1", "RY2"],
            report_list
        )
        self.assertEqual(
            ["R1", "R2"],
            [resource.attrib.get("id") for resource in resource_list]
        )
        assert_report_item_list_equal(
            report_list,
            [
                fixture.report_not_found("RY1", context_type="resources"),
                fixture.report_not_found("RY2", context_type="resources"),
            ]
        )

    def test_more_additional_search(self):
        report_list = []
        resource_list = common.find_resources_and_report(
            self.cib,
            ["R1", "R2"],
            report_list,
            additional_search=self.additional_search,
        )
        self.assertEqual(
            ["R1x", "R2x"],
            [resource.attrib.get("id") for resource in resource_list]
        )
        assert_report_item_list_equal(
            report_list,
            []
        )


class FindPrimitives(TestCase):
    def assert_find_resources(self, input_resource_id, output_resource_ids):
        self.assertEqual(
            output_resource_ids,
            [
                element.get("id", "")
                for element in
                common.find_primitives(
                    fixture_cib.find(
                        './/*[@id="{0}"]'.format(input_resource_id)
                    )
                )
            ]
        )

    def test_primitive(self):
        self.assert_find_resources("A", ["A"])

    def test_primitive_in_clone(self):
        self.assert_find_resources("B", ["B"])

    def test_primitive_in_master(self):
        self.assert_find_resources("C", ["C"])

    def test_primitive_in_group(self):
        self.assert_find_resources("D1", ["D1"])
        self.assert_find_resources("D2", ["D2"])
        self.assert_find_resources("E1", ["E1"])
        self.assert_find_resources("E2", ["E2"])
        self.assert_find_resources("F1", ["F1"])
        self.assert_find_resources("F2", ["F2"])

    def test_primitive_in_bundle(self):
        self.assert_find_resources("H", ["H"])

    def test_group(self):
        self.assert_find_resources("D", ["D1", "D2"])

    def test_group_in_clone(self):
        self.assert_find_resources("E", ["E1", "E2"])

    def test_group_in_master(self):
        self.assert_find_resources("F", ["F1", "F2"])

    def test_cloned_primitive(self):
        self.assert_find_resources("B-clone", ["B"])

    def test_cloned_group(self):
        self.assert_find_resources("E-clone", ["E1", "E2"])

    def test_mastered_primitive(self):
        self.assert_find_resources("C-master", ["C"])

    def test_mastered_group(self):
        self.assert_find_resources("F-master", ["F1", "F2"])

    def test_bundle_empty(self):
        self.assert_find_resources("G-bundle", [])

    def test_bundle_with_primitive(self):
        self.assert_find_resources("H-bundle", ["H"])


class FindResourcesToEnable(TestCase):
    def assert_find_resources(self, input_resource_id, output_resource_ids):
        self.assertEqual(
            output_resource_ids,
            [
                element.get("id", "")
                for element in
                common.find_resources_to_enable(
                    fixture_cib.find(
                        './/*[@id="{0}"]'.format(input_resource_id)
                    )
                )
            ]
        )

    def test_primitive(self):
        self.assert_find_resources("A", ["A"])

    def test_primitive_in_clone(self):
        self.assert_find_resources("B", ["B", "B-clone"])

    def test_primitive_in_master(self):
        self.assert_find_resources("C", ["C", "C-master"])

    def test_primitive_in_group(self):
        self.assert_find_resources("D1", ["D1"])
        self.assert_find_resources("D2", ["D2"])
        self.assert_find_resources("E1", ["E1"])
        self.assert_find_resources("E2", ["E2"])
        self.assert_find_resources("F1", ["F1"])
        self.assert_find_resources("F2", ["F2"])

    def test_primitive_in_bundle(self):
        self.assert_find_resources("H", ["H", "H-bundle"])

    def test_group(self):
        self.assert_find_resources("D", ["D"])

    def test_group_in_clone(self):
        self.assert_find_resources("E", ["E", "E-clone"])

    def test_group_in_master(self):
        self.assert_find_resources("F", ["F", "F-master"])

    def test_cloned_primitive(self):
        self.assert_find_resources("B-clone", ["B-clone", "B"])

    def test_cloned_group(self):
        self.assert_find_resources("E-clone", ["E-clone", "E"])

    def test_mastered_primitive(self):
        self.assert_find_resources("C-master", ["C-master", "C"])

    def test_mastered_group(self):
        self.assert_find_resources("F-master", ["F-master", "F"])

    def test_bundle_empty(self):
        self.assert_find_resources("G-bundle", ["G-bundle"])

    def test_bundle_with_primitive(self):
        self.assert_find_resources("H-bundle", ["H-bundle", "H"])


class Enable(TestCase):
    @staticmethod
    def assert_enabled(pre, post):
        resource = etree.fromstring(pre)
        common.enable(resource, IdProvider(resource))
        assert_xml_equal(post, etree_to_str(resource))

    def test_disabled(self):
        self.assert_enabled(
            """
                <resource>
                    <meta_attributes>
                        <nvpair name="target-role" value="something" />
                    </meta_attributes>
                </resource>
            """,
            """
                <resource>
                    <meta_attributes />
                </resource>
            """
        )

    def test_enabled(self):
        self.assert_enabled(
            """
                <resource>
                </resource>
            """,
            """
                <resource>
                </resource>
            """
        )

    def test_only_first_meta(self):
        # this captures the current behavior
        # once pcs supports more instance and meta attributes for each resource,
        # this test should be reconsidered
        self.assert_enabled(
            """
                <resource>
                    <meta_attributes id="meta1">
                        <nvpair name="target-role" value="something" />
                    </meta_attributes>
                    <meta_attributes id="meta2">
                        <nvpair name="target-role" value="something" />
                    </meta_attributes>
                </resource>
            """,
            """
                <resource>
                    <meta_attributes id="meta1" />
                    <meta_attributes id="meta2">
                        <nvpair name="target-role" value="something" />
                    </meta_attributes>
                </resource>
            """
        )


class Disable(TestCase):
    @staticmethod
    def assert_disabled(pre, post):
        resource = etree.fromstring(pre)
        common.disable(resource, IdProvider(resource))
        assert_xml_equal(post, etree_to_str(resource))

    def test_disabled(self):
        xml = """
            <resource id="R">
                <meta_attributes id="R-meta_attributes">
                    <nvpair id="R-meta_attributes-target-role"
                        name="target-role" value="Stopped" />
                </meta_attributes>
            </resource>
        """
        self.assert_disabled(xml, xml)

    def test_enabled(self):
        self.assert_disabled(
            """
                <resource id="R">
                </resource>
            """,
            """
                <resource id="R">
                    <meta_attributes id="R-meta_attributes">
                        <nvpair id="R-meta_attributes-target-role"
                            name="target-role" value="Stopped" />
                    </meta_attributes>
                </resource>
            """
        )

    def test_only_first_meta(self):
        # this captures the current behavior
        # once pcs supports more instance and meta attributes for each resource,
        # this test should be reconsidered
        self.assert_disabled(
            """
                <resource id="R">
                    <meta_attributes id="R-meta_attributes">
                    </meta_attributes>
                    <meta_attributes id="R-meta_attributes-2">
                    </meta_attributes>
                </resource>
            """,
            """
                <resource id="R">
                    <meta_attributes id="R-meta_attributes">
                        <nvpair id="R-meta_attributes-target-role"
                            name="target-role" value="Stopped" />
                    </meta_attributes>
                    <meta_attributes id="R-meta_attributes-2">
                    </meta_attributes>
                </resource>
            """
        )


class FindResourcesToManage(TestCase):
    def assert_find_resources(self, input_resource_id, output_resource_ids):
        self.assertEqual(
            output_resource_ids,
            [
                element.get("id", "")
                for element in
                common.find_resources_to_manage(
                    fixture_cib.find(
                        './/*[@id="{0}"]'.format(input_resource_id)
                    )
                )
            ]
        )

    def test_primitive(self):
        self.assert_find_resources("A", ["A"])

    def test_primitive_in_clone(self):
        self.assert_find_resources("B", ["B", "B-clone"])

    def test_primitive_in_master(self):
        self.assert_find_resources("C", ["C", "C-master"])

    def test_primitive_in_group(self):
        self.assert_find_resources("D1", ["D1", "D"])
        self.assert_find_resources("D2", ["D2", "D"])
        self.assert_find_resources("E1", ["E1", "E-clone", "E"])
        self.assert_find_resources("E2", ["E2", "E-clone", "E"])
        self.assert_find_resources("F1", ["F1", "F-master", "F"])
        self.assert_find_resources("F2", ["F2", "F-master", "F"])

    def test_primitive_in_bundle(self):
        self.assert_find_resources("H", ["H", "H-bundle"])

    def test_group(self):
        self.assert_find_resources("D", ["D", "D1", "D2"])

    def test_group_in_clone(self):
        self.assert_find_resources("E", ["E", "E-clone", "E1", "E2"])

    def test_group_in_master(self):
        self.assert_find_resources("F", ["F", "F-master", "F1", "F2"])

    def test_cloned_primitive(self):
        self.assert_find_resources("B-clone", ["B-clone", "B"])

    def test_cloned_group(self):
        self.assert_find_resources("E-clone", ["E-clone", "E", "E1", "E2"])

    def test_mastered_primitive(self):
        self.assert_find_resources("C-master", ["C-master", "C"])

    def test_mastered_group(self):
        self.assert_find_resources("F-master", ["F-master", "F", "F1", "F2"])

    def test_bundle_empty(self):
        self.assert_find_resources("G-bundle", ["G-bundle"])

    def test_bundle_with_primitive(self):
        self.assert_find_resources("H-bundle", ["H-bundle", "H"])


class FindResourcesToUnmanage(TestCase):
    def assert_find_resources(self, input_resource_id, output_resource_ids):
        self.assertEqual(
            output_resource_ids,
            [
                element.get("id", "")
                for element in
                common.find_resources_to_unmanage(
                    fixture_cib.find(
                        './/*[@id="{0}"]'.format(input_resource_id)
                    )
                )
            ]
        )

    def test_primitive(self):
        self.assert_find_resources("A", ["A"])

    def test_primitive_in_clone(self):
        self.assert_find_resources("B", ["B"])

    def test_primitive_in_master(self):
        self.assert_find_resources("C", ["C"])

    def test_primitive_in_group(self):
        self.assert_find_resources("D1", ["D1"])
        self.assert_find_resources("D2", ["D2"])
        self.assert_find_resources("E1", ["E1"])
        self.assert_find_resources("E2", ["E2"])
        self.assert_find_resources("F1", ["F1"])
        self.assert_find_resources("F2", ["F2"])

    def test_primitive_in_bundle(self):
        self.assert_find_resources("H", ["H"])

    def test_group(self):
        self.assert_find_resources("D", ["D1", "D2"])

    def test_group_in_clone(self):
        self.assert_find_resources("E", ["E1", "E2"])

    def test_group_in_master(self):
        self.assert_find_resources("F", ["F1", "F2"])

    def test_cloned_primitive(self):
        self.assert_find_resources("B-clone", ["B"])

    def test_cloned_group(self):
        self.assert_find_resources("E-clone", ["E1", "E2"])

    def test_mastered_primitive(self):
        self.assert_find_resources("C-master", ["C"])

    def test_mastered_group(self):
        self.assert_find_resources("F-master", ["F1", "F2"])

    def test_bundle_empty(self):
        self.assert_find_resources("G-bundle", ["G-bundle"])

    def test_bundle_with_primitive(self):
        self.assert_find_resources("H-bundle", ["H-bundle", "H"])


class Manage(TestCase):
    @staticmethod
    def assert_managed(pre, post):
        resource = etree.fromstring(pre)
        common.manage(resource, IdProvider(resource))
        assert_xml_equal(post, etree_to_str(resource))

    def test_unmanaged(self):
        self.assert_managed(
            """
                <resource>
                    <meta_attributes>
                        <nvpair name="is-managed" value="something" />
                    </meta_attributes>
                </resource>
            """,
            """
                <resource>
                    <meta_attributes />
                </resource>
            """
        )

    def test_managed(self):
        self.assert_managed(
            """
                <resource>
                </resource>
            """,
            """
                <resource>
                </resource>
            """
        )

    def test_only_first_meta(self):
        # this captures the current behavior
        # once pcs supports more instance and meta attributes for each resource,
        # this test should be reconsidered
        self.assert_managed(
            """
                <resource>
                    <meta_attributes id="meta1">
                        <nvpair name="is-managed" value="something" />
                    </meta_attributes>
                    <meta_attributes id="meta2">
                        <nvpair name="is-managed" value="something" />
                    </meta_attributes>
                </resource>
            """,
            """
                <resource>
                    <meta_attributes id="meta1" />
                    <meta_attributes id="meta2">
                        <nvpair name="is-managed" value="something" />
                    </meta_attributes>
                </resource>
            """
        )


class Unmanage(TestCase):
    @staticmethod
    def assert_unmanaged(pre, post):
        resource = etree.fromstring(pre)
        common.unmanage(resource, IdProvider(resource))
        assert_xml_equal(post, etree_to_str(resource))

    def test_unmanaged(self):
        xml = """
            <resource id="R">
                <meta_attributes id="R-meta_attributes">
                    <nvpair id="R-meta_attributes-is-managed"
                        name="is-managed" value="false" />
                </meta_attributes>
            </resource>
        """
        self.assert_unmanaged(xml, xml)

    def test_managed(self):
        self.assert_unmanaged(
            """
                <resource id="R">
                </resource>
            """,
            """
                <resource id="R">
                    <meta_attributes id="R-meta_attributes">
                        <nvpair id="R-meta_attributes-is-managed"
                            name="is-managed" value="false" />
                    </meta_attributes>
                </resource>
            """
        )

    def test_only_first_meta(self):
        # this captures the current behavior
        # once pcs supports more instance and meta attributes for each resource,
        # this test should be reconsidered
        self.assert_unmanaged(
            """
                <resource id="R">
                    <meta_attributes id="R-meta_attributes">
                    </meta_attributes>
                    <meta_attributes id="R-meta_attributes-2">
                    </meta_attributes>
                </resource>
            """,
            """
                <resource id="R">
                    <meta_attributes id="R-meta_attributes">
                        <nvpair id="R-meta_attributes-is-managed"
                            name="is-managed" value="false" />
                    </meta_attributes>
                    <meta_attributes id="R-meta_attributes-2">
                    </meta_attributes>
                </resource>
            """
        )


class ValidateMoveBanClearMixin():
    #pylint: disable=too-many-public-methods
    @staticmethod
    def _fixture_clone(promotable=False):
        return etree.fromstring(f"""
            <clone id="R-clone">
                <primitive id="R" />
                <meta_attributes>
                    <nvpair name="promotable" value="{'true' if promotable else 'false'}" />
                </meta_attributes>
            </clone>
        """)

    @staticmethod
    def _fixture_group_clone(promotable=False):
        return etree.fromstring(f"""
            <clone id="G-clone">
                <group id="G">
                    <primitive id="R" />
                </group>
                <meta_attributes>
                    <nvpair name="promotable" value="{'true' if promotable else 'false'}" />
                </meta_attributes>
            </clone>
        """)

    @staticmethod
    def _fixture_master():
        return etree.fromstring(f"""
            <master id="R-master">
                <primitive id="R" />
            </master>
        """)

    @staticmethod
    def _fixture_group_master():
        return etree.fromstring(f"""
            <master id="G-master">
                <group id="G">
                    <primitive id="R" />
                </group>
            </master>
        """)

    def test_master_true_promotable_clone(self):
        element = self._fixture_clone(True)
        assert_report_item_list_equal(
            self.validate(element, True),
            []
        )

    def test_master_false_promotable_clone(self):
        element = self._fixture_clone(True)
        assert_report_item_list_equal(
            self.validate(element, False),
            []
        )

    def test_master_true_clone(self):
        element = self._fixture_clone(False)
        assert_report_item_list_equal(
            self.validate(element, True),
            [
                fixture.error(
                    self.report_code_bad_master,
                    resource_id="R-clone",
                    promotable_id=None,
                ),
            ]
        )

    def test_master_false_clone(self):
        element = self._fixture_clone(False)
        assert_report_item_list_equal(
            self.validate(element, False),
            []
        )

    def test_master_true_master(self):
        element = self._fixture_master()
        assert_report_item_list_equal(
            self.validate(element, True),
            []
        )

    def test_master_false_master(self):
        element = self._fixture_master()
        assert_report_item_list_equal(
            self.validate(element, False),
            []
        )

    def test_master_true_promotable_clone_resource(self):
        element = self._fixture_clone(True)
        assert_report_item_list_equal(
            self.validate(element.find("./primitive"), True),
            [
                fixture.error(
                    self.report_code_bad_master,
                    resource_id="R",
                    promotable_id="R-clone",
                ),
            ]
        )

    def test_master_false_promotable_clone_resource(self):
        element = self._fixture_clone(True)
        assert_report_item_list_equal(
            self.validate(element.find("./primitive"), False),
            []
        )

    def test_master_true_promotable_clone_group(self):
        element = self._fixture_group_clone(True)
        assert_report_item_list_equal(
            self.validate(element.find("./group"), True),
            [
                fixture.error(
                    self.report_code_bad_master,
                    resource_id="G",
                    promotable_id="G-clone",
                ),
            ]
        )

    def test_master_false_promotable_clone_group(self):
        element = self._fixture_group_clone(True)
        assert_report_item_list_equal(
            self.validate(element.find("./group"), False),
            []
        )

    def test_master_true_promotable_clone_group_resource(self):
        element = self._fixture_group_clone(True)
        assert_report_item_list_equal(
            self.validate(element.find("./group/primitive"), True),
            [
                fixture.error(
                    self.report_code_bad_master,
                    resource_id="R",
                    promotable_id="G-clone",
                ),
            ]
        )

    def test_master_false_promotable_clone_group_resource(self):
        element = self._fixture_group_clone(True)
        assert_report_item_list_equal(
            self.validate(element.find("./group/primitive"), False),
            []
        )

    def test_master_true_clone_resource(self):
        element = self._fixture_clone(False)
        assert_report_item_list_equal(
            self.validate(element.find("./primitive"), True),
            [
                fixture.error(
                    self.report_code_bad_master,
                    resource_id="R",
                    promotable_id=None,
                ),
            ]
        )

    def test_master_false_clone_resource(self):
        element = self._fixture_clone(False)
        assert_report_item_list_equal(
            self.validate(element.find("./primitive"), False),
            []
        )

    def test_master_true_clone_group(self):
        element = self._fixture_group_clone(False)
        assert_report_item_list_equal(
            self.validate(element.find("./group"), True),
            [
                fixture.error(
                    self.report_code_bad_master,
                    resource_id="G",
                    promotable_id=None,
                ),
            ]
        )

    def test_master_false_clone_group(self):
        element = self._fixture_group_clone(False)
        assert_report_item_list_equal(
            self.validate(element.find("./group"), False),
            []
        )

    def test_master_true_clone_group_resource(self):
        element = self._fixture_group_clone(False)
        assert_report_item_list_equal(
            self.validate(element.find("./group/primitive"), True),
            [
                fixture.error(
                    self.report_code_bad_master,
                    resource_id="R",
                    promotable_id=None,
                ),
            ]
        )

    def test_master_false_clone_group_resource(self):
        element = self._fixture_group_clone(False)
        assert_report_item_list_equal(
            self.validate(element.find("./group/primitive"), False),
            []
        )

    def test_master_true_master_resource(self):
        element = self._fixture_master()
        assert_report_item_list_equal(
            self.validate(element.find("./primitive"), True),
            [
                fixture.error(
                    self.report_code_bad_master,
                    resource_id="R",
                    promotable_id="R-master",
                ),
            ]
        )

    def test_master_true_master_group(self):
        element = self._fixture_group_master()
        assert_report_item_list_equal(
            self.validate(element.find("./group"), True),
            [
                fixture.error(
                    self.report_code_bad_master,
                    resource_id="G",
                    promotable_id="G-master",
                ),
            ]
        )

    def test_master_true_master_group_resource(self):
        element = self._fixture_group_master()
        assert_report_item_list_equal(
            self.validate(element.find("./group/primitive"), True),
            [
                fixture.error(
                    self.report_code_bad_master,
                    resource_id="R",
                    promotable_id="G-master",
                ),
            ]
        )


class ValidateMove(ValidateMoveBanClearMixin, TestCase):
    validate = staticmethod(common.validate_move)
    report_code_bad_master = (
        report_codes.CANNOT_MOVE_RESOURCE_MASTER_RESOURCE_NOT_PROMOTABLE
    )

    @staticmethod
    def _fixture_bundle():
        return etree.fromstring(f"""
            <bundle id="R-bundle">
                <primitive id="R" />
            </bundle>
        """)

    def test_master_false_promotable_clone(self):
        element = self._fixture_clone(True)
        assert_report_item_list_equal(
            self.validate(element, False),
            [
                fixture.error(
                    report_codes.CANNOT_MOVE_RESOURCE_PROMOTABLE_NOT_MASTER,
                    resource_id="R-clone",
                    promotable_id="R-clone",
                ),
            ]
        )

    def test_master_true_clone(self):
        element = self._fixture_clone(False)
        assert_report_item_list_equal(
            self.validate(element, True),
            [
                fixture.error(
                    report_codes.CANNOT_MOVE_RESOURCE_CLONE,
                    resource_id="R-clone",
                ),
            ]
        )

    def test_master_false_clone(self):
        element = self._fixture_clone(False)
        assert_report_item_list_equal(
            self.validate(element, False),
            [
                fixture.error(
                    report_codes.CANNOT_MOVE_RESOURCE_CLONE,
                    resource_id="R-clone",
                ),
            ]
        )

    def test_master_false_master(self):
        element = self._fixture_master()
        assert_report_item_list_equal(
            self.validate(element, False),
            [
                fixture.error(
                    report_codes.CANNOT_MOVE_RESOURCE_PROMOTABLE_NOT_MASTER,
                    resource_id="R-master",
                    promotable_id="R-master",
                ),
            ]
        )

    def test_master_false_promotable_clone_resource(self):
        element = self._fixture_clone(True)
        assert_report_item_list_equal(
            self.validate(element.find("./primitive"), False),
            [
                fixture.error(
                    report_codes.CANNOT_MOVE_RESOURCE_PROMOTABLE_NOT_MASTER,
                    resource_id="R",
                    promotable_id="R-clone",
                ),
            ]
        )

    def test_master_false_promotable_clone_group(self):
        element = self._fixture_group_clone(True)
        assert_report_item_list_equal(
            self.validate(element.find("./group"), False),
            [
                fixture.error(
                    report_codes.CANNOT_MOVE_RESOURCE_PROMOTABLE_NOT_MASTER,
                    resource_id="G",
                    promotable_id="G-clone",
                ),
            ]
        )

    def test_master_false_promotable_clone_group_resource(self):
        element = self._fixture_group_clone(True)
        assert_report_item_list_equal(
            self.validate(element.find("./group/primitive"), False),
            [
                fixture.error(
                    report_codes.CANNOT_MOVE_RESOURCE_PROMOTABLE_NOT_MASTER,
                    resource_id="R",
                    promotable_id="G-clone",
                ),
            ]
        )

    def test_master_true_clone_resource(self):
        element = self._fixture_clone(False)
        assert_report_item_list_equal(
            self.validate(element.find("./primitive"), True),
            [
                fixture.error(
                    report_codes.CANNOT_MOVE_RESOURCE_CLONE,
                    resource_id="R",
                ),
            ]
        )

    def test_master_false_clone_resource(self):
        element = self._fixture_clone(False)
        assert_report_item_list_equal(
            self.validate(element.find("./primitive"), False),
            [
                fixture.error(
                    report_codes.CANNOT_MOVE_RESOURCE_CLONE,
                    resource_id="R",
                ),
            ]
        )

    def test_master_true_clone_group(self):
        element = self._fixture_group_clone(False)
        assert_report_item_list_equal(
            self.validate(element.find("./group"), True),
            [
                fixture.error(
                    report_codes.CANNOT_MOVE_RESOURCE_CLONE,
                    resource_id="G",
                ),
            ]
        )

    def test_master_false_clone_group(self):
        element = self._fixture_group_clone(False)
        assert_report_item_list_equal(
            self.validate(element.find("./group"), False),
            [
                fixture.error(
                    report_codes.CANNOT_MOVE_RESOURCE_CLONE,
                    resource_id="G",
                ),
            ]
        )

    def test_master_true_clone_group_resource(self):
        element = self._fixture_group_clone(False)
        assert_report_item_list_equal(
            self.validate(element.find("./group/primitive"), True),
            [
                fixture.error(
                    report_codes.CANNOT_MOVE_RESOURCE_CLONE,
                    resource_id="R",
                ),
            ]
        )

    def test_master_false_clone_group_resource(self):
        element = self._fixture_group_clone(False)
        assert_report_item_list_equal(
            self.validate(element.find("./group/primitive"), False),
            [
                fixture.error(
                    report_codes.CANNOT_MOVE_RESOURCE_CLONE,
                    resource_id="R",
                ),
            ]
        )

    def test_bundle(self):
        element = self._fixture_bundle()
        assert_report_item_list_equal(
            self.validate(element, False),
            [
                fixture.error(
                    report_codes.CANNOT_MOVE_RESOURCE_BUNDLE,
                    resource_id="R-bundle",
                ),
            ]
        )

    def test_bundle_resource(self):
        element = self._fixture_bundle()
        assert_report_item_list_equal(
            self.validate(element.find("./primitive"), False),
            []
        )

class ValidateBan(ValidateMoveBanClearMixin, TestCase):
    validate = staticmethod(common.validate_ban)
    report_code_bad_master = (
        report_codes.CANNOT_BAN_RESOURCE_MASTER_RESOURCE_NOT_PROMOTABLE
    )


class ValidateUnmoveUnban(ValidateMoveBanClearMixin, TestCase):
    validate = staticmethod(common.validate_unmove_unban)
    report_code_bad_master = (
        report_codes
            .CANNOT_UNMOVE_UNBAN_RESOURCE_MASTER_RESOURCE_NOT_PROMOTABLE
    )
