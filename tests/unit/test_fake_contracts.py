import pytest

from tests.fakes.protocols import (
    ClickEventRepoProtocol,
    ContentMapRepoProtocol,
    InboundEventRepoProtocol,
    SocialBridgeAdminClientProtocol,
)
from tests.fakes.repos_fake import FakeClickEventRepo, FakeContentMapRepo, FakeInboundEventRepo
from tests.fakes.socialbridge_admin_client_fake import FakeSocialBridgeAdminClient


@pytest.mark.parametrize(
    "fake,protocol",
    [
        (FakeSocialBridgeAdminClient(), SocialBridgeAdminClientProtocol),
        (FakeContentMapRepo(), ContentMapRepoProtocol),
        (FakeInboundEventRepo(), InboundEventRepoProtocol),
        (FakeClickEventRepo(), ClickEventRepoProtocol),
    ],
)
def test_fake_implements_protocol_contract(fake, protocol):
    assert isinstance(fake, protocol)
