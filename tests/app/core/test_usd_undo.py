# Copyright Contributors to the OpenDCC project
# SPDX-License-Identifier: Apache-2.0

import unittest

import opendcc.core as core
from pxr import Sdf, Usd


class TestUsdUndo(unittest.TestCase):
    UNDO_REDO_CYCLES = 3

    def setUp(self):
        self.app = core.Application.instance()
        self.assertTrue(self.app.is_ui_available())
        self.session = self.app.get_session()
        self.stack = self.app.get_undo_stack()
        enabled, limit = self.stack.is_enabled(), self.stack.get_undo_limit()
        self.addCleanup(self.stack.set_enabled, enabled)
        self.addCleanup(self.stack.set_undo_limit, limit)
        self.stack.set_enabled(True)
        # Keep every edit available for undo; zero means unlimited history.
        self.stack.set_undo_limit(0)
        self.stack.clear()
        self.stage = Usd.Stage.CreateInMemory()
        self.session.set_current_stage(self.stage)
        self.addCleanup(self.session.close_stage, self.stage)
        self.addCleanup(self.stack.clear)

    def snapshot_layers(self):
        return tuple(layer.ExportToString() for layer in self.stage.GetLayerStack())

    def assert_undo_redo_restores_layers(self, before, after):
        self.assertNotEqual(before, after)
        history_size = self.stack.get_size()
        self.assertEqual(history_size, 1)
        for _ in range(self.UNDO_REDO_CYCLES):
            self.stack.undo()
            self.assertEqual(self.snapshot_layers(), before)
            self.assertFalse(self.stack.can_undo())
            self.assertTrue(self.stack.can_redo())
            self.stack.redo()
            self.assertEqual(self.snapshot_layers(), after)
            self.assertTrue(self.stack.can_undo())
            self.assertFalse(self.stack.can_redo())
            self.assertEqual(self.stack.get_size(), history_size)

    def test_create_and_delete_prim_subtree(self):
        before = self.snapshot_layers()
        with core.UsdEditsUndoBlock():
            prim = self.stage.DefinePrim("/World/Child", "Xform")
            prim.CreateAttribute("value", Sdf.ValueTypeNames.Double).Set(7.0)
        self.assert_undo_redo_restores_layers(before, self.snapshot_layers())
        self.stack.clear()
        before = self.snapshot_layers()
        with core.UsdEditsUndoBlock():
            self.assertTrue(self.stage.RemovePrim("/World"))
        self.assert_undo_redo_restores_layers(before, self.snapshot_layers())

    def test_default_value_and_time_samples(self):
        prim = self.stage.DefinePrim("/World", "Xform")
        attribute = prim.CreateAttribute("value", Sdf.ValueTypeNames.Double)
        attribute.Set(1.0)
        attribute.Set(2.0, 1)
        self.stack.clear()
        before = self.snapshot_layers()
        with core.UsdEditsUndoBlock():
            attribute.Set(3.0)
            attribute.Set(4.0, 1)
            attribute.Set(5.0, 2)
        self.assert_undo_redo_restores_layers(before, self.snapshot_layers())
        self.assertEqual(attribute.Get(), 3.0)
        self.assertEqual(attribute.GetTimeSamples(), [1.0, 2.0])

    def test_relationship_targets(self):
        prim = self.stage.DefinePrim("/World")
        relationship = prim.CreateRelationship("targets")
        relationship.SetTargets([Sdf.Path("/Old")])
        self.stack.clear()
        before = self.snapshot_layers()
        with core.UsdEditsUndoBlock():
            relationship.SetTargets([Sdf.Path("/First"), Sdf.Path("/Second")])
        self.assert_undo_redo_restores_layers(before, self.snapshot_layers())
        self.assertEqual(relationship.GetTargets(), [Sdf.Path("/First"), Sdf.Path("/Second")])

    def test_sublayer_edit_restores_only_authored_layer(self):
        sublayer = Sdf.Layer.CreateAnonymous("undo-sublayer.usda")
        root = self.stage.GetRootLayer()
        root.subLayerPaths.append(sublayer.identifier)
        self.stage.SetEditTarget(sublayer)
        self.stack.clear()
        root_before = root.ExportToString()
        before = self.snapshot_layers()
        with core.UsdEditsUndoBlock():
            self.stage.DefinePrim("/InSublayer", "Xform")
        self.assert_undo_redo_restores_layers(before, self.snapshot_layers())
        self.assertEqual(root.ExportToString(), root_before)
        self.assertIsNotNone(sublayer.GetPrimAtPath("/InSublayer"))
        self.assertEqual(self.stage.GetEditTarget().GetLayer(), sublayer)

    def test_nested_blocks_make_one_entry_and_empty_blocks_make_none(self):
        before = self.snapshot_layers()
        with core.UsdEditsUndoBlock():
            with core.UsdEditsUndoBlock():
                pass
        self.assertEqual(self.stack.get_size(), 0)
        with core.UsdEditsUndoBlock():
            self.stage.DefinePrim("/First")
            with core.UsdEditsUndoBlock():
                self.stage.DefinePrim("/Second")
            self.assertEqual(self.stack.get_size(), 0)
        self.assert_undo_redo_restores_layers(before, self.snapshot_layers())

    def test_exception_closes_block_without_rolling_back_edits(self):
        before = self.snapshot_layers()
        with self.assertRaisesRegex(RuntimeError, "test interruption"):
            with core.UsdEditsUndoBlock():
                self.stage.DefinePrim("/BeforeException")
                raise RuntimeError("test interruption")
        self.assert_undo_redo_restores_layers(before, self.snapshot_layers())
        self.stack.clear()
        with core.UsdEditsUndoBlock():
            self.stage.DefinePrim("/AfterException")
        self.assertEqual(self.stack.get_size(), 1)
