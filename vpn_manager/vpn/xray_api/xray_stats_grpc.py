import grpc
from grpc_generated_files import command_pb2, command_pb2_grpc


def get_stats_online(host, user):
    channel = grpc.insecure_channel(host)
    stub = command_pb2_grpc.StatsServiceStub(channel)

    req = command_pb2.GetStatsRequest(name=f'user>>>{user}>>>online')

    resp = stub.GetStatsOnline(req)
    return resp
