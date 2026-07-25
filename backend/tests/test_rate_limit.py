"""The sliding window, driven by an injected clock instead of real waiting."""

from app.services.rate_limit import ADDRESS_LIMIT, DEVICE_LIMIT, Limit, SlidingWindow, check, reset


def test_requests_inside_the_cap_are_allowed() -> None:
    window = SlidingWindow(Limit(requests=3, per_seconds=60))

    assert [window.hit("device", at=1.0) for _ in range(3)] == [None, None, None]


def test_the_request_over_the_cap_is_told_how_long_to_wait() -> None:
    window = SlidingWindow(Limit(requests=2, per_seconds=60))
    window.hit("device", at=0.0)
    window.hit("device", at=10.0)

    assert window.hit("device", at=20.0) == 40.0


def test_the_window_slides_rather_than_resetting_on_the_hour() -> None:
    window = SlidingWindow(Limit(requests=2, per_seconds=60))
    window.hit("device", at=0.0)
    window.hit("device", at=30.0)

    assert window.hit("device", at=59.0) is not None
    # The first hit has aged out by now, so there is room again.
    assert window.hit("device", at=61.0) is None


def test_one_key_cannot_use_up_another_keys_allowance() -> None:
    window = SlidingWindow(Limit(requests=1, per_seconds=60))

    assert window.hit("noisy", at=0.0) is None
    assert window.hit("noisy", at=1.0) is not None
    assert window.hit("quiet", at=1.0) is None


def test_a_wait_is_never_reported_as_zero_seconds() -> None:
    window = SlidingWindow(Limit(requests=1, per_seconds=60))
    window.hit("device", at=0.0)

    assert window.hit("device", at=59.9) == 1.0


def test_the_device_limit_is_tighter_than_the_network_limit() -> None:
    assert DEVICE_LIMIT.requests < ADDRESS_LIMIT.requests
    assert str(DEVICE_LIMIT) == "30 uploads every 10 minutes"


def test_an_anonymous_caller_is_still_limited_by_address() -> None:
    reset()
    try:
        for _ in range(ADDRESS_LIMIT.requests):
            assert check(device_id=None, address="10.0.0.1") is None

        rejection = check(device_id=None, address="10.0.0.1")
        assert rejection is not None
        assert rejection.limit is ADDRESS_LIMIT
        assert "network" in rejection.detail
        assert check(device_id=None, address="10.0.0.2") is None
    finally:
        reset()
