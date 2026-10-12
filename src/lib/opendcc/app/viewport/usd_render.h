/*
 * Copyright Contributors to the OpenDCC project
 * SPDX-License-Identifier: Apache-2.0
 */

#pragma once

#include "opendcc/render_system/irender.h"
#include "opendcc/base/vendor/tiny_process/process.hpp"
#include "opendcc/usd/usd_live_share/live_share_session.h"
#include "opendcc/render_view/display_driver_api/display_driver_api.h"
#include "opendcc/app/ui/logger/render_catalog.h"
#include "opendcc/app/viewport/offscreen_render.h"

#include <filesystem>
#include "opendcc/app/viewport/render_process.h"

#include <QObject>

#include <mutex>
#include <future>

OPENDCC_NAMESPACE_OPEN

class ViewportRenderAOVs;
class ViewportWidget;
class LiveShareSession;
class RenderProcess;

class OPENDCC_API UsdRender
    : public render_system::IRender
    , public std::enable_shared_from_this<UsdRender>
{
public:
    using RenderCmdFn = std::function<std::string()>;
    UsdRender(const RenderCmdFn& render_cmd);
    ~UsdRender() override;
    virtual void set_attributes(const render_system::RenderAttributes& attributes) override;
    virtual bool init_render(render_system::RenderMethod type) override;
    virtual bool start_render() override;
    virtual bool pause_render() override;
    virtual bool resume_render() override;
    virtual bool stop_render() override;
    virtual void update_render() override;
    virtual void wait_render() override;
    virtual render_system::RenderStatus render_status() override;
    virtual void finished(std::function<void(render_system::RenderStatus)> cb) override;

private:
    bool start_render_impl();

    void update_render_cmd(const std::string& stage_path, const std::string& transfer_layer_cfg);
    void init_temp_dir();
    std::filesystem::path write_transfer_layers() const;
    void create_render_catalog();

    QMetaObject::Connection m_connect;
    render_system::RenderAttributes m_attributes;
    std::filesystem::path m_tmp_dir;
    std::unique_ptr<ViewportOffscreenRender> m_render;
    std::unique_ptr<display_driver_api::RenderViewConnection> m_render_view_connection;
    std::shared_ptr<ViewportRenderAOVs> m_processor;
    std::unordered_map<std::string, int32_t> m_image_handles;
    std::string m_render_cmd;
    render_system::RenderMethod m_render_method = render_system::RenderMethod::NONE;

    struct LogData
    {
        std::string catalog;
        CatalogDataPtr catalog_data;
    };
    LogData m_log_data;

    std::unique_ptr<RenderProcess> m_render_process;
    std::unique_ptr<LiveShareSession> m_live_share;
    RenderCmdFn m_render_cmd_fn;
};

OPENDCC_NAMESPACE_CLOSE
