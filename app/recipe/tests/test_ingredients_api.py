from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Ingredient, Recipe
from recipe.serializers import IngredientSerializer

INGREDIENTS_URL = reverse('recipe:ingredient-list')


class PublicIngredientsApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_login_required(self):
        response = self.client.get(INGREDIENTS_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientsApiTests(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='test@example.com',
            password='Qwerty123',
            name='John'
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_ingredient_list(self):
        Ingredient.objects.create(user=self.user, name='Cucumber')
        Ingredient.objects.create(user=self.user, name='Potato')

        response = self.client.get(INGREDIENTS_URL)
        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_ingredients_limited_to_user(self):
        user2 = get_user_model().objects.create_user(
            name='Test',
            email='testanother@example.com',
            password='passpass1234'
        )
        ingredient = Ingredient.objects.create(user=self.user,
                                               name='Salt')
        Ingredient.objects.create(user=user2,
                                  name='Garlic')
        response = self.client.get(INGREDIENTS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], ingredient.name)

    def test_create_ingredient_successful(self):
        payload = {'name': 'Herring'}
        response = self.client.post(INGREDIENTS_URL, payload)

        exists = Ingredient.objects.filter(
            user=self.user,
            name=payload['name']
        ).exists()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(exists)

    def test_create_ingredient_invalid(self):
        response = self.client.post(INGREDIENTS_URL, {'name': ''})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filter_assigned_only_ingredients(self):
        ingredient1 = Ingredient.objects.create(user=self.user, name='Garlic')
        ingredient2 = Ingredient.objects.create(user=self.user, name='Cabbage')
        recipe = Recipe.objects.create(
            user=self.user,
            title='Fried eggs',
            time_minutes=3,
            price=1.00
        )
        recipe.ingredients.add(ingredient1)

        response = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})
        serializer1 = IngredientSerializer(ingredient1)
        serializer2 = IngredientSerializer(ingredient2)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, response.data)
        self.assertNotIn(serializer2.data, response.data)

    def test_retrieve_ingredients_assigned_unique(self):
        ingredient = Ingredient.objects.create(user=self.user, name='Butter')
        Ingredient.objects.create(user=self.user, name='Bread')
        recipe1 = Recipe.objects.create(
            user=self.user,
            title='Fried eggs',
            time_minutes=3,
            price=1.00
        )
        recipe2 = Recipe.objects.create(
            user=self.user,
            title='Chicken curry',
            time_minutes=40,
            price=12.00
        )
        recipe1.ingredients.add(ingredient)
        recipe2.ingredients.add(ingredient)
        response = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
