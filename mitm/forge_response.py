import json
from mitmproxy import http

def request(flow: http.HTTPFlow) -> None:
    # Check if the request URL matches the one you are interested in
    if flow.request.pretty_url == "http://10.151.101.121:5000/":
        # Create a JSON response body
        json_response = {
            "key": 3000  # Your desired key-value pair
        }
        # Forge a response with status 200 and JSON body
        flow.response = http.Response.make(
            200,  # Status code (e.g., 200 for OK)
            json.dumps(json_response).encode(),  # Convert dict to JSON string and encode
            {"Content-Type": "application/json"}  # Response headers for JSON
        )
