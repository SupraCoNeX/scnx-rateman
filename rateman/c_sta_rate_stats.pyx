from libc.stdlib cimport calloc, free

__all__ = ["StationRateStats"]


cdef class StationRateStats:
    cdef unsigned long long *_stats
    cdef int _max_rate_ofs
    cdef int _max_txpwr_ofs

    # size of one entry, i.e. one combination of rate and tx power:
    # [0]: attempts
    # [1]: successes
    # [2]: timestamp
    cdef int _txpwr_stride
    cdef int _rate_stride

    def __cinit__(self, int n_rates, int n_txpwrs):
        self._stats = NULL
        self.reset(n_rates, n_txpwrs)

    def __dealloc__(self):
        if self._stats != NULL:
            free(self._stats)
            self._stats = NULL

    def reset(self, int n_rates, int n_txpwrs):
        if self._stats != NULL:
            free(self._stats)

        self._txpwr_stride = 3  # per tx power: attempts, successes, last used timestamp
        self._rate_stride = (n_txpwrs + 1) * self._txpwr_stride  # per rate: all tx powers + 1 dummy

        cdef int array_size = (n_rates + 1) * (n_txpwrs + 1) * 3

        self._stats = <unsigned long long*>calloc(array_size, sizeof(unsigned long long))
        self._max_rate_ofs = n_rates
        self._max_txpwr_ofs = n_txpwrs

    cdef int _offset(self, int rate, int txpwr):
        if rate == -1:
            rate = self._max_rate_ofs

        if txpwr == -1:
            txpwr = self._max_txpwr_ofs

        return rate * self._rate_stride + txpwr * self._txpwr_stride

    def update(self, unsigned long long timestamp, rates, txpwrs, attempts, successes, size_t len):
        self._update(timestamp, rates, txpwrs, attempts, successes, len)

    cdef _update(
        self,
        unsigned long long timestamp,
        const int[::1] rates,
        const int[::1] txpwrs,
        const int[::1] attempts,
        const int[::1] successes,
        size_t len
    ):
        cdef int ofs

        if self._stats == NULL:
            return

        for i in range(len):
            ofs = self._offset(rates[i], txpwrs[i])
            self._stats[ofs] += attempts[i]
            self._stats[ofs + 1] += successes[i]
            self._stats[ofs + 2] = timestamp

    def get(self, int rate, int txpwr):
        if self._stats == NULL:
            return None

        if rate < 0 or rate > self._max_rate_ofs or txpwr > self._max_txpwr_ofs:
            return None

        ofs = self._offset(rate, txpwr)

        return self._stats[ofs], self._stats[ofs + 1], self._stats[ofs + 2]
