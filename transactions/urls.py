from django.urls import path

from . import views

urlpatterns = [
    path("", views.transactions_view, name="transactions"),
    path("import-csv/", views.import_transactions_csv, name="import_transactions_csv"),
    path("export-csv/", views.export_transactions_csv, name="export_transactions_csv"),
]
