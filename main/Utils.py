from typing import Any, Dict
import json
from urllib.parse import parse_qs, urlparse, urlencode

def merge_params(url: str, params: Dict[str, Any], json_params: bool = False, fragment: str = None, separator: str = '&') -> str:
    url_parts = urlparse(url)
    if not url_parts.scheme or not url_parts.netloc:
        raise ValueError("Invalid URL")
    if not isinstance(params, dict):
        raise ValueError("Params must be a dictionary")
    query = parse_qs(url_parts.query, keep_blank_values=True, strict_parsing=False, separator=separator)
    if json_params:
        for key, value in params.items():
            query[key] = [json.dumps(value)]
    else:
        query.update(params)
    if fragment is not None:
        url_parts = url_parts._replace(fragment=fragment)
    url_parts = url_parts._replace(query=urlencode(query, doseq=True, separator=separator))
    return url_parts.geturl()

def parse_params(authorization_response: str, cache: Dict[str, Dict[str, str]] = None, separator: str = '&') -> Dict[str, Any]:
    if cache is not None and authorization_response in cache:
        return cache[authorization_response]
    parsed_url = urlparse(authorization_response)
    if not parsed_url.scheme or not parsed_url.netloc:
        raise ValueError("Invalid authorization response")
    params_dict = {k: v[0] for k, v in parse_qs(parsed_url.query, keep_blank_values=True, strict_parsing=False, separator=separator).items()}
    if cache is not None:
        cache[authorization_response] = params_dict
    return {k: json.loads(v) if v.startswith('{') or v.startswith('[') else v for k, v in params_dict.items()}
