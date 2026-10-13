// Copyright Contributors to the OpenDCC project
// SPDX-License-Identifier: Apache-2.0

#include "opendcc/base/packaging/toml_parser.h"
#include <pxr/base/vt/array.h>
#include <algorithm>
#include <cstdint>
#include "package_test_utils.h"

#define DOCTEST_CONFIG_NO_SHORT_MACRO_NAMES
#define DOCTEST_CONFIG_SUPER_FAST_ASSERTS
#define DOCTEST_CONFIG_IMPLEMENTATION_IN_DLL
#include <doctest/doctest.h>
OPENDCC_NAMESPACE_OPEN
PXR_NAMESPACE_USING_DIRECTIVE

DOCTEST_TEST_SUITE("PackagingTOMLParserTests")
{
    DOCTEST_TEST_CASE("deserialization")
    {

        packaging_tests::TemporaryDirectory directory;
        PackageData actual;
        auto assert_attribute = [&actual](const std::string& name, const VtValue& expected) {
            DOCTEST_INFO("Manifest attribute: " << name);
            const auto attr = std::find_if(actual.raw_attributes.begin(), actual.raw_attributes.end(),
                                           [&name](const PackageAttribute& attr) { return attr.name == name; });
            DOCTEST_REQUIRE(attr != actual.raw_attributes.end());
            DOCTEST_CHECK(attr->value.GetTypeid() == expected.GetTypeid());
            DOCTEST_CHECK_EQ(attr->value, expected);
        };
        auto parser = TOMLParser();

        DOCTEST_SUBCASE("basic_types")
        {
            const auto text = R"(
bool = true
int = 1
float = 3.1415
str = 'some str'
arr = [1, 2, 3]
mixed_arr = [3.41, 0]

[base]
name = 'asdf'

[table]
val1 = 'cx'
val2 = 3
inline = { a = 'a', b = 'c' }

[[table_arr]]
a = 42

[[table_arr.val]]
"a.b" = 64

[[table_arr]]
c = 'c'
)";
            const auto test_file = directory.write("package.toml", text);

            actual = parser.parse(test_file);
            DOCTEST_CHECK_EQ(actual.name, std::string("asdf"));
            assert_attribute("base", VtValue(VtDictionary { { "name", VtValue("asdf") } }));
            assert_attribute("bool", VtValue(true));
            assert_attribute("int", VtValue(int64_t { 1 }));
            assert_attribute("float", VtValue(3.1415));
            assert_attribute("str", VtValue("some str"));
            assert_attribute("arr", VtValue(VtArray<VtValue> { VtValue(int64_t { 1 }), VtValue(int64_t { 2 }), VtValue(int64_t { 3 }) }));
            assert_attribute("mixed_arr", VtValue(VtArray<VtValue> { VtValue(3.41), VtValue(int64_t { 0 }) }));

            const VtDictionary expected_inline_table = { { "a", VtValue("a") }, { "b", VtValue("c") } };
            const VtDictionary expected_table = { { "val1", VtValue("cx") },
                                                  { "val2", VtValue(int64_t { 3 }) },
                                                  { "inline", VtValue(expected_inline_table) } };
            assert_attribute("table", VtValue(expected_table));

            const VtArray<VtDictionary> expected_nested_tables = { VtDictionary { { "a.b", VtValue(int64_t { 64 }) } } };
            const VtArray<VtDictionary> expected_table_array = {
                VtDictionary { { "a", VtValue(int64_t { 42 }) }, { "val", VtValue(expected_nested_tables) } }, VtDictionary { { "c", VtValue("c") } }
            };
            assert_attribute("table_arr", VtValue(expected_table_array));
        }
    }

    DOCTEST_TEST_CASE("invalid_manifests")
    {
        packaging_tests::TemporaryDirectory directory;
        TOMLParser parser;
        for (const auto& text : { "[base\nname = 'broken'\n", "[base]\nroot = '.'\n", "[base]\nname = 42\n" })
        {
            DOCTEST_INFO("Invalid manifest: " << text);
            const auto filename = directory.write("package.toml", text);
            DOCTEST_CHECK_FALSE(parser.parse(filename).is_valid());
        }
        DOCTEST_CHECK_FALSE(parser.parse((directory.path() / "missing.toml").generic_u8string()).is_valid());
    }
}

OPENDCC_NAMESPACE_CLOSE
