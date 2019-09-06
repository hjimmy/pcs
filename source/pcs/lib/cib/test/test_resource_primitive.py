from __future__ import (
    absolute_import,
    division,
    print_function,
)

from functools import partial

from lxml import etree

from pcs.test.tools.assertions import assert_xml_equal
from pcs.lib.resource_agent import CrmAgent
from pcs.lib.cib.resource import primitive
from pcs.test.tools.pcs_unittest import TestCase, mock


class FindPrimitivesByAgent(TestCase):
    def setUp(self):
        self.agent = mock.MagicMock(spec_set=CrmAgent)
        self.agent.get_standard.return_value = "standard"
        self.agent.get_provider.return_value = "provider"
        self.agent.get_type.return_value = "agent_type"
        self.resources_section = etree.fromstring("""
        <resources>
            <primitive
                class="standard" provider="provider" type="agent_type" id="r0"
            />
            <primitive
                class="something" provider="provider" type="agent_type" id="r23"
            />
            <primitive class="stonith" type="agent_type" id="r1"/>
            <primitive
                class="standard" provider="provider" type="dummy1" id="r123"
            />
            <group>
                <primitive class="stonith" type="agent_type" id="r2"/>
                <primitive
                    class="standard" provider="pacemaker" type="agent_type"
                    id="r3"
                />
                <primitive
                    class="standard" provider="provider" type="agent_type"
                    id="r4"
                />
            </group>
            <clone>
                <group>
                    <primitive
                        class="standard" provider="provider" type="agent_type"
                        id="r5"
                    />
                </group>
            </clone>
            <clone>
                <primitive
                    class="standard" provider="provider" type="agent_type"
                    id="r6"
                />
            </clone>
        </resources>
        """)

    def test_stonith(self):
        self.agent.get_standard.return_value = "stonith"
        self.agent.get_provider.return_value = ""
        results = primitive.find_primitives_by_agent(
            self.resources_section, self.agent
        )
        expected_results = [
            '<primitive class="stonith" type="agent_type" id="r1"/>',
            '<primitive class="stonith" type="agent_type" id="r2"/>',
        ]
        self.assertEqual(len(expected_results), len(results))
        for i, res in enumerate(results):
            assert_xml_equal(expected_results[i], etree.tostring(res).decode())

    def test_with_provider(self):
        results = primitive.find_primitives_by_agent(
            self.resources_section, self.agent
        )
        expected_results = [
            """<primitive
                class="standard" provider="provider" type="agent_type" id="r0"
            />""",
            """<primitive
                class="standard" provider="provider" type="agent_type" id="r4"
            />""",
            """<primitive
                class="standard" provider="provider" type="agent_type" id="r5"
            />""",
            """<primitive
                class="standard" provider="provider" type="agent_type" id="r6"
            />""",
        ]
        self.assertEqual(len(expected_results), len(results))
        for i, res in enumerate(results):
            assert_xml_equal(expected_results[i], etree.tostring(res).decode())


@mock.patch("pcs.lib.cib.resource.primitive.append_new_instance_attributes")
@mock.patch("pcs.lib.cib.resource.primitive.append_new_meta_attributes")
@mock.patch("pcs.lib.cib.resource.primitive.create_operations")
class AppendNew(TestCase):
    def setUp(self):
        self.resources_section = etree.fromstring("<resources/>")

        self.instance_attributes = {"a": "b"}
        self.meta_attributes = {"c": "d"}
        self.operation_list = [{"name": "monitoring"}]

        self.run = partial(
            primitive.append_new,
            self.resources_section,
            instance_attributes=self.instance_attributes,
            meta_attributes=self.meta_attributes,
            operation_list=self.operation_list,
        )

    def check_mocks(
        self,
        primitive_element,
        create_operations,
        append_new_meta_attributes,
        append_new_instance_attributes,
    ):
        create_operations.assert_called_once_with(
            primitive_element,
            self.operation_list
        )
        append_new_meta_attributes.assert_called_once_with(
            primitive_element,
            self.meta_attributes
        )
        append_new_instance_attributes.assert_called_once_with(
            primitive_element,
            self.instance_attributes
        )

    def test_append_without_provider(
        self,
        create_operations,
        append_new_meta_attributes,
        append_new_instance_attributes,
    ):
        primitive_element = self.run("RESOURCE_ID", "OCF", None, "DUMMY")
        self.assertEqual(
            primitive_element,
            self.resources_section.find(".//primitive")
        )
        self.assertEqual(primitive_element.attrib["class"], "OCF")
        self.assertEqual(primitive_element.attrib["type"], "DUMMY")
        self.assertFalse(primitive_element.attrib.has_key("provider"))

        self.check_mocks(
            primitive_element,
            create_operations,
            append_new_meta_attributes,
            append_new_instance_attributes,
        )

    def test_append_with_provider(
        self,
        create_operations,
        append_new_meta_attributes,
        append_new_instance_attributes,
    ):
        primitive_element = self.run("RESOURCE_ID", "OCF", "HEARTBEAT", "DUMMY")
        self.assertEqual(
            primitive_element,
            self.resources_section.find(".//primitive")
        )
        self.assertEqual(primitive_element.attrib["class"], "OCF")
        self.assertEqual(primitive_element.attrib["type"], "DUMMY")
        self.assertEqual(primitive_element.attrib["provider"], "HEARTBEAT")

        self.check_mocks(
            primitive_element,
            create_operations,
            append_new_meta_attributes,
            append_new_instance_attributes,
        )
