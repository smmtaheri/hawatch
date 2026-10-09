"""Browser revalidation must also work after gzip makes the ETag weak."""
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient


@pytest.mark.parametrize('path', ['/api/v1/points/tochal/forecast/week/', '/api/v1/routes/tochal-darband/forecast/week/'])
@pytest.mark.parametrize(('header', 'status'), [
    ('"current"', 304),
    ('W/"current"', 304),
    ('"other",W/"current"', 304),
    (' W/"other" , "current" ', 304),
    ('*', 304),
    ('W/"previous"', 200),
    ('current', 200),
    ('', 200),
])
def test_week_revalidation_preserves_private_cache_headers(path, header, status):
    with patch('hawatch.api.v1.week_views.cached_week', return_value=((b'{"updated":true}', '"current"'), 'HIT')):
        response = APIClient().get(path, HTTP_IF_NONE_MATCH=header)
    assert response.status_code == status
    assert response.content == (b'' if status == 304 else b'{"updated":true}')
    assert response['ETag'] == '"current"'
    assert response['Cache-Control'].startswith('private, max-age=')
    assert response['CDN-Cache-Control'] == 'no-store'
    assert response['Surrogate-Control'] == 'no-store'
    assert 'Accept-Encoding' in response['Vary'].split(', ')
    assert response['X-Hawatch-Cache'] == 'HIT'
