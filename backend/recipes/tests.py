import base64
import tempfile

from django.test import override_settings
from rest_framework.test import APITestCase

from recipes.models import Ingredient, Recipe
from users.models import User

PIXEL = ('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABAgMAAABieywa'
         'AAAACVBMVEUAAAD///9fX1/S0ecCAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAACklEQV'
         'QImWNoAAAAggCByxOyYQAAAABJRU5ErkJggg==')


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix='foodgram_test_'))
class ApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            'u1', 'u1@ex.com', 'Qwerty123!', first_name='A', last_name='B')
        self.author = User.objects.create_user(
            'u2', 'u2@ex.com', 'Qwerty123!', first_name='C', last_name='D')
        self.sugar = Ingredient.objects.create(name='сахар',
                                               measurement_unit='г')
        self.salt = Ingredient.objects.create(name='соль',
                                              measurement_unit='г')

    def _recipe(self, **kw):
        data = {'ingredients': [{'id': self.sugar.id, 'amount': 5}],
                'image': PIXEL, 'name': 'Торт', 'text': 'Вкусно',
                'cooking_time': 10}
        data.update(kw)
        return data

    def test_register_and_login(self):
        resp = self.client.post('/api/users/', {
            'email': 'n@ex.com', 'username': 'new', 'first_name': 'N',
            'last_name': 'M', 'password': 'Qwerty123!'}, format='json')
        self.assertEqual(resp.status_code, 201)
        resp = self.client.post('/api/auth/token/login/', {
            'email': 'n@ex.com', 'password': 'Qwerty123!'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('auth_token', resp.data)

    def test_registration_requires_names(self):
        resp = self.client.post('/api/users/', {
            'email': 'n@ex.com', 'username': 'new',
            'password': 'Qwerty123!'}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_recipe_crud_and_permissions(self):
        self.client.force_authenticate(self.author)
        resp = self.client.post('/api/recipes/', self._recipe(),
                                format='json')
        self.assertEqual(resp.status_code, 201, resp.data)
        rid = resp.data['id']
        self.assertEqual(resp.data['ingredients'][0]['amount'], 5)
        # чужой рецепт править нельзя
        self.client.force_authenticate(self.user)
        resp = self.client.patch(f'/api/recipes/{rid}/', self._recipe(),
                                 format='json')
        self.assertEqual(resp.status_code, 403)
        self.client.force_authenticate(self.author)
        resp = self.client.patch(
            f'/api/recipes/{rid}/',
            self._recipe(ingredients=[{'id': self.salt.id, 'amount': 2}]),
            format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data['ingredients'][0]['name'], 'соль')
        resp = self.client.delete(f'/api/recipes/{rid}/')
        self.assertEqual(resp.status_code, 204)

    def test_recipe_validation(self):
        self.client.force_authenticate(self.user)
        bad = [
            {'ingredients': []},
            {'ingredients': [{'id': 9999, 'amount': 1}]},
            {'ingredients': [{'id': self.sugar.id, 'amount': 0}]},
            {'ingredients': [{'id': self.sugar.id, 'amount': 1}] * 2},
            {'cooking_time': 0},
            {'name': 'x' * 257},
            {'image': ''},
        ]
        for patch in bad:
            resp = self.client.post('/api/recipes/', self._recipe(**patch),
                                    format='json')
            self.assertEqual(resp.status_code, 400, patch)

    def test_anonymous_cannot_create(self):
        resp = self.client.post('/api/recipes/', self._recipe(),
                                format='json')
        self.assertEqual(resp.status_code, 401)

    def test_favorite_cart_and_shopping_list(self):
        self.client.force_authenticate(self.author)
        ids = []
        for amount in (5, 10):
            resp = self.client.post('/api/recipes/', self._recipe(
                ingredients=[{'id': self.sugar.id, 'amount': amount}]),
                format='json')
            ids.append(resp.data['id'])
        self.client.force_authenticate(self.user)
        for rid in ids:
            self.assertEqual(self.client.post(
                f'/api/recipes/{rid}/shopping_cart/').status_code, 201)
        self.assertEqual(self.client.post(
            f'/api/recipes/{ids[0]}/shopping_cart/').status_code, 400)
        self.assertEqual(self.client.post(
            '/api/recipes/9999/favorite/').status_code, 404)
        self.client.post(f'/api/recipes/{ids[0]}/favorite/')
        resp = self.client.get('/api/recipes/?is_favorited=1')
        self.assertEqual(resp.data['count'], 1)
        resp = self.client.get('/api/recipes/?is_in_shopping_cart=1')
        self.assertEqual(resp.data['count'], 2)
        resp = self.client.get('/api/recipes/download_shopping_cart/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Сахар (г) — 15', resp.content.decode())
        self.assertEqual(self.client.delete(
            f'/api/recipes/{ids[0]}/shopping_cart/').status_code, 204)

    def test_recipes_order_and_pagination(self):
        for i in range(7):
            Recipe.objects.create(
                author=self.author, name=f'r{i}', text='t', cooking_time=1,
                image='x.png')
        resp = self.client.get('/api/recipes/')
        self.assertEqual(resp.data['count'], 7)
        self.assertEqual(len(resp.data['results']), 6)
        self.assertEqual(resp.data['results'][0]['name'], 'r6')
        resp = self.client.get('/api/recipes/?limit=2')
        self.assertEqual(len(resp.data['results']), 2)

    def test_subscriptions(self):
        self.client.force_authenticate(self.user)
        url = f'/api/users/{self.author.id}/subscribe/'
        self.assertEqual(self.client.post(url).status_code, 201)
        self.assertEqual(self.client.post(url).status_code, 400)
        self.assertEqual(self.client.post(
            f'/api/users/{self.user.id}/subscribe/').status_code, 400)
        self.assertEqual(self.client.post(
            '/api/users/9999/subscribe/').status_code, 404)
        resp = self.client.get('/api/users/subscriptions/?recipes_limit=1')
        self.assertEqual(resp.data['count'], 1)
        self.assertTrue(resp.data['results'][0]['is_subscribed'])
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(self.client.delete(url).status_code, 400)

    def test_avatar_and_password(self):
        self.client.force_authenticate(self.user)
        resp = self.client.put('/api/users/me/avatar/', {'avatar': PIXEL},
                               format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('avatar', resp.data)
        self.assertEqual(self.client.put(
            '/api/users/me/avatar/', {}, format='json').status_code, 400)
        self.assertEqual(self.client.delete(
            '/api/users/me/avatar/').status_code, 204)
        resp = self.client.post('/api/users/set_password/', {
            'current_password': 'Qwerty123!', 'new_password': 'Zxcvb987!'},
            format='json')
        self.assertEqual(resp.status_code, 204)

    def test_ingredient_search_and_link(self):
        resp = self.client.get('/api/ingredients/?name=СА')
        self.assertEqual([i['name'] for i in resp.data], ['сахар'])
        recipe = Recipe.objects.create(
            author=self.author, name='r', text='t', cooking_time=1,
            image='x.png')
        resp = self.client.get(f'/api/recipes/{recipe.id}/get-link/')
        self.assertIn('/s/', resp.data['short-link'])
        resp = self.client.get(f'/s/{recipe.id:x}/')
        self.assertEqual(resp.status_code, 302)
        base64.b64decode(PIXEL.split(',')[1])
