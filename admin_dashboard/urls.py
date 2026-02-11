from django.urls import path
from.import views

urlpatterns = [
    # ----------------Admin dashboard views
    path("admin", views.admin_dashboard, name="dashboard"),
    path("admin/data", views.admin_dashboard_data, name="admin_dashboard_data"),
    #path("best-selling-data/", views.best_selling_data, name="best_selling_data"),
    path('sales_chart_data/', views.sales_chart_data, name='admin_sales_chart_data'),
    path('admin/ledger-excel/',views.download_ledger_excel, name='ledger_excel'),

    # ----------------Admin sales report views
    path('sales-report/', views.sales_report_view, name='admin_sales_report'),
]