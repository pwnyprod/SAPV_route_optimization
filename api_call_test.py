import os
from google.cloud import optimization_v1

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/markj/Documents/Studium/Master Maschinenbau TH Köln/Digitalisierung/routenplanung-sapv-f3073b6aecd7.json'
project_id= 'routenplanung-sapv'


def call_sync_api(project_id: str) -> None:
    """Call the sync api for fleet routing."""
    # Use the default credentials for the environment.
    # Change the file name to your request file.
    request_file_name = "test_request.json"
    fleet_routing_client = optimization_v1.FleetRoutingClient()

    with open(request_file_name) as f:
        # The request must include the `parent` field with the value set to
        # 'projects/{YOUR_GCP_PROJECT_ID}'.
        fleet_routing_request = optimization_v1.OptimizeToursRequest.from_json(f.read())
        fleet_routing_request.parent = f"projects/{project_id}"
        # Send the request and print the response.
        # Fleet Routing will return a response by the earliest of the `timeout`
        # field in the request payload and the gRPC timeout specified below.
        fleet_routing_response = fleet_routing_client.optimize_tours(
            fleet_routing_request, timeout=100
        )
        print(fleet_routing_response)
        # If you want to format the response to JSON, you can do the following:
        # from google.protobuf.json_format import MessageToJson
        # json_obj = MessageToJson(fleet_routing_response._pb)

call_sync_api(project_id)