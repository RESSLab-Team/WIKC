""" Functions to generate the imperfection geometries.

"""
import numpy as np
from .i_sec_imperfections import flange_imperfection, web_imperfection, straightness_imperfection, \
    twisting_imperfection, plumbness_imperfection


# -------------------------------------------------------------------------------------------------------------------- #


def set_imperfection_properties(component):
    """Build wave parameters from inputs without changing the model length.

    ``imperfection_props`` holds user options; ``imperfection_params`` holds
    the derived amplitudes, axes and wave lengths. The returned dictionary
    can also be passed directly to i_local_imp/i_straight_imp/etc.
    """
    options = component._check_imperfection_props()
    section = component.section
    geometry = np.array([component.length, section.d, section.bf, section.tf, section.tw])
    if not np.all(np.isfinite(geometry)) or np.any(geometry <= 0.):
        raise ValueError('Component length and section dimensions must be finite and positive')
    if section.d <= 2. * section.tf or section.tw > section.bf:
        raise ValueError('Invalid I-section dimensions')

    # Half models represent z in [0, L_full/2], measured from a physical end.
    # The real mesh length remains component.length.
    length = component.length * (2. if options['is_half_model'] else 1.)
    web_amp = section.d / 300. * options['local_scale_web']
    flange_amp = section.bf / 250. * options['local_scale_flange']
    if options['couple_local']:
        # Retain the original amplitude relation and operation order.
        dw = web_amp
        df = dw * section.bf / 2. / ((section.d - section.tf) / 2.)
        if abs(df) > abs(flange_amp):
            df = flange_amp
            dw = df * ((section.d - section.tf) / 2.) / (section.bf / 2.)
        web_amp, flange_amp = dw, df

    n1 = component.coord_sys.basis[:, 0]
    n2 = component.coord_sys.basis[:, 1]
    props = {
        'n1': n1, 'n2': n2, 'length': length,
        'num_waves': options['num_of_waves'],
        'total_wave_length': options['wave_length_factor'] * section.d,
        'flange_width': section.bf,
        'web_depth': section.d - 2. * section.tf,
        'web_thickness': section.tw,
        'web_identification_mode': options['web_identification_mode'],
        'epsilon': 0.2,
        'is_RBS': options['is_RBS'],
        'delta_web': web_amp,
        'delta_flange': flange_amp,
        # op = local n1; ip = local n2 (the convention used in pywikc_m).
        'delta_global_op': length / 1500. * options['straight_scale_op'],
        'delta_global_ip': length / 1500. * options['straight_scale_ip'],
        'delta_plumbness_op': length / 1000. * options['plumb_scale_op'],
        'delta_plumbness_ip': length / 1000. * options['plumb_scale_ip'],
        'theta_twist': (0.6 / 100.) * options['twist_scale'],
    }
    if options['is_RBS']:
        props['RBS_offset'] = options['RBS_offset']
    component.imperfection_params = props
    return props


def generate_component_imp(component):
    """ Generates the imperfections for a component. """
    # Always rebuild so repeated generation reflects edited inputs.
    props = set_imperfection_properties(component)
    mid_height = props['length'] / 2.
    component.node_imperfections.clear()
    # Process the beam nodes
    for node_id, coords in component.beam_nodes.items():
        imp = np.array([0., 0., 0.])
        imp += i_straight_imp(coords, props)
        imp += i_plumb_imp(coords, props)
        component.node_imperfections[node_id] = imp
    # Process the continuum nodes
    for node_id, coords in component.continuum_nodes.items():
        if coords[2] > mid_height and props['is_RBS'] is False:
            is_top = True
        else:
            is_top = False
        imp = np.array([0., 0., 0.])
        imp += i_straight_imp(coords, props)
        imp += i_plumb_imp(coords, props)
        imp += i_local_imp(coords, props, is_top)
        imp += i_twist_imp(coords, props)
        component.node_imperfections[node_id] = imp
    pass


def i_local_imp(coord, props, is_top_seg):
    """ Returns the local flange/web imperfection.
    :param list coord: Node position in component coordinate system.
    :param dict props: Defines the properties of the imperfection.
    :param bool is_top_seg: If yes, the treat as top segment.
    """
    x = coord[0]
    y = coord[1]
    z = coord[2]
    # Check if top segment or bottom segment
    if is_top_seg:
        # Top segment z_mod starts at the top of the column and is positive in -z direction
        z_mod = props['length'] - z
        should_reverse = True
    else:
        z_mod = z
        should_reverse = False
    # Account for the RBS offset, if RBS, will always be "bottom segment"
    if props['is_RBS']:
        # todo: this is a hack, and should be made into an option in web/flange imperfections
        if props['RBS_offset'] <= z <= props['RBS_offset'] + props['total_wave_length']:
            z_mod -= props['RBS_offset']
        else:
            # Large value so that will not be considered for local imperfections
            z_mod = 1.0e8
    # Default to 'shell' uses the original centerline rule; 'solid' refers finite-thickness classification
    x_tol = 1.e-8
    if props.get('web_identification_mode', 'shell') == 'solid':
        is_web_node = (abs(x) <= props['web_thickness'] / 2. + x_tol and
                       abs(y) <= props['web_depth'] / 2. + x_tol)
    else:
        is_web_node = (abs(x) <= x_tol)
    if is_web_node:
        # Web node
        local_imp = web_imperfection(y, z_mod, should_reverse, **props)
    else:  # Flange node
        local_imp = flange_imperfection(x, y, z_mod, should_reverse, **props)
    return np.array(local_imp)


def i_straight_imp(coord, props):
    """ Returns the out-of-straightness imperfection.
    :param list coord: Node position in component coordinate system.
    :param dict props: Defines the properties of the imperfection.
    """
    z = coord[2]

    # Reuse the original single-axis shape; no duplicated ip/op formulas.
    return (np.array(straightness_imperfection(
        z, props['length'], props['delta_global_op'], props['n1'])) +
        np.array(straightness_imperfection(
            z, props['length'], props['delta_global_ip'], props['n2'])))


def i_twist_imp(coord, props):
    """ Returns the twisting imperfection.
    :param list coord: Node position in component coordinate system.
    :param dict props: Defines the properties of the imperfection.
    """
    x = coord[0]
    y = coord[1]
    z = coord[2]
    return np.array(twisting_imperfection(x, y, z, **props))


def i_plumb_imp(coord, props):
    """ Returns the out-of-plumbness imperfection.
    :param list coord: Node position in component coordinate system.
    :param dict props: Defines the properties of the imperfection.
    """
    z = coord[2]
    return (np.array(plumbness_imperfection(
        z, props['length'], props['delta_plumbness_op'], props['n1'])) +
        np.array(plumbness_imperfection(
            z, props['length'], props['delta_plumbness_ip'], props['n2'])))

# -------------------------------------------------------------------------------------------------------------------- #
