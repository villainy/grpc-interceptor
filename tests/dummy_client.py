from concurrent import futures
from contextlib import contextmanager
from tempfile import gettempdir
from typing import Callable, Dict, List
from uuid import uuid4

import grpc

from grpc_interceptor.base import Interceptor
from tests.protos import dummy_pb2_grpc
from tests.protos.dummy_pb2 import DummyRequest, DummyResponse

SpecialCaseFunction = Callable[[str], str]


class DummyService(dummy_pb2_grpc.DummyServiceServicer):
    def __init__(self, special_cases: Dict[str, SpecialCaseFunction]):
        self._special_cases = special_cases

    def Execute(
        self, request: DummyRequest, context: grpc.ServicerContext
    ) -> DummyResponse:
        inp = request.input
        if inp in self._special_cases:
            output = self._special_cases[inp](inp)
        else:
            output = inp
        return DummyResponse(output=output)


@contextmanager
def dummy_client(
    special_cases: Dict[str, SpecialCaseFunction], interceptors: List[Interceptor],
):
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=1), interceptors=interceptors
    )
    dummy_service = DummyService(special_cases)
    dummy_pb2_grpc.add_DummyServiceServicer_to_server(dummy_service, server)

    uds_path = f"{gettempdir()}/{uuid4()}.sock"
    server.add_insecure_port(f"unix://{uds_path}")
    server.start()

    channel = grpc.insecure_channel(f"unix://{uds_path}")
    client = dummy_pb2_grpc.DummyServiceStub(channel)

    try:
        yield client
    finally:
        server.stop(None)
