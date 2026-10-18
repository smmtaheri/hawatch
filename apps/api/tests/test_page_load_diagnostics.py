import json
from unittest.mock import patch

from rest_framework.test import APIRequestFactory

from hawatch.api.v1.page_load_diagnostics import page_load_failure


def report():
    return {"path":"/points/eskelim","version":"release1","reason":"timeout","elapsed_ms":15000,
            "app_ready":True,"data_ready":True,"initial_data":True,"effective_type":"4g",
            "failed_assets":[],"pending_assets":["/static-assets/release1/assets/hawatch.js"]}


def test_failure_is_logged_without_analytics_or_account_data():
    payload = {**report(),"cookie":"secret","query":"token=secret"}
    with patch("hawatch.api.v1.page_load_diagnostics.LoadFailureThrottle.allow_request",return_value=True), patch("hawatch.api.v1.page_load_diagnostics.log.warning") as log:
        response = page_load_failure(APIRequestFactory().post("/api/v1/diagnostics/page-load/",payload,format="json"))
    assert response.status_code == 204
    assert response["Cache-Control"] == "no-store"
    assert log.call_args.kwargs["extra"] == {"event":"web.page_load_incomplete","page_load":report()}


def test_diagnostics_reject_query_strings_external_urls_and_oversized_payloads():
    factory = APIRequestFactory()
    cases = [{**report(),"path":"/points/eskelim?token=secret"},
             {**report(),"pending_assets":["https://elsewhere.test/script.js"]},
             {**report(),"unexpected":"x"*5000}]
    with patch("hawatch.api.v1.page_load_diagnostics.LoadFailureThrottle.allow_request",return_value=True), patch("hawatch.api.v1.page_load_diagnostics.log.warning") as log:
        for payload in cases:
            response = page_load_failure(factory.post("/api/v1/diagnostics/page-load/",payload,format="json"))
            assert response.status_code == 400
    log.assert_not_called()
