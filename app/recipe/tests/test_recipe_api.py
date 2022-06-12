import os
import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe, Tag, Ingredient
from recipe.serializers import RecipeSerializer, RecipeDetailSerializer

RECIPE_URL = reverse('recipe:recipe-list')


def image_upload_url(recipe_id):
    return reverse('recipe:recipe-upload-image', args=[recipe_id])


def detail_url(recipe_id):
    return reverse('recipe:recipe-detail', args=[recipe_id])


def sample_recipe(user, **params):
    defaults = {
        'title': 'Borsch',
        'time_minutes': 30,
        'price': 7.99
    }
    defaults.update(params)
    return Recipe.objects.create(user=user, **defaults)


def sample_tag(user, name='Sample tag'):
    return Tag.objects.create(user=user, name=name)


def sample_ingredient(user, name='Cinnamon'):
    return Ingredient.objects.create(user=user, name=name)


class PublicRecipeApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_login_required(self):
        response = self.client.get(RECIPE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTests(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='test@example.com',
            password='Qwerty123',
            name='John'
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        sample_recipe(user=self.user)
        sample_recipe(user=self.user,
                      title='Risotto',
                      time_minutes=20,
                      price=8.30,
                      )

        response = self.client.get(RECIPE_URL)
        recipe_list = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipe_list, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_recipes_limited_to_user(self):
        user2 = get_user_model().objects.create_user(
            name='Test',
            email='testanother@example.com',
            password='passpass1234'
        )
        recipe = sample_recipe(user=self.user)
        sample_recipe(user=user2,
                      title='Risotto',
                      time_minutes=20,
                      price=8.30,
                      )
        response = self.client.get(RECIPE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], recipe.title)

    def test_view_recipe_detail(self):
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))
        recipe.ingredients.add(sample_ingredient(user=self.user))

        response = self.client.get(detail_url(recipe.id))
        serializer = RecipeDetailSerializer(recipe)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_recipe_successful(self):
        payload = {
            'title': 'Borsch',
            'time_minutes': 30,
            'price': 7.00
        }
        response = self.client.post(RECIPE_URL, payload)

        recipe = Recipe.objects.get(id=response.data['id'])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for key in payload.keys():
            self.assertEqual(payload[key], getattr(recipe, key))

    def test_create_recipe_with_tag_successful(self):
        tag1 = sample_tag(user=self.user, name='Vegan')
        tag2 = sample_tag(user=self.user, name='Dessert')
        payload = {
            'title': 'Borsch',
            'time_minutes': 30,
            'price': 7.00,
            'tags': [tag1.id, tag2.id]
        }
        response = self.client.post(RECIPE_URL, payload)

        recipe = Recipe.objects.get(id=response.data['id'])
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        tags = recipe.tags.all()
        self.assertIn(tag1, tags)
        self.assertIn(tag2, tags)

    def test_create_recipe_with_ingredient_successful(self):
        ingredient1 = sample_ingredient(user=self.user, name='Garlic')
        ingredient2 = sample_ingredient(user=self.user, name='Onion')
        payload = {
            'title': 'Borsch',
            'time_minutes': 30,
            'price': 7.00,
            'ingredients': [ingredient1.id, ingredient2.id]
        }
        response = self.client.post(RECIPE_URL, payload)

        recipe = Recipe.objects.get(id=response.data['id'])
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        ingredients = recipe.ingredients.all()
        self.assertIn(ingredient1, ingredients)
        self.assertIn(ingredient2, ingredients)

    def test_partial_update_recipes(self):
        recipe = sample_recipe(user=self.user)
        payload = {'title': 'Updated Title'}
        response = self.client.patch(detail_url(recipe.id), payload)
        recipe.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.title, payload['title'])

    def test_full_update_recipes(self):
        recipe = sample_recipe(user=self.user)
        payload = {
            'title': 'Updated Title',
            'time_minutes': 42,
            'price': 3
        }
        response = self.client.put(detail_url(recipe.id), payload)
        recipe.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for key in payload.keys():
            self.assertEqual(getattr(recipe, key), payload[key])


class RecipeImageUploadTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email='test@example',
            password='Qwerty123',
            name='John'
        )
        self.client.force_authenticate(self.user)
        self.recipe = sample_recipe(user=self.user)

    def tearDown(self):
        self.recipe.image.delete()

    def test_upload_image_to_recipe(self):
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as file:
            img = Image.new('RGB', (10, 10))
            img.save(file, 'JPEG')
            file.seek(0)
            response = self.client.post(url, {'image': file},
                                        format='multipart')
        self.recipe.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('image', response.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_bad_request(self):
        url = image_upload_url(self.recipe.id)
        response = self.client.post(url, {'image': 'notimage'},
                                    format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filter_recipes_by_tags(self):
        recipe1 = sample_recipe(user=self.user, title='Thai vegetable curry')
        recipe2 = sample_recipe(user=self.user, title='Aubergine with tahini')
        recipe3 = sample_recipe(user=self.user, title='Fish and Chips')
        tag1 = sample_tag(user=self.user, name='Vegan')
        tag2 = sample_tag(user=self.user, name='Vegetarian')
        recipe1.tags.add(tag1)
        recipe2.tags.add(tag2)

        response = self.client.get(
            RECIPE_URL,
            {'tags': f'{tag1.id},{tag2.id}'}
        )
        serializer1 = RecipeSerializer(recipe1)
        serializer2 = RecipeSerializer(recipe2)
        serializer3 = RecipeSerializer(recipe3)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, response.data)
        self.assertIn(serializer2.data, response.data)
        self.assertNotIn(serializer3.data, response.data)

    def test_filter_recipes_by_ingredients(self):
        recipe1 = sample_recipe(user=self.user, title='Thai vegetable curry')
        recipe2 = sample_recipe(user=self.user, title='Aubergine with tahini')
        recipe3 = sample_recipe(user=self.user, title='Fish and Chips')
        ingredient1 = sample_ingredient(user=self.user, name='Cabbage')
        ingredient2 = sample_ingredient(user=self.user, name='Salt')
        recipe1.ingredients.add(ingredient1)
        recipe2.ingredients.add(ingredient2)

        response = self.client.get(
            RECIPE_URL,
            {'ingredients': f'{ingredient1.id},{ingredient2.id}'}
        )
        serializer1 = RecipeSerializer(recipe1)
        serializer2 = RecipeSerializer(recipe2)
        serializer3 = RecipeSerializer(recipe3)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, response.data)
        self.assertIn(serializer2.data, response.data)
        self.assertNotIn(serializer3.data, response.data)
