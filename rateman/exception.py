class RateManError(Exception):
    def __init__(self, msg):
        self._msg = msg

    def __repr__(self):
        return self._msg


class RadioConfigError(RateManError):
    def __init__(self, ap, radio, msg):
        super().__init__(msg)
        self._ap = ap,
        self._radio = radio

    def __repr__(self):
        return f"{self._ap.name}:{self._radio}: {msg}"


class RateControlError(RateManError):
    def __init__(self, rc_alg, msg):
        super().__init__(msg)
        self._alg = rc_alg

    def __repr__(self):
        return f"Error concerning rate control '{self._alg}': {self._msg}"

    def __str__(self):
        return f"Error concerning rate control '{self._alg}': {self._msg}"


class RateControlConfigError(RateControlError):
    def __init__(self, sta, rc_alg, msg):
        super().__init__(rc_alg, msg)
        self._sta = sta

    def __repr__(self):
        return f"{self._sta}: Error configuring rate control '{self._alg}': {self._msg}"


class AccessPointNotConnectedError(RateManError):
    def __init__(self, ap, msg):
        super().__init__(msg)
        self._ap = ap

    def __repr__(self):
        return f"Accesspoint '{self._ap.name}':  Not Connected: {self._msg}"


class ParsingError(RateManError):
    def __init__(self, ap, msg):
        super().__init__(msg)
        self._ap = ap

    def __repr__(self):
        return f"{self._ap}: {msg}"


class UnsupportedAPIVersionError(RateManError):
    def __init__(self, ap, supported_version, announced_version):
        super().__init__("")
        self._ap = ap
        self._announced = announced_version
        self._supported = supported_version

    def __str__(self):
        return f"{self._ap.name} announced unsupported API version {self._announced}. "
        f"We support {self._supported}"

    def __repr__(self):
        return f"Unsupported API version for {self._ap}: {self._announced} "
        f"(we support {self._supported})"


class UnsupportedFeatureException(RateManError):
    def __init__(self, ap, radio, feature):
        super().__init__("")
        self._ap = ap
        self._radio = radio
        self._feature = feature

    def __str__(self):
        return f"{self._ap.name}:{self._radio}: Radio does not support feature '{feature}'"

    def __repr__(self):
        return f"{self._ap}:{self._radio}: Radio does not support feature '{feature}'"


class StationModeError(RateManError):
    def __init__(self, sta, msg):
        super().__init__(msg)
        self._sta = sta

    def __repr__(self):
        return f"{self._sta}: {msg}"
