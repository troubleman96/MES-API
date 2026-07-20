from rest_framework.pagination import PageNumberPagination

from apps.core.responses import envelope_ok


class MesPagination(PageNumberPagination):
    page_size_query_param = "per_page"
    page_size = 25
    max_page_size = 200

    def get_paginated_response(self, data):
        return envelope_ok(
            data={"items": data, "total": self.page.paginator.count},
            meta={
                "page": self.page.number,
                "per_page": self.get_page_size(self.request),
                "total_pages": self.page.paginator.num_pages,
            },
        )
