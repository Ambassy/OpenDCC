/*
 * Copyright Contributors to the OpenDCC project
 * SPDX-License-Identifier: Apache-2.0
 */

#pragma once
#include "opendcc/opendcc.h"
#include "opendcc/app/core/api.h"
#include "opendcc/app/viewport/viewport_view.h"
#include <functional>
#include <pxr/base/tf/token.h>
#include <string>
#include <unordered_map>
#include <QMouseEvent>
#include <unordered_set>

class QWidget;
class QKeyEvent;
class QAction;
class QCursor;

OPENDCC_NAMESPACE_OPEN
class ViewportGLWidget;
class ViewportUiDrawManager;
class PrimMaterialOverride;

class ViewportMouseEvent
{
public:
    ViewportMouseEvent(int x, int y, const QPoint& global_pos, Qt::MouseButton button, Qt::MouseButtons buttons, Qt::KeyboardModifiers modifiers)
        : m_x(x)
        , m_y(y)
        , m_global_pos(global_pos)
        , m_button(button)
        , m_buttons(buttons)
        , m_modifiers(modifiers)
    {
    }
    int x() const { return m_x; }
    int y() const { return m_y; }
    QPoint global_pos() const { return m_global_pos; }
    Qt::MouseButton button() const { return m_button; }
    Qt::MouseButtons buttons() const { return m_buttons; }
    Qt::KeyboardModifiers modifiers() const { return m_modifiers; }

private:
    int m_x = 0;
    int m_y = 0;
    QPoint m_global_pos;
    Qt::MouseButton m_button = Qt::MouseButton::NoButton;
    Qt::MouseButtons m_buttons = Qt::NoButton;
    Qt::KeyboardModifiers m_modifiers = Qt::NoModifier;
};

/**
 * @brief The IViewportToolContext is a base ToolContext class.
 * It allows to create custom Tool Contexts.
 *
 * Tool context provides interaction with a viewport
 * by overriding it's mouse and keyboard event handlers.
 *
 * This class allows to redefine the default key actions for the specific tool.
 *
 * @note Each viewport instance shares only one instance of the ToolContext.
 *
 */
class OPENDCC_API IViewportToolContext
{
public:
    IViewportToolContext() {}
    virtual ~IViewportToolContext() {}

    /**
     * @brief The event on the mouse button pressing.
     *
     * @param mouse_event The information about the mouse event.
     * @param viewport_view The ViewportView for which to handle the event.
     * It contains the data about the viewport state and allows to manipulate it.
     * @param draw_manager //This parameter isn't used in this method.
     * Using it is not safe. This API will be changed in the future//
     * @return true if the event was successfully handled.
     * @return false if the event wasn't handled.
     *
     * @note Allows to handle only the left and middle mouse button pressing events.
     * The right mouse button is reserved.
     *
     */
    virtual bool on_mouse_press(const ViewportMouseEvent& mouse_event, const ViewportViewPtr& viewport_view, ViewportUiDrawManager* draw_manager)
    {
        return false;
    };
    /**
     * @brief The event on the mouse button double clicking.
     *
     * @param mouse_event The information about the mouse event.
     * @param viewport_view The ViewportView for which to handle the event.
     * It contains the data about the viewport state and allows to manipulate it.
     * @param draw_manager //This parameter isn't used in this method.
     * Using it is not safe. This API will be changed in the future//
     * @return true if the event was successfully handled.
     * @return false if the event wasn't handled.
     *
     * @note Allows to handle only the left and middle mouse button pressing events.
     * The right mouse button is reserved.
     *
     */
    virtual bool on_mouse_double_click(const ViewportMouseEvent& mouse_event, const ViewportViewPtr& viewport_view,
                                       ViewportUiDrawManager* draw_manager)
    {
        return on_mouse_press(mouse_event, viewport_view, draw_manager);
    };
    /**
     * @brief The event on the mouse move.
     *
     * @param mouse_event The information about the mouse move.
     * @param viewport_view The ViewportView for which to handle the event.
     * It contains the data about the viewport state and allows to manipulate it.
     * @param draw_manager //This parameter isn't used in this method.
     * Using it is not safe. This API will be changed in the future//
     * @return true if the event was successfully handled.
     * @return false if the event wasn't handled.
     */
    virtual bool on_mouse_move(const ViewportMouseEvent& mouse_event, const ViewportViewPtr& viewport_view, ViewportUiDrawManager* draw_manager)
    {
        return false;
    };
    /**
     * @brief The event on the mouse release.
     *
     * @param mouse_event The information about the mouse release.
     * @param viewport_view The ViewportView for which to handle the event.
     * It contains the data about the viewport state and allows to manipulate it.
     * @param draw_manager //This parameter isn't used in this method.
     * Using it is not safe. This API will be changed in the future//
     * @return true if the event was successfully handled.
     * @return false if the event wasn't handled.
     *
     * @note Allows to handle only the left and middle mouse button pressing events.
     * The right mouse button is reserved.
     *
     */
    virtual bool on_mouse_release(const ViewportMouseEvent& mouse_event, const ViewportViewPtr& viewport_view, ViewportUiDrawManager* draw_manager)
    {
        return false;
    };
    /**
     * @brief The event on the key press.
     *
     * @param key_event The QkeyEvent information about the key press.
     * @param viewport_view The ViewportView for which to handle the event.
     * It contains the data about the viewport state and allows to manipulate it.
     * @param draw_manager //This parameter isn't used in this method.
     * Using it is not safe. This API will be changed in the future//
     * @return true if the event was successfully handled.
     * @return false if the event wasn't handled.
     */
    virtual bool on_key_press(QKeyEvent* key_event, const ViewportViewPtr& viewport_view, ViewportUiDrawManager* draw_manager) { return false; };
    /**
     * @brief The event on the key release.
     *
     * @param key_event The QkeyEvent information about the key release.
     * @param viewport_view The ViewportView for which to handle the event.
     * It contains the data about the viewport state and allows to manipulate it.
     * @param draw_manager //This parameter isn't used in this method.
     * Using it is not safe. This API will be changed in the future//
     * @return true if the event was successfully handled.
     * @return false if the event wasn't handled.
     */
    virtual bool on_key_release(QKeyEvent* key_event, const ViewportViewPtr& viewport_view, ViewportUiDrawManager* draw_manager) { return false; };
    /**
     * @brief A virtual method which allows to draw simple geometry for the specified ViewportView.
     *
     * @param viewport_view The ViewportView for which to handle the event.
     * It contains the data about the viewport state and allows to manipulate it.
     * @param draw_manager The UI Draw manager which is used for drawing simple geometry.
     * Calling this method takes place after the hydra engine's execution.
     *
     * @note Using ViewportUiDrawManager is safe only inside this method.
     *
     */
    virtual void draw(const ViewportViewPtr& viewport_view, ViewportUiDrawManager* draw_manager) {};
    /**
     * @brief A virtual method which allows to redefine the specified prim material.
     *
     * @return A set of the prim paths and the materials assigned for them as a value of the PrimMaterialOverride class.
     *
     * @note This is an experimental feature which can be used only in the USD context.
     *
     */
    virtual std::shared_ptr<PrimMaterialOverride> get_prim_material_override() { return nullptr; }
    /**
     * @brief Returns the name of the tool context.
     *
     */
    virtual PXR_NS::TfToken get_name() const = 0;
    /**
     * @brief Redefines the current cursor.
     *
     * @return Overridden QCursor* or nullptr if redefining isn't required.
     *
     * @note On changing the tool context, the cursor is set to default.
     */
    virtual QCursor* get_cursor() { return nullptr; };
};

class OPENDCC_API ViewportToolContextRegistry
{
public:
    using ViewportToolContextRegistryCallback = std::function<IViewportToolContext*()>;

    static IViewportToolContext* create_tool_context(const PXR_NS::TfToken& context, const PXR_NS::TfToken& name);
    static bool register_tool_context(const PXR_NS::TfToken& context, const PXR_NS::TfToken& name, ViewportToolContextRegistryCallback callback);
    static bool unregister_tool_context(const PXR_NS::TfToken& context, const PXR_NS::TfToken& name);

private:
    ViewportToolContextRegistry() = default;
    ~ViewportToolContextRegistry() = default;
    ViewportToolContextRegistry(const ViewportToolContextRegistry&) = delete;
    ViewportToolContextRegistry(ViewportToolContextRegistry&&) = delete;
    ViewportToolContextRegistry& operator=(const ViewportToolContextRegistry&) = delete;
    ViewportToolContextRegistry& operator=(ViewportToolContextRegistry&&) = delete;

    static ViewportToolContextRegistry& instance();

    std::unordered_map<PXR_NS::TfToken, std::unordered_map<PXR_NS::TfToken, ViewportToolContextRegistryCallback, PXR_NS::TfToken::HashFunctor>,
                       PXR_NS::TfToken::HashFunctor>
        m_registry_map;
};
OPENDCC_NAMESPACE_CLOSE
