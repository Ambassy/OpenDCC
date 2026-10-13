/*
 * Copyright Contributors to the OpenDCC project
 * SPDX-License-Identifier: Apache-2.0
 */

#include "opendcc/base/packaging/package_entry_point.h"
#include "opendcc/base/utils/env.h"
#include <fstream>
#include <string>
#include <stdexcept>

OPENDCC_NAMESPACE_OPEN

class LifecycleEntryPoint : public PackageEntryPoint
{
public:
    ~LifecycleEntryPoint() override
    {
        if (!m_filename.empty())
            std::ofstream(m_filename, std::ios::app) << "native:destroy:" << m_package_name << '\n';
    }
    void initialize(const Package& package) override
    {
        m_filename = package.get_attribute("test.event_log").Get<std::string>();
        m_package_name = package.get_name();
        record("native:init", package);
        const auto environment_variable = package.get_attribute("test.environment_variable");
        if (environment_variable.IsHolding<std::string>())
            std::ofstream(m_filename, std::ios::app) << "native:environment:" << get_env(environment_variable.Get<std::string>()) << '\n';
        const auto fail = package.get_attribute("test.fail_initialize");
        if (fail.IsHolding<bool>() && fail.Get<bool>())
            throw std::runtime_error("Native test initialization failed");
    }
    void uninitialize(const Package& package) override { record("native:uninit", package); }

private:
    std::string m_filename;
    std::string m_package_name;
    void record(const char* event, const Package& package)
    {
        const auto filename = package.get_attribute("test.event_log");
        if (filename.IsHolding<std::string>())
            std::ofstream(filename.Get<std::string>(), std::ios::app) << event << ':' << package.get_name() << '\n';
    }
};

OPENDCC_DEFINE_PACKAGE_ENTRY_POINT(LifecycleEntryPoint);

OPENDCC_NAMESPACE_CLOSE
