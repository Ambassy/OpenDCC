// Copyright Contributors to the OpenDCC project
// SPDX-License-Identifier: Apache-2.0

#include "opendcc/base/packaging/package_registry.h"

#define DOCTEST_CONFIG_NO_SHORT_MACRO_NAMES
#define DOCTEST_CONFIG_SUPER_FAST_ASSERTS
#define DOCTEST_CONFIG_IMPLEMENTATION_IN_DLL
#include <doctest/doctest.h>

OPENDCC_NAMESPACE_OPEN
PXR_NAMESPACE_USING_DIRECTIVE

namespace
{
    class TestPackageProvider : public PackageProvider
    {
    public:
        explicit TestPackageProvider(const PackageData& data)
            : m_packages { data }
        {
        }

        void fetch() override {}
        const std::vector<PackageData>& get_cached_packages() const override { return m_packages; }

    private:
        std::vector<PackageData> m_packages;
    };
}

DOCTEST_TEST_SUITE("PackagingPackageRegistry")
{
    DOCTEST_TEST_CASE("UTF-8 package root")
    {
        PackageData data;
        data.name = "test_utf8_root";
#ifdef OPENDCC_OS_WINDOWS
        const auto prefix = std::string("C:");
#else
        const auto prefix = std::string();
#endif
        data.path = prefix + u8"/packages/\u0442\u0435\u0441\u0442";
        auto root = std::string(u8"assets/../\u8d44\u6e90");
        auto expected = prefix + u8"/packages/\u0442\u0435\u0441\u0442/\u8d44\u6e90";

        DOCTEST_SUBCASE("relative root") {}
        DOCTEST_SUBCASE("absolute root")
        {
            root = prefix + u8"/assets/\u8d44\u6e90";
            expected = root;
        }

        data.raw_attributes.push_back({ "base", VtValue(VtDictionary { { "root", VtValue(root) } }) });
        PackageRegistry registry;
        registry.add_package_provider(std::make_shared<TestPackageProvider>(data));
        registry.fetch_packages();

        DOCTEST_CHECK_EQ(registry.get_package(data.name).get_root_dir(), expected);
    }
}

OPENDCC_NAMESPACE_CLOSE
