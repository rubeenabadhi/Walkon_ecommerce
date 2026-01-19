from django.urls import path
from . import views


urlpatterns = [
    #=======================================================================USER VIEW=======================================================================
    path("add-review/<int:product_id>/", views.add_review, name="add_review"),
    path("edit_review/<int:review_id>/", views.edit_review, name="edit_review"),
    path("delete_review/<int:review_id>/", views.delete_review, name="delete_review"),

    #=======================================================================ADMIN VIEW=======================================================================
    path("admin-review/", views.admin_review, name="admin_review"),
    path("delete-review/<int:review_id>/", views.delete_review, name="delete_review"),
]
