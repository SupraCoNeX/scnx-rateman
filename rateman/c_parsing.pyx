# cython: profile=True

import cython
import array
from cpython cimport array
from libc.string cimport strchr, memcpy, memcmp
from libc.stdlib cimport strtoull, strtol
from libc.limits cimport ULONG_MAX, ULLONG_MAX

__all__ = ["parse_txs"]


@cython.profile(False)
cdef int next_field(const char *buf, char c, const char **next):
    cdef const char *sep = strchr(buf, c)

    if sep == NULL:
        return -1

    if next:
        next[0] = sep + 1

    return sep - buf


@cython.profile(False)
cdef int parse_str(const char *buf, char *dst, int size):
    cdef int len = next_field(buf, b';', NULL)

    if len < 0 or len > size:
        return -1

    memcpy(dst, buf, len)
    dst[len] = 0

    return len + 1


@cython.profile(False)
cdef int parse_mrr_stage(const char *buf,
    int *rate,
    int *count,
    int *txpwr,
    int *successful_at
):
    cdef char *next

    if buf[0] == b',':
        rate[0] = -1
        count[0] = 0
        txpwr[0] = -1
        return 3

    rate[0] = strtol(buf, &next, 16)
    count[0] = strtol(next + 1, &next, 16)

    successful_at[0] = successful_at[0] + 1

    if next[1] == b';' or next[1] == b'\0' or next[1] == b'\n':
        txpwr[0] = -1
        return next + 2 - buf
    else:
        txpwr[0] = strtol(next + 1, &next, 16)
        return next + 1 - buf


@cython.profile(False)
cdef int parse_mrr(
    const char *buf,
    int *rates,
    int *counts,
    int *txpwrs,
    size_t len
):
    cdef int ofs
    cdef int i = len - 1
    cdef int successful_at = -1

    for i in range(len):
        ofs = parse_mrr_stage(buf, rates + i, counts + i, txpwrs + i, &successful_at)
        buf += ofs

    return successful_at

cdef int _parse_txs(
    const char *line,
    char *phy,
    int *phy_len,
    unsigned long long *timestamp,
    char *mac,
    int *num_frames,
    int *probe,
    int[::1] rates,
    int[::1] txpwrs,
    int[::1] attempts,
    int[::1] successes,
):
    cdef const char *cur = line
    cdef char *next
    cdef int ofs
    cdef int successful_at
    cdef int counts[4]
    cdef int num_acked
    cdef int num_semicolons

    num_semicolons = line.count(b';')
    if num_semicolons != 10:
        return -1

    ofs = parse_str(cur, phy, 16)
    if (ofs == -1):
        return -1

    phy_len[0] = ofs - 1
    cur += ofs

    timestamp[0] = strtoull(cur, &next, 16)
    if timestamp[0] == ULLONG_MAX:
        return -1

    # check for correct length of timestamp
    if next - cur != 16:
        return -1

    cur = next + 1

    if memcmp(cur, b"txs;", 4):
        return -1

    cur += 4
    ofs = parse_str(cur, mac, 18)
    if ofs == -1:
        return -1

    cur += ofs
    num_frames[0] = strtol(cur, &next, 16)
    if num_frames[0] == ULONG_MAX:
        return -1

    num_acked = strtol(next + 1, &next, 16)
    if num_acked == ULONG_MAX:
        return -1

    probe[0] = strtol(next + 1, &next, 16)
    if probe[0] == ULONG_MAX:
        return -1

    cur = next + 1
    successful_at = parse_mrr(cur, &rates[0], counts, &txpwrs[0], 4)

    for i in range(4):
        attempts[i] = num_frames[0] * counts[i]
        successes[i] = num_acked if (i == successful_at) else 0

    return successful_at


def parse_txs(const unsigned char[:] data):
    cdef char phy[16]
    cdef int phy_len
    cdef unsigned long long timestamp
    cdef char mac[18]
    cdef int num_frames
    cdef int probe

    rates = array.array('i', [0, 0, 0, 0])
    txpwrs = array.array('i', [0, 0, 0, 0])
    attempts = array.array('i', [0, 0, 0, 0])
    successes = array.array('i', [0, 0, 0, 0])

    cdef int succ_stage = _parse_txs(
        <const char*> &data[0],
        phy,
        &phy_len,
        &timestamp,
        mac,
        &num_frames,
        &probe,
        rates,
        txpwrs,
        attempts,
        successes
    )

    if succ_stage == -1:
        return None

    try:
        return (
            phy[:phy_len].decode("utf-8", "strict"),
            timestamp,
            mac[:17].decode("utf-8", "strict"),
            num_frames,
            probe,
            rates,
            txpwrs,
            attempts,
            successes,
            succ_stage
        )
    except Exception as e:
        return None


cdef int twos_complement(const char *hexstr, int bitwidth):
    cdef int val = strtol(hexstr, NULL, 16)
    if val & (1 << (bitwidth - 1)):
        return val - (1 << bitwidth)
    return val


cdef int parse_s8(const char *s):
    return twos_complement(s, 8)


cdef int _parse_rxs(
    const char *line,
    char *phy,
    int *phy_len,
    unsigned long long *timestamp,
    char *mac,
    int *min_rssi,
    int[::1] per_antenna
):
    cdef const char *cur = line
    cdef char *next
    cdef int ofs
    cdef int num_semicolons

    num_semicolons = line.count(b';')
    if num_semicolons != 8:
        return -1

    ofs = parse_str(cur, phy, 16)
    if (ofs == -1):
        return -1

    phy_len[0] = ofs - 1
    cur += ofs

    timestamp[0] = strtoull(cur, &next, 16)
    if timestamp[0] == ULLONG_MAX:
        return -1

    # check for correct length of timestamp
    if next - cur != 16:
        return -1

    cur = next + 1
    if memcmp(cur, b"rxs;", 4):
        return -1

    cur += 4
    ofs = parse_str(cur, mac, 18)
    if ofs == -1:
        return -1
    cur += ofs

    min_rssi[0] = parse_s8(cur)
    cur = cur + 3

    for i in range(4):
        per_antenna[i] = parse_s8(cur)
        cur = cur + 3

    return 0

def parse_rxs(const unsigned char[:] data):
    cdef char phy[16]
    cdef int phy_len
    cdef unsigned long long timestamp
    cdef char mac[18]
    cdef int min_rssi
    per_antenna = array.array('i', [0, 0, 0, 0])

    try:
        if _parse_rxs(
            <const char*> &data[0],
            phy,
            &phy_len,
            &timestamp,
            mac,
            &min_rssi,
            per_antenna
        ):
            return None

        return (
            phy[:phy_len].decode("utf-8", "strict"),
            timestamp,
            mac[:17].decode("utf-8", "strict"),
            min_rssi,
            per_antenna
        )
    except Exception as e:
        return None