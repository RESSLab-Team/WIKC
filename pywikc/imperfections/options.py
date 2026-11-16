"""Parse and normalize imperfection inputs without modifying the caller's dict."""

import math


_SCALES = (
    'local_scale', 'local_scale_web', 'local_scale_flange',
    'straight_scale', 'straight_scale_ip', 'straight_scale_op',
    'plumb_scale_ip', 'plumb_scale_op', 'twist_scale',
)
_BOOLEANS = ('is_RBS', 'is_half_model', 'couple_local')
_NUMBERS = _SCALES + ('wave_length_factor', 'RBS_offset')
_KNOWN = set(_NUMBERS + _BOOLEANS + ('num_of_waves', 'web_identification_mode'))


def parse_bool(value):
    """Accept explicit true/false tokens; never use bool('False')."""
    if isinstance(value, bool):
        return value
    token = str(value).strip().lower()
    if token in ('true', '1', 'yes'):
        return True
    if token in ('false', '0', 'no'):
        return False
    raise ValueError('Expected true/false, 1/0 or yes/no; got {!r}'.format(value))


def parse_imperfection_options(items):
    """Parse comma-separated key=value items after the *Imperfection keyword."""
    options = {}
    for item in items:
        if not item.strip():
            continue  # Permit a trailing comma.
        key, separator, value = item.partition('=')
        key, value = key.strip(), value.strip()
        if not separator or not value:
            raise ValueError('Expected imperfection key=value; got {!r}'.format(item))
        if key not in _KNOWN:
            raise ValueError('Unknown imperfection option: {}'.format(key))
        if key in options:
            raise ValueError('Duplicate imperfection option: {}'.format(key))
        if key in _BOOLEANS:
            options[key] = parse_bool(value)
        elif key == 'num_of_waves':
            options[key] = int(value)
        elif key == 'web_identification_mode':
            options[key] = value.lower()
        else:
            options[key] = float(value)
    return options


def normalize_imperfection_options(options):
    """Return validated defaults; preserve legacy amplitudes unless opted out.

    Explicit per-direction/per-plate scales override the legacy scales.
    couple_local=True retains the original web/flange amplitude relation.
    web_identification_mode='solid' uses finite-thickness web classification by default.
    """
    unknown = set(options) - _KNOWN
    if unknown:
        raise ValueError('Unknown imperfection option(s): {}'.format(', '.join(sorted(unknown))))
    result = dict(options)
    for key in ('num_of_waves', 'wave_length_factor'):
        if key not in result:
            raise ValueError('Missing required imperfection option: {}'.format(key))
    waves = result['num_of_waves']
    if isinstance(waves, bool) or waves not in (1, 2):
        raise ValueError('num_of_waves must be 1 or 2')
    result['num_of_waves'] = int(waves)

    defaults = {
        'local_scale': 1., 'straight_scale': 1., 'twist_scale': 1.,
        'straight_scale_ip': 0., 'plumb_scale_ip': 0., 'plumb_scale_op': 0.,
        'is_RBS': False, 'is_half_model': False, 'couple_local': True,
        'web_identification_mode': 'solid',
    }
    for key, value in defaults.items():
        result.setdefault(key, value)
    result.setdefault('local_scale_web', result['local_scale'])
    result.setdefault('local_scale_flange', result['local_scale'])
    result.setdefault('straight_scale_op', result['straight_scale'])
    for key in _BOOLEANS:
        result[key] = parse_bool(result[key])
    for key in _NUMBERS:
        if key in result:
            result[key] = float(result[key])
            if not math.isfinite(result[key]):
                raise ValueError('{} must be finite'.format(key))
    if result['wave_length_factor'] <= 0.:
        raise ValueError('wave_length_factor must be positive')
    if result['web_identification_mode'] not in ('shell', 'solid'):
        raise ValueError("web_identification_mode must be 'shell' or 'solid'")
    if result['is_RBS'] and 'RBS_offset' not in result:
        raise ValueError('RBS_offset is required when is_RBS=True')
    if 'RBS_offset' in result and result['RBS_offset'] < 0.:
        raise ValueError('RBS_offset must be nonnegative')
    if (result['couple_local'] and
            result['local_scale_web'] * result['local_scale_flange'] < 0.):
        raise ValueError('Opposite local signs require couple_local=False')
    return result
