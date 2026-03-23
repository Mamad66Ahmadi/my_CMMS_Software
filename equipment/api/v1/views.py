# equipment/api/v1/views.py

from rest_framework import viewsets, filters
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from ...models import LocationTag
from .serializers import LocationTagSerializer
from .permissions import IsStaffOrReadOnly
from .filters import LocationTagFilter


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 100

class LocationTagModelViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsStaffOrReadOnly]
    queryset = LocationTag.objects.all()
    serializer_class = LocationTagSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = LocationTagFilter

    lookup_field = 'loc_tag'  # Correct
    lookup_url_kwarg = 'loc_tag'  # Correct


    # ✅ CRITICAL FIX: Prevent template lookup
    def get_filter_backends(self):
        filter_backends = super().get_filter_backends()
        filter_backends[0].template_name = None
        return filter_backends