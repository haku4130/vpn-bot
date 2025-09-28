import grpc
from google.protobuf.message import Message
from grpc_generated_files import account_pb2, handler_pb2, handler_pb2_grpc, typed_message_pb2, user_pb2

from .exceptions import EmailExistsError, InboundTagNotFoundError, XrayError


def to_typed_message(message: Message) -> typed_message_pb2.TypedMessage:
    return typed_message_pb2.TypedMessage(type=message.DESCRIPTOR.full_name, value=message.SerializeToString())


class XrayAPI:
    @staticmethod
    def add_user(
        server_address: str,
        inbound_tag: str,
        email: str,
        user_id: str,
        level: int = 0,
    ) -> None:
        """Добавляет пользователя (adu) в указанный inbound Xray через gRPC API."""

        # Подключаемся к gRPC API Xray
        channel = grpc.insecure_channel(server_address)
        stub = handler_pb2_grpc.HandlerServiceStub(channel)

        user = user_pb2.User(
            email=email,
            level=level,
            account=to_typed_message(
                account_pb2.Account(
                    id=user_id,
                    flow='xtls-rprx-vision',
                ),
            ),
        )

        try:
            stub.AlterInbound(
                handler_pb2.AlterInboundRequest(
                    tag=inbound_tag,
                    operation=to_typed_message(handler_pb2.AddUserOperation(user=user)),
                ),
            )
        except grpc.RpcError as rpc_err:
            detail = rpc_err.details() or ''
            if detail.endswith(f'User {email} already exists.'):
                raise EmailExistsError(detail, email) from rpc_err
            if detail.endswith(f'handler not found: {inbound_tag}'):
                raise InboundTagNotFoundError(detail, inbound_tag) from rpc_err
            raise XrayError(detail) from rpc_err
        finally:
            channel.close()
