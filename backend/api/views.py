from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart)
from users.models import Subscription, User
from .filters import IngredientFilter, RecipeFilter
from .permissions import IsAuthorOrReadOnly
from .serializers import (AvatarSerializer, IngredientSerializer,
                          RecipeMinifiedSerializer, RecipeReadSerializer,
                          RecipeWriteSerializer, UserWithRecipesSerializer)


class UserViewSet(DjoserUserViewSet):
    """Пользователи: djoser + аватар, подписки."""

    @action(['put', 'delete'], detail=False, url_path='me/avatar',
            permission_classes=[IsAuthenticated])
    def avatar(self, request):
        user = request.user
        if request.method == 'DELETE':
            if user.avatar:
                user.avatar.delete(save=True)
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = AvatarSerializer(user, data=request.data,
                                      context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        url = request.build_absolute_uri(user.avatar.url)
        return Response({'avatar': url})

    @action(['get'], detail=False, permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        authors = User.objects.filter(
            following__user=request.user).order_by('id')
        page = self.paginate_queryset(authors)
        serializer = UserWithRecipesSerializer(
            page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

    @action(['post', 'delete'], detail=True,
            permission_classes=[IsAuthenticated])
    def subscribe(self, request, id=None):
        author = get_object_or_404(User, pk=id)
        if request.method == 'DELETE':
            deleted, _ = Subscription.objects.filter(
                user=request.user, author=author).delete()
            if not deleted:
                return Response({'errors': 'Вы не подписаны на автора.'},
                                status=status.HTTP_400_BAD_REQUEST)
            return Response(status=status.HTTP_204_NO_CONTENT)
        if author == request.user:
            return Response({'errors': 'Нельзя подписаться на себя.'},
                            status=status.HTTP_400_BAD_REQUEST)
        _, created = Subscription.objects.get_or_create(
            user=request.user, author=author)
        if not created:
            return Response({'errors': 'Вы уже подписаны на автора.'},
                            status=status.HTTP_400_BAD_REQUEST)
        serializer = UserWithRecipesSerializer(
            author, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class IngredientViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    filterset_class = IngredientFilter


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.select_related('author').prefetch_related(
        'recipe_ingredients__ingredient')
    permission_classes = [IsAuthorOrReadOnly]
    filterset_class = RecipeFilter
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(['get'], detail=True, url_path='get-link',
            permission_classes=[AllowAny])
    def get_link(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        link = request.build_absolute_uri(f'/s/{recipe.pk:x}/')
        return Response({'short-link': link})

    def _toggle(self, request, pk, model):
        """Добавить/удалить рецепт в избранное или список покупок."""
        user = request.user
        recipe = get_object_or_404(Recipe, pk=pk)
        if request.method == 'POST':
            _, created = model.objects.get_or_create(user=user, recipe=recipe)
            if not created:
                return Response({'errors': 'Рецепт уже добавлен.'},
                                status=status.HTTP_400_BAD_REQUEST)
            return Response(
                RecipeMinifiedSerializer(
                    recipe, context={'request': request}).data,
                status=status.HTTP_201_CREATED)
        deleted, _ = model.objects.filter(user=user, recipe=recipe).delete()
        if not deleted:
            return Response({'errors': 'Рецепта нет в списке.'},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(['post', 'delete'], detail=True,
            permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        return self._toggle(request, pk, Favorite)

    @action(['post', 'delete'], detail=True,
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        return self._toggle(request, pk, ShoppingCart)

    @action(['get'], detail=False, permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        items = (
            RecipeIngredient.objects
            .filter(recipe__shoppingcart_set__user=request.user)
            .values('ingredient__name', 'ingredient__measurement_unit')
            .annotate(total=Sum('amount'))
            .order_by('ingredient__name')
        )
        lines = [
            f'{item["ingredient__name"].capitalize()} '
            f'({item["ingredient__measurement_unit"]}) — {item["total"]}'
            for item in items
        ]
        response = HttpResponse('\n'.join(lines),
                                content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = (
            'attachment; filename="shopping_list.txt"')
        return response
