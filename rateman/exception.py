class RateManError(Exception):
	def __init__(self, msg):
		self._msg = msg

	def __repr__(self):
		return msg


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
		super().__init__(
		    f"{ap.name} announced unsupported API version! "
		    f"Announced={announced_version} supported={supported_version}"
		)

class StationModeError(RateManError):
	def __init__(self, sta, msg):
		super().__init__(msg)
		self._sta = sta

	def __repr__(self):
		return f"{self._sta}: {msg}"