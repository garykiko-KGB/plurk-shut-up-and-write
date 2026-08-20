import unittest

from core.activity import Activity, ActivityConfig
from core.activity_manager import ActivityManager


class TestActivityManager(unittest.TestCase):
    """Tests for the ActivityManager."""

    def setUp(self) -> None:
        self.manager = ActivityManager()

        self.activity_1 = Activity(
            owner_user_id=1001,
            source_plurk_id=2001,
        )

        self.activity_2 = Activity(
            owner_user_id=1002,
            source_plurk_id=2002,
        )

        self.activity_3 = Activity(
            owner_user_id=1001,
            source_plurk_id=2003,
            config=ActivityConfig(
                work_time=20,
                break_time=10,
                rounds=6,
                prepare_time=3,
            ),
        )

    # --------------------------------------------------
    # Initialization
    # --------------------------------------------------

    def test_manager_starts_empty(self) -> None:
        self.assertEqual(
            self.manager.count(),
            0,
        )

        self.assertEqual(
            self.manager.get_all(),
            [],
        )

    # --------------------------------------------------
    # Add
    # --------------------------------------------------

    def test_add_activity(self) -> None:
        self.manager.add(self.activity_1)

        self.assertEqual(
            self.manager.count(),
            1,
        )

        self.assertIs(
            self.manager.get(2001),
            self.activity_1,
        )

    def test_add_multiple_activities(self) -> None:
        self.manager.add(self.activity_1)
        self.manager.add(self.activity_2)

        self.assertEqual(
            self.manager.count(),
            2,
        )

        self.assertIs(
            self.manager.get(2001),
            self.activity_1,
        )

        self.assertIs(
            self.manager.get(2002),
            self.activity_2,
        )

    def test_add_duplicate_source_plurk_raises_error(self) -> None:
        self.manager.add(self.activity_1)

        duplicate = Activity(
            owner_user_id=9999,
            source_plurk_id=2001,
        )

        with self.assertRaises(ValueError):
            self.manager.add(duplicate)

        self.assertEqual(
            self.manager.count(),
            1,
        )

        self.assertIs(
            self.manager.get(2001),
            self.activity_1,
        )

    # --------------------------------------------------
    # Get
    # --------------------------------------------------

    def test_get_existing_activity(self) -> None:
        self.manager.add(self.activity_1)

        result = self.manager.get(2001)

        self.assertIs(
            result,
            self.activity_1,
        )

    def test_get_missing_activity_returns_none(self) -> None:
        result = self.manager.get(9999)

        self.assertIsNone(
            result
        )

    # --------------------------------------------------
    # Exists
    # --------------------------------------------------

    def test_exists_returns_true_for_existing_activity(self) -> None:
        self.manager.add(self.activity_1)

        self.assertTrue(
            self.manager.exists(2001)
        )

    def test_exists_returns_false_for_missing_activity(self) -> None:
        self.assertFalse(
            self.manager.exists(9999)
        )

    # --------------------------------------------------
    # Get by owner
    # --------------------------------------------------

    def test_get_by_owner_returns_matching_activities(self) -> None:
        self.manager.add(self.activity_1)
        self.manager.add(self.activity_2)
        self.manager.add(self.activity_3)

        result = self.manager.get_by_owner(1001)

        self.assertEqual(
            len(result),
            2,
        )

        self.assertIn(
            self.activity_1,
            result,
        )

        self.assertIn(
            self.activity_3,
            result,
        )

        self.assertNotIn(
            self.activity_2,
            result,
        )

    def test_get_by_owner_returns_empty_list_when_none_exist(self) -> None:
        self.manager.add(self.activity_1)

        result = self.manager.get_by_owner(9999)

        self.assertEqual(
            result,
            [],
        )

    # --------------------------------------------------
    # Get all
    # --------------------------------------------------

    def test_get_all_returns_all_activities(self) -> None:
        self.manager.add(self.activity_1)
        self.manager.add(self.activity_2)
        self.manager.add(self.activity_3)

        result = self.manager.get_all()

        self.assertEqual(
            len(result),
            3,
        )

        self.assertIn(
            self.activity_1,
            result,
        )

        self.assertIn(
            self.activity_2,
            result,
        )

        self.assertIn(
            self.activity_3,
            result,
        )

    # --------------------------------------------------
    # Remove
    # --------------------------------------------------

    def test_remove_existing_activity(self) -> None:
        self.manager.add(self.activity_1)
        self.manager.add(self.activity_2)

        removed = self.manager.remove(2001)

        self.assertIs(
            removed,
            self.activity_1,
        )

        self.assertEqual(
            self.manager.count(),
            1,
        )

        self.assertIsNone(
            self.manager.get(2001)
        )

        self.assertIs(
            self.manager.get(2002),
            self.activity_2,
        )

    def test_remove_missing_activity_returns_none(self) -> None:
        removed = self.manager.remove(9999)

        self.assertIsNone(
            removed
        )

        self.assertEqual(
            self.manager.count(),
            0,
        )

    def test_removed_activity_can_be_added_again(self) -> None:
        self.manager.add(self.activity_1)

        removed = self.manager.remove(2001)

        self.assertIs(
            removed,
            self.activity_1,
        )

        self.manager.add(self.activity_1)

        self.assertIs(
            self.manager.get(2001),
            self.activity_1,
        )

        self.assertEqual(
            self.manager.count(),
            1,
        )

    # --------------------------------------------------
    # Clear
    # --------------------------------------------------

    def test_clear_removes_all_activities(self) -> None:
        self.manager.add(self.activity_1)
        self.manager.add(self.activity_2)
        self.manager.add(self.activity_3)

        self.manager.clear()

        self.assertEqual(
            self.manager.count(),
            0,
        )

        self.assertEqual(
            self.manager.get_all(),
            [],
        )

    # --------------------------------------------------
    # Manager does not alter activity state
    # --------------------------------------------------

    def test_add_does_not_change_activity_state(self) -> None:
        self.manager.add(self.activity_1)

        self.assertEqual(
            self.activity_1.current_round,
            0,
        )

        self.assertEqual(
            self.activity_1.status.value,
            "preparing",
        )

    def test_get_returns_same_activity_object(self) -> None:
        self.manager.add(self.activity_1)

        result = self.manager.get(2001)

        self.assertIs(
            result,
            self.activity_1,
        )


if __name__ == "__main__":
    unittest.main()
