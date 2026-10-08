import numpy as np
import pytest
from obspy import Stream, Trace, UTCDateTime

from app import stations
from app.errors import InsufficientDataError, InvalidRequestError
from app.stations import ChannelInfo


def ch(net, sta, loc, code, lat=35.0, lon=139.0):
    return ChannelInfo(net, sta, loc, code, lat, lon)


def test_select_stations_requires_three_components_and_sorts_by_distance():
    channels = [
        *(ch("IU", "FAR", "00", f"BH{c}", lat=37.0) for c in "ZNE"),
        *(ch("IU", "NEAR", "00", f"BH{c}", lat=35.1) for c in "ZNE"),
        ch("IU", "PART", "00", "BHZ"),
        ch("IU", "PART", "00", "BHN"),
    ]
    result = stations.select_stations(channels, 35.0, 139.0)
    assert [s.station for s in result] == ["NEAR", "FAR"]
    assert 10 < result[0].distance_km < 12
    assert result[0].id == "IU.NEAR.00.BH"


def test_select_stations_prefers_hh_over_bh():
    channels = [
        *(ch("JP", "ABC", "", f"BH{c}") for c in "ZNE"),
        *(ch("JP", "ABC", "", f"HH{c}") for c in "ZNE"),
    ]
    [only] = stations.select_stations(channels, 35.0, 139.0)
    assert only.band == "HH" and only.id == "JP.ABC..HH"


def test_parse_station_id():
    assert stations.parse_station_id("IU.ANMO.00.BH") == ("IU", "ANMO", "00", "BH")
    assert stations.parse_station_id("JP.ABC..HH") == ("JP", "ABC", "", "HH")
    with pytest.raises(InvalidRequestError):
        stations.parse_station_id("IU.ANMO")


def _trace(comp, n=1000, start=UTCDateTime(2026, 1, 1)):
    header = {"network": "IU", "station": "X", "location": "00", "channel": f"BH{comp}",
              "sampling_rate": 100.0, "starttime": start}
    return Trace(np.arange(n, dtype=np.float64), header=header)


def test_stream_to_array_orders_zne_and_trims_to_common_span():
    st = Stream([_trace("E"), _trace("N", start=UTCDateTime(2026, 1, 1, 0, 0, 1)), _trace("Z")])
    data, fs, start = stations.stream_to_array(st)
    assert data.shape == (3, 900)
    assert fs == 100.0
    assert start == UTCDateTime(2026, 1, 1, 0, 0, 1)


def test_stream_to_array_missing_channel():
    with pytest.raises(InsufficientDataError):
        stations.stream_to_array(Stream([_trace("Z"), _trace("N")]))


def test_theoretical_arrivals_at_100_km():
    p, s = stations.theoretical_arrivals(100.0, 10.0)
    assert 12 < p < 20
    assert 22 < s < 35


# ---- 1/2 horizontals ---------------------------------------------------------------

def _inventory():
    from obspy.core.inventory import Channel, Inventory, Network, Station

    def chan(code, az, dip):
        return Channel(code, "00", 35.0, 139.0, 0.0, 0.0, azimuth=az, dip=dip,
                       sample_rate=100.0)

    sta = Station("X", 35.0, 139.0, 0.0,
                  channels=[chan("BHZ", 0, -90), chan("BH1", 90, 0), chan("BH2", 180, 0)])
    return Inventory([Network("IU", stations=[sta])], source="test")


def _oriented(comp_data):
    traces = []
    for comp, scale in comp_data.items():
        tr = _trace(comp)
        tr.data = tr.data * scale
        traces.append(tr)
    return Stream(traces)


def test_orient_to_zne_uses_real_azimuths():
    st = _oriented({"Z": 1.0, "1": 2.0, "2": 3.0})
    out = stations.orient_to_zne(st, _inventory())
    data, _, _ = stations.stream_to_array(out)
    ref = np.arange(1000, dtype=np.float32)
    np.testing.assert_allclose(data[1], -3.0 * ref, atol=1e-2)  # N = -BH2
    np.testing.assert_allclose(data[2], 2.0 * ref, atol=1e-2)   # E = BH1


def test_orient_to_zne_passes_through_zne():
    st = Stream([_trace("Z"), _trace("N"), _trace("E")])
    assert stations.orient_to_zne(st, None) is st


def test_orient_to_zne_failure_raises():
    st = Stream([_trace("Z"), _trace("1"), _trace("2")])
    from obspy.core.inventory import Inventory
    with pytest.raises(InsufficientDataError):
        stations.orient_to_zne(st, Inventory([], source="test"))


def test_select_stations_accepts_z12_but_not_z1():
    channels = [
        *(ch("IU", "OK", "00", f"BH{c}") for c in "Z12"),
        ch("IU", "BAD", "00", "BHZ"),
        ch("IU", "BAD", "00", "BH1"),
    ]
    assert [s.station for s in stations.select_stations(channels, 35.0, 139.0)] == ["OK"]


@pytest.mark.parametrize("bad", [
    "*.*.*.HH", "IU.AN?O.00.BH", "IU.AN,MO.00.BH", "IU.ANMO.00.LH", "IUU.ANMO.00.BH",
    "IU.ANMOXX.00.BH", "IU.ANMO.000.BH", "IU.ANMO.00.BHZ", "IU.ANMO.00.", "..00.BH",
])
def test_parse_station_id_rejects_wildcards_and_malformed(bad):
    with pytest.raises(InvalidRequestError):
        stations.parse_station_id(bad)


def test_parse_station_id_normalizes_case():
    assert stations.parse_station_id("iu.anmo.00.bh") == ("IU", "ANMO", "00", "BH")
    assert stations.parse_station_id("jp.abc..hh") == ("JP", "ABC", "", "HH")


def test_parse_station_id_rejects_trailing_newline():
    with pytest.raises(InvalidRequestError):
        stations.parse_station_id("IU.ANMO.00.BH\n")
