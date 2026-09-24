"""Task 3 acceptance tests for geometry-backed full-city output."""
from __future__ import annotations

import unittest
from collections.abc import Callable
from typing import Any, cast

from modeling.tokyo_nova import build, pipeline
from modeling.tokyo_nova.layout import build_layout


class FullCityTests(unittest.TestCase):
    def build_city(self) -> dict:
        city_builder = cast(Callable[[dict[str, Any]], dict[str, Any]] | None, getattr(build, "build_city", None))
        if city_builder is None:
            self.fail("build.build_city must emit the full city scene")
        return city_builder(build_layout())

    def test_emitted_city_has_facilities_interiors_distinct_buildings_props_and_access(self) -> None:
        city = self.build_city()

        # Assert on emitted MeshData/collider plans, not the descriptive layout registries.
        building_keys = city["building_geometry"]
        self.assertEqual(len(building_keys), 24)
        self.assertGreaterEqual(len({tuple(building_keys[key]["silhouette"]) for key in building_keys}), 18)
        self.assertGreaterEqual(len(city["facility_geometry"]), 12)
        self.assertIn("clothing_repair", city["facility_geometry"])
        self.assertGreaterEqual(len(city["accessible_interiors"]), 6)
        self.assertGreaterEqual(len(city["prop_geometry"]), 60)
        for kind, geometry in city["prop_geometry"].items():
            self.assertTrue(geometry["parts"], kind)
            self.assertGreater(geometry["triangles"], 0, kind)
        sea_screen_parts = city["prop_geometry"]["abstract_sea_screen"]["parts"]
        self.assertGreaterEqual(sum("sea_wave" in part for part in sea_screen_parts), 3)
        catalog = {asset["kind"]: asset for asset in city["asset_catalog"]}
        self.assertEqual(set(catalog), set(city["prop_geometry"]))
        for kind, asset in catalog.items():
            self.assertTrue(asset["dimensions"], kind)
            self.assertTrue(asset["parts"], kind)
            self.assertTrue(asset["materials"], kind)
            self.assertTrue(asset["wear_details"], kind)
            self.assertTrue(asset["placement"]["buildings"], kind)

        # Each hinged leaf must be physically attached at its actual front doorway, not stranded in the room.
        building_defs = {building["key"]: building for building in build_layout()["buildings"]}
        for building_key, building in building_defs.items():
            if building_key in {"north_yatai", "north_terminal_repair", "north_machiya"}:
                continue
            leaf = next(item for item in city["collision_geometry"] if item[0] == building_key and "open_door_leaf" in item[1])
            center = [(leaf[2][axis] + leaf[3][axis]) / 2 for axis in range(3)]
            if building["front"] in ("north", "south"):
                wall_z = float(building["center"][2]) + (float(building["size"][1]) / 2) * (1 if building["front"] == "north" else -1)
                self.assertLess(abs(center[2] - wall_z), 1.2, building_key)
            else:
                wall_x = float(building["center"][0]) + (float(building["size"][0]) / 2) * (1 if building["front"] == "east" else -1)
                self.assertLess(abs(center[0] - wall_x), 1.2, building_key)

        # Exact emitted structural collider bounds must leave the 20 m walking square open.
        for owner, part, minimum, maximum in city["collision_geometry"]:
            if maximum[1] > -2.2 and minimum[1] < 2.6 and maximum[0] > -10 and minimum[0] < 10 and maximum[2] > -10 and minimum[2] < 10:
                self.fail(f"visible collider {owner}/{part} intrudes into the clear plaza")

        for entrance in ("entrance_north", "entrance_east", "entrance_south", "entrance_west"):
            self.assertIn(entrance, city["accessibility"]["route_keys"])
        self.assertGreaterEqual(city["accessibility"]["loop_count"], 2)
        self.assertTrue(city["accessibility"]["roof_route_continuous"])
        for building in city["building_geometry"].values():
            if "door_clearance_verified_from_colliders" in building:
                self.assertTrue(building["door_clearance_verified_from_colliders"], building["building_key"])
                self.assertEqual(building["door_blocking_parts"], [], building["building_key"])
        for interior in city["accessible_interiors"].values():
            self.assertGreaterEqual(interior["door_width"], 0.9)
            self.assertGreater(interior["door_height"], 2.0)
            self.assertTrue(interior["door_opening_verified_from_meshes"])
            self.assertTrue(interior["door_clearance_verified_from_colliders"], interior["building_key"])
            self.assertEqual(interior["door_blocking_parts"], [], interior["building_key"])
            self.assertTrue(interior["entry_corridor_verified_from_props"], interior["building_key"])
            self.assertEqual(interior["entry_corridor_blocking_props"], [], interior["building_key"])
            self.assertTrue(interior["route_connected"])

    def test_actual_props_have_support_and_city_routes_use_continuous_walkable_colliders(self) -> None:
        city = self.build_city()
        assemblies = city["assemblies"]
        motorcycle = next(item for item in assemblies if item.name == "south_repair_yard_motorcycle_static")
        room = next(item for item in assemblies if item.kind == "interior_room" and item.name == "south_repair_yard")
        floor = next(part for part in room.parts if part.name == "south_repair_yard_room_floor")
        floor_top = max(vertex[1] for vertex in floor.vertices)
        self.assertAlmostEqual(motorcycle.bounds[0][1], floor_top, places=5)
        self.assertGreaterEqual(sum("tire" in part.name for part in motorcycle.parts), 2)
        self.assertTrue(any("engine" in part.name for part in motorcycle.parts))

        layout = build_layout()
        manifest = pipeline.build_blockout_manifest(layout)
        slots = {slot["slot"]["key"]: slot for slot in pipeline.iter_slots(manifest)}
        roof = slots["roof_access_ramp"]
        roof_collider = next(component for component in roof["components"] if component["type"] == "FrooxEngine.BoxCollider")
        self.assertTrue(roof_collider["fields"].get("Enabled", True))
        self.assertTrue(roof_collider["fields"]["CharacterCollider"])
        self.assertEqual(roof_collider["fields"]["Size"][0], 1.8)

        treads = [slots[f"west_bar_basement_stair_{index:02d}"] for index in range(12)]
        bounds = []
        for tread in treads:
            position = tread["slot"]["position"]
            collider = next(component for component in tread["components"] if component["type"] == "FrooxEngine.BoxCollider")
            size = collider["fields"]["Size"]
            self.assertTrue(collider["fields"].get("Enabled", True))
            self.assertTrue(collider["fields"]["CharacterCollider"])
            bounds.append(([position[0] - size[0] / 2, position[1] - size[1] / 2], [position[0] + size[0] / 2, position[1] + size[1] / 2]))
        for first, second in zip(sorted(bounds, key=lambda box: box[0][0]), sorted(bounds, key=lambda box: box[0][0])[1:]):
            self.assertAlmostEqual(first[1][0], second[0][0], places=6)
            self.assertAlmostEqual(first[1][1], second[0][1], places=6)

    def test_emitted_city_contains_owned_sky_signage_and_keeps_existing_global_sky_untouched(self) -> None:
        city = self.build_city()
        self.assertTrue(city["sky_geometry"]["inner_facing"])
        self.assertTrue(city["sky_geometry"]["owned_root_only"])
        self.assertFalse(city["sky_geometry"]["mutates_global_skybox"])
        self.assertGreater(city["sky_geometry"]["layer_count"], 2)
        self.assertGreater(city["lighting"]["local_light_count"], 0)
        self.assertLessEqual(city["lighting"]["local_light_count"], 24)
        light_names = [light["name"] for light in city["lighting"]["lights"]]
        self.assertEqual(len(light_names), len(set(light_names)))
        clinic = next(item for item in build_layout()["buildings"] if item["key"] == "east_clinic")
        clinic_light = next(light for light in city["lighting"]["lights"] if light["key"] == "city_light_03")
        self.assertLessEqual(abs(clinic_light["position"][0] - clinic["center"][0]), clinic["size"][0] / 2)
        self.assertLessEqual(abs(clinic_light["position"][2] - clinic["center"][2]), clinic["size"][1] / 2)

        signs = pipeline._city_facility_signage(build_layout())
        self.assertEqual(len(signs["children"]), 17)
        labels = {child["components"][0]["fields"]["Text"] for child in signs["children"]}
        self.assertIn("古着仕立て・縫い直し", labels)
        self.assertTrue(all(child["components"][0]["type"] == "FrooxEngine.TextRenderer" for child in signs["children"]))

    def test_city_manifest_disables_only_replaced_blockout_geometry_and_has_colliders_from_meshes(self) -> None:
        layout = build_layout()
        city = self.build_city()
        manifest = pipeline.build_city_manifest(layout, city)
        self.assertGreaterEqual(manifest["limits"]["expandedNodes"], 50000)
        managed = {slot["slot"]["key"]: slot for slot in pipeline.iter_slots(manifest)}
        for building in layout["buildings"]:
            old_renderer_enabled = []
            for slot in pipeline.iter_slots(manifest):
                if slot["slot"].get("key") == f"building_{building['key']}":
                    for nested in pipeline.iter_slots(slot):
                        old_renderer_enabled.extend(
                            component.get("fields", {}).get("Enabled")
                            for component in nested.get("components", [])
                            if component.get("type") in ("FrooxEngine.MeshRenderer", "FrooxEngine.BoxCollider")
                        )
            self.assertTrue(old_renderer_enabled, building["key"])
            if building["key"] in {"north_yatai", "north_terminal_repair", "north_machiya"}:
                self.assertFalse(any(value for slot in pipeline.iter_slots(manifest) if slot["slot"].get("key", "").startswith(("north_yatai_", "north_terminal_repair_", "north_machiya_")) and not slot["slot"].get("key", "").endswith("_floor") for component in slot.get("components", []) if component.get("type") in ("FrooxEngine.MeshRenderer", "FrooxEngine.BoxCollider") for value in [component.get("fields", {}).get("Enabled")]), building["key"])
            else:
                self.assertFalse(any(old_renderer_enabled), building["key"])
        colliders = [slot for slot in managed.values() if slot["slot"].get("key", "").startswith("city_collision_") and slot.get("components")]
        self.assertLessEqual(len(colliders), 24, "group static wall/floor collider components under stable per-building slots")
        collision_components = [component for slot in colliders for component in slot["components"]]
        self.assertGreater(len(collision_components), 1000)
        for component in collision_components:
            self.assertEqual(component["type"], "FrooxEngine.BoxCollider")
            self.assertTrue(component["fields"]["Enabled"])
            self.assertTrue(component["fields"]["CharacterCollider"])
            self.assertTrue(all(value > 0 for value in component["fields"]["Size"]))


if __name__ == "__main__":
    unittest.main()
