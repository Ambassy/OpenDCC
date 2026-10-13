/*
 * Copyright Contributors to the OpenDCC project
 * SPDX-License-Identifier: Apache-2.0
 */

#include "package_lifecycle_fixture.h"
#include <algorithm>

#define DOCTEST_CONFIG_NO_SHORT_MACRO_NAMES
#define DOCTEST_CONFIG_SUPER_FAST_ASSERTS
#define DOCTEST_CONFIG_IMPLEMENTATION_IN_DLL
#include <doctest/doctest.h>

OPENDCC_NAMESPACE_OPEN

DOCTEST_TEST_SUITE("PackagingLifecycle")
{
    DOCTEST_TEST_CASE_FIXTURE(packaging_tests::LifecycleFixture, "native_only_load_unload_reload")
    {
        write_manifest("native", native_entry_point());
        registry.fetch_packages();
        const auto package = registry.get_package("native");
        DOCTEST_REQUIRE(registry.load(package));
        DOCTEST_CHECK(package.is_loaded());
        DOCTEST_CHECK(init_and_uninit_events() == std::vector<std::string> { "native:init:native" });
        DOCTEST_CHECK(registry.load(package));
        DOCTEST_CHECK(init_and_uninit_events().size() == 1);
        DOCTEST_REQUIRE(registry.unload(package));
        DOCTEST_CHECK_FALSE(package.is_loaded());
        DOCTEST_CHECK(init_and_uninit_events() == std::vector<std::string> { "native:init:native", "native:uninit:native" });
        DOCTEST_CHECK_FALSE(packaging_tests::is_library_loaded(OPENDCC_PACKAGING_LIFECYCLE_LIBRARY));
        DOCTEST_REQUIRE(registry.load(package));
        DOCTEST_CHECK(init_and_uninit_events().back() == "native:init:native");
        DOCTEST_REQUIRE(registry.unload(package));
        const std::vector<std::string> expected_reload_events = { "native:init:native", "native:uninit:native", "native:init:native",
                                                                  "native:uninit:native" };
        DOCTEST_CHECK(init_and_uninit_events() == expected_reload_events);
        DOCTEST_CHECK(registry.unload(package));
        DOCTEST_CHECK(init_and_uninit_events() == expected_reload_events);
    }

    DOCTEST_TEST_CASE_FIXTURE(packaging_tests::LifecycleFixture, "plain_library_and_python_import_do_not_initialize_entry_points")
    {
        const auto imports = fmt::format(R"toml([[native.load]]
path = '{}'

[[python.import]]
module = 'lifecycle_entry_point'
)toml",
                                         OPENDCC_PACKAGING_PLAIN_LIBRARY);
        write_manifest("imports", imports);
        registry.fetch_packages();
        DOCTEST_REQUIRE(registry.load("imports"));
        DOCTEST_CHECK(init_and_uninit_events().empty());
        DOCTEST_CHECK(modules.contains("lifecycle_entry_point"));
        DOCTEST_CHECK(packaging_tests::is_library_loaded(OPENDCC_PACKAGING_PLAIN_LIBRARY));
        DOCTEST_REQUIRE(registry.unload("imports"));
        DOCTEST_CHECK(init_and_uninit_events().empty());
        DOCTEST_CHECK_FALSE(packaging_tests::is_library_loaded(OPENDCC_PACKAGING_PLAIN_LIBRARY));
    }

    DOCTEST_TEST_CASE_FIXTURE(packaging_tests::LifecycleFixture, "diamond_initializes_once_and_unloads_dependents_first")
    {
        write_manifest("leaf", python_entry_point());
        write_manifest("left", native_entry_point(), "cpp", "[dependencies]\nleaf = {}\n");
        write_manifest("right", python_entry_point(), "cpp", "[dependencies]\nleaf = {}\n");
        write_manifest("root", native_entry_point(), "cpp", "[dependencies]\nleft = {}\nright = {}\n");
        registry.fetch_packages();
        DOCTEST_REQUIRE(registry.load("root"));
        const std::vector<std::string> package_names = { "leaf", "left", "right", "root" };
        const auto initialization_events = init_and_uninit_events();
        DOCTEST_REQUIRE(initialization_events.size() == package_names.size());
        for (const auto& event : { "python:init:leaf", "native:init:left", "python:init:right", "native:init:root" })
            DOCTEST_CHECK(std::count(initialization_events.begin(), initialization_events.end(), event) == 1);
        DOCTEST_CHECK(initialization_events.front() == "python:init:leaf");
        DOCTEST_CHECK(initialization_events.back() == "native:init:root");
        for (const auto& name : package_names)
            DOCTEST_CHECK(registry.get_package(name).is_loaded());
        DOCTEST_REQUIRE(registry.unload("leaf"));
        const auto lifecycle_events = init_and_uninit_events();
        DOCTEST_REQUIRE(lifecycle_events.size() == initialization_events.size() + package_names.size());
        for (const auto& event : { "python:uninit:leaf", "native:uninit:left", "python:uninit:right", "native:uninit:root" })
            DOCTEST_CHECK(std::count(lifecycle_events.begin(), lifecycle_events.end(), event) == 1);
        const auto position = [&lifecycle_events](const std::string& event) {
            return std::find(lifecycle_events.begin(), lifecycle_events.end(), event);
        };
        DOCTEST_CHECK(position("native:uninit:root") < position("native:uninit:left"));
        DOCTEST_CHECK(position("native:uninit:root") < position("python:uninit:right"));
        DOCTEST_CHECK(position("native:uninit:left") < position("python:uninit:leaf"));
        DOCTEST_CHECK(position("python:uninit:right") < position("python:uninit:leaf"));
        for (const auto& name : package_names)
            DOCTEST_CHECK_FALSE(registry.get_package(name).is_loaded());
    }
}

OPENDCC_NAMESPACE_CLOSE
