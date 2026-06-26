import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from secure_agg.crypto.fixed_point import encode_vector
from secure_agg.crypto.secret_sharing import split_vector
from secure_agg.schemas.messages import ShareMessage, compute_payload_digest


def test_share_message_does_not_contain_plaintext_parameter_array() -> None:
    plaintext = [1.0, 2.0, 3.0]
    share = split_vector(encode_vector(plaintext))[0]
    message = ShareMessage(
        round_id="r1",
        sender_id="P1",
        receiver_id="P1",
        vector_length=len(share),
        payload=share,
        digest=compute_payload_digest(share),
    )

    serialized = json.dumps(message.model_dump(), sort_keys=True)

    assert '"values"' not in serialized
    assert json.dumps(plaintext) not in serialized
    assert all(isinstance(value, int) for value in message.payload)
