// Copyright Contributors to the OpenDCC project
// SPDX-License-Identifier: Apache-2.0

#include "opendcc/base/packaging/filesystem_package_provider.h"
#include <opendcc/base/packaging/toml_parser.h>
#include <pxr/base/tf/fileUtils.h>
#include "pxr/base/tf/pathUtils.h"
#include <filesystem>
#include "opendcc/base/logging/logger.h"

PXR_NAMESPACE_USING_DIRECTIVE
OPENDCC_NAMESPACE_OPEN

FileSystemPackageProvider::FileSystemPackageProvider()
{
    register_package_parser("toml", std::make_shared<TOMLParser>());
}

void FileSystemPackageProvider::fetch()
{
    m_cached_packages.clear();
    std::vector<std::string> glob_patterns;
    glob_patterns.reserve(m_package_directories.size() * m_package_parsers.size());

    for (const auto& dir : m_package_directories)
    {
        for (const auto& parser : m_package_parsers)
        {
            glob_patterns.push_back(dir + "/package" + parser.first);
        }
    }

    std::string glob_patterns_str = "[";
    if (glob_patterns.empty())
    {
        glob_patterns_str += "]";
    }
    else
    {
        for (const auto& pattern : glob_patterns)
        {
            glob_patterns_str += "\"" + pattern + "\", ";
        }
        glob_patterns_str += "]";
    }

    OPENDCC_INFO("Fetching packages from the following directories: {}", glob_patterns_str);

    const auto found_package_paths = TfGlob(glob_patterns, ARCH_GLOB_MARK);

    std::unordered_map<std::string, std::string> unique_packages;
    for (const auto& path : found_package_paths)
    {
        auto file_path = std::filesystem::u8path(path);
        auto parser = m_package_parsers[file_path.extension().u8string()];
        if (parser)
        {
            auto data = parser->parse(path);
            if (data)
            {
                auto unique_pkg = unique_packages.emplace(data.name, path);

                if (!unique_pkg.second)
                {
                    OPENDCC_WARN("Package with name '{}' ({}) was already discovered at path '{}'. Ignoring all duplicates.", data.name, path,
                                 unique_pkg.first->second);
                    continue;
                }

                m_cached_packages.push_back(std::move(data));
            }
        }
    }
}

const std::vector<PackageData>& FileSystemPackageProvider::get_cached_packages() const
{
    return m_cached_packages;
}

void FileSystemPackageProvider::register_package_parser(const std::string& extension, const std::shared_ptr<PackageParser>& parser)
{
    if (extension.empty())
    {
        OPENDCC_ERROR("Failed to register filesystem package parser: extension is empty.");
        return;
    }

    if (extension[0] != '.')
    {
        m_package_parsers['.' + extension] = parser;
    }
    else
    {
        m_package_parsers[extension] = parser;
    }
}

void FileSystemPackageProvider::add_path(const char* file_system_path)
{
    m_package_directories.push_back(file_system_path);
}

void FileSystemPackageProvider::remove_path(const char* file_system_path)
{
    auto it = std::find(m_package_directories.begin(), m_package_directories.end(), std::string(file_system_path));
    if (it == m_package_directories.end())
    {
        return;
    }
    m_package_directories.erase(it);
}

OPENDCC_NAMESPACE_CLOSE
