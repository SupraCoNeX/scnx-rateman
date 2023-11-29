from libc.string cimport strlen, strchr, memcpy, memcmp
from libc.stdio cimport printf
from libc.stdlib cimport strtoull, strtol

__all__ = ["parse_txs"]


cdef size_t next_field(const char *buf, char c, const char **next):
    cdef const char *sep = strchr(buf, c)

    if not sep:
        return 0

    if next:
        next[0] = sep + 1

    return sep - buf


cdef int parse_str(const char *buf, char *dst, size_t size):
    cdef int len = next_field(buf, b';', NULL)

    if len > size:
        return -1

    memcpy(dst, buf, len)
    dst[len] = 0

    return len + 1


cdef int parse_mrr_stage(const char *buf, int *rate, int *count, int *txpwr, int *successful_at):
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


cdef int parse_mrr(const char *buf, int *rates, int *counts, int *txpwrs, size_t len):
    cdef int ofs
    cdef int i = len - 1
    cdef int successful_at = -1

    for i in range(len):
        ofs = parse_mrr_stage(buf, &rates[i], &counts[i], &txpwrs[i], &successful_at)
        buf += ofs

    return successful_at


def parse_txs(const unsigned char[:] data):
    cdef const char *cur = <const char*> &data[0]
    cdef char *next;
    cdef int ofs
    cdef char phy[16]
    cdef size_t phy_len
    cdef unsigned long long timestamp
    cdef char mac[18]
    cdef int num_frames
    cdef int num_acked
    cdef int rates[4]
    cdef int counts[4]
    cdef int txpwrs[4]
    cdef int attempts[4]
    cdef int successes[4]
    cdef int successful_at

    ofs = parse_str(cur, phy, 16)
    phy_len = ofs - 1
    cur += ofs

    timestamp = strtoull(cur, &next, 16)

    # check for correct length of timestamp
    if next - cur != 16:
        return None

    cur = next + 1

    # FIXME: is this check necessary?
    if memcmp(cur, b"txs;", 4):
        return None

    cur += 4

    ofs = parse_str(cur, mac, 18)

    cur += ofs
    num_frames = strtol(cur, &next, 16)
    num_acked = strtol(next + 1, &next, 16)

    cur = next + 3

    successful_at = parse_mrr(cur, rates, counts, txpwrs, 4)

    for i in range(4):
        attempts[i] = num_frames * counts[i]
        successes[i] = num_acked if (i == successful_at) else 0

    return phy[:phy_len].decode("utf-8"), timestamp, mac[:17].decode("utf-8", "strict"), rates, txpwrs, attempts, successes
