"""Tests for test views to ensure they all work correctly."""

from __future__ import annotations

from django.test import TestCase, override_settings

from ..management.commands.seed_testdata import seed_test_data


@override_settings(ROOT_URLCONF="recipes.tests.test_urls_testviews")
class TestViewsStatusCodeTest(TestCase):
    """Test that all test views return 200 status codes."""

    def setUp(self) -> None:
        """Seed the database with test data."""
        seed_test_data()

    def test_testviews_index(self) -> None:
        """Test the test views index page."""
        response = self.client.get("/testviews/")
        self.assertEqual(response.status_code, 200)

    def test_recipe_list_views(self) -> None:
        """Test all recipe list test views."""
        test_urls = [
            "/testviews/recipes/empty/",
            "/testviews/recipes/one/",
            "/testviews/recipes/three/",
            "/testviews/recipes/many/",
        ]
        for url in test_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(
                    response.status_code,
                    200,
                    f"Failed for {url}: {response.status_code}",
                )

    def test_recipe_detail_views(self) -> None:
        """Test recipe detail test views."""
        test_urls = [
            "/testviews/recipes/detail/",
            "/testviews/recipes/cooking/",
        ]
        for url in test_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(
                    response.status_code,
                    200,
                    f"Failed for {url}: {response.status_code}",
                )

    def test_recipe_edit_view(self) -> None:
        """Test recipe edit view (redirects to actual edit page)."""
        response = self.client.get("/testviews/recipes/edit/")
        # This should redirect to the edit page
        self.assertEqual(response.status_code, 302)

    def test_collection_list_views(self) -> None:
        """Test all collection list test views."""
        test_urls = [
            "/testviews/collections/empty/",
            "/testviews/collections/one/",
            "/testviews/collections/three/",
            "/testviews/collections/many/",
        ]
        for url in test_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(
                    response.status_code,
                    200,
                    f"Failed for {url}: {response.status_code}",
                )

    def test_collection_detail_views(self) -> None:
        """Test collection detail test views."""
        test_urls = [
            "/testviews/collections/detail-empty/",
            "/testviews/collections/detail/",
        ]
        for url in test_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(
                    response.status_code,
                    200,
                    f"Failed for {url}: {response.status_code}",
                )

    def test_meal_plan_list_views(self) -> None:
        """Test all meal plan list test views."""
        test_urls = [
            "/testviews/meal-plans/empty/",
            "/testviews/meal-plans/one/",
            "/testviews/meal-plans/three/",
            "/testviews/meal-plans/many/",
        ]
        for url in test_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(
                    response.status_code,
                    200,
                    f"Failed for {url}: {response.status_code}",
                )

    def test_meal_plan_detail_views(self) -> None:
        """Test meal plan detail test views."""
        test_urls = [
            "/testviews/meal-plans/detail-empty/",
            "/testviews/meal-plans/detail/",
        ]
        for url in test_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(
                    response.status_code,
                    200,
                    f"Failed for {url}: {response.status_code}",
                )

    def test_shopping_list_view(self) -> None:
        """Test shopping list test view."""
        response = self.client.get("/testviews/meal-plans/shopping-list/")
        self.assertEqual(response.status_code, 200)

    def test_job_list_views(self) -> None:
        """Test all job list test views."""
        test_urls = [
            "/testviews/jobs/empty/",
            "/testviews/jobs/one/",
            "/testviews/jobs/three/",
            "/testviews/jobs/many/",
        ]
        for url in test_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(
                    response.status_code,
                    200,
                    f"Failed for {url}: {response.status_code}",
                )

    def test_job_detail_views(self) -> None:
        """Test job detail test views."""
        test_urls = [
            "/testviews/jobs/detail/pending/",
            "/testviews/jobs/detail/running/",
            "/testviews/jobs/detail/completed/",
            "/testviews/jobs/detail/failed/",
            "/testviews/jobs/detail/cancelled/",
        ]
        for url in test_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(
                    response.status_code,
                    200,
                    f"Failed for {url}: {response.status_code}",
                )

    def test_all_testviews_return_200(self) -> None:
        """Comprehensive test that all test views return 200 or expected redirect."""
        # All URLs that should return 200
        urls_200 = [
            "/testviews/",
            "/testviews/recipes/empty/",
            "/testviews/recipes/one/",
            "/testviews/recipes/three/",
            "/testviews/recipes/many/",
            "/testviews/recipes/detail/",
            "/testviews/recipes/cooking/",
            "/testviews/collections/empty/",
            "/testviews/collections/one/",
            "/testviews/collections/three/",
            "/testviews/collections/many/",
            "/testviews/collections/detail-empty/",
            "/testviews/collections/detail/",
            "/testviews/meal-plans/empty/",
            "/testviews/meal-plans/one/",
            "/testviews/meal-plans/three/",
            "/testviews/meal-plans/many/",
            "/testviews/meal-plans/detail-empty/",
            "/testviews/meal-plans/detail/",
            "/testviews/meal-plans/shopping-list/",
            "/testviews/jobs/empty/",
            "/testviews/jobs/one/",
            "/testviews/jobs/three/",
            "/testviews/jobs/many/",
            "/testviews/jobs/detail/pending/",
            "/testviews/jobs/detail/running/",
            "/testviews/jobs/detail/completed/",
            "/testviews/jobs/detail/failed/",
            "/testviews/jobs/detail/cancelled/",
        ]

        # URLs that should redirect
        urls_redirect = ["/testviews/recipes/edit/"]

        for url in urls_200:
            with self.subTest(url=url, expected=200):
                response = self.client.get(url)
                self.assertEqual(
                    response.status_code,
                    200,
                    f"{url} returned {response.status_code} instead of 200",
                )

        for url in urls_redirect:
            with self.subTest(url=url, expected=302):
                response = self.client.get(url)
                self.assertEqual(
                    response.status_code,
                    302,
                    f"{url} returned {response.status_code} instead of 302",
                )
