import os
import sys
import datetime
import time
import socket
import lxml.etree as ET
from copy import deepcopy
import markdown

import constants
import toolpane_defs
from forms.morphable import Morphable
from forms.term import Term
from forms.rule import Rule
from forms.settings import MeasureSettings
import vis_lib
from snapshot import SnapshotGrowth


def global_ctx(host, compname, _req_args, _req_kwargs):
    '''
        Items added to every context
    '''
    return {
        'cur_time': datetime.datetime.now(),
        'cur_year': datetime.date.today().year,
        'cur_secs': time.time(),
        'config': host.config,
        'compname': compname,
        'hostname': socket.gethostname(),
        'debug': host.debug
    }


def calibration(_host, _req_args, _req_kwargs):
    return {
        'profile_selection_toolpane': toolpane_defs.PROFILE_SELECTION,
        'lawn_dims_toolpane': toolpane_defs.CALIBRATION_LAWN_DIMS,
        'cal_quad_toolpane': toolpane_defs.CALIBRATION_QUAD
    }


def topview(_host, _req_args, _req_kwargs):
    return {}

def fence(_host, _req_args, _req_kwargs):
    return {
        'profile_selection_toolpane': toolpane_defs.PROFILE_SELECTION,
        'fence_cutter_toolpane': toolpane_defs.FENCE_CUTTER,
        'fence_edit_toolpane': toolpane_defs.FENCE_EDIT
    }


def fencesvg(_host, _req_args, _req_kwargs):
    return {}


def routeview(_host, _req_args, _req_kwargs):
    return {}


def routeviewsvg(_host, _req_args, _req_kwargs):
    return {}

def route(_host, _req_args, _req_kwargs):
    return {}

def vision(host, _req_args, _req_kwargs):

    cam_settings = host.camera.settings.clone(host.config)
    settings_toolpane = cam_settings.get_settings_as_toolpane(
        't1', 'ToolPaneSettings')

    return {
        'profile_selection_toolpane': toolpane_defs.PROFILE_SELECTION,
        'settings_toolpane': settings_toolpane,
        'settings_buttons_toolpane': toolpane_defs.CAM_SET_BTNS
    }


def scoring(host, _req_args, _req_kwargs):

    # create/refresh the working target snapshot for scorecard parameter adjustments
    min_progress = SnapshotGrowth.POSED.value
    selected_snapshots = [
        s for s in host.snapshot_buffer.values() if s._growth.value >= min_progress]
    host.log_debug('scoring: min progress requested: {0} {1}'.format(
        min_progress,
        [(s.ssid, s._growth.value) for s in selected_snapshots]
    )
    )
    if len(selected_snapshots) > 0:
        host.cached_scoring_snapshot = deepcopy(selected_snapshots[-1])
        host.log_debug('scoring: selected requested snapshot: {0}'.format(
            host.cached_scoring_snapshot.ssid))
        proj_ssids = [
            p.ssid for p in host.cached_scoring_snapshot._fltrd_projections]
        vp_idxs = [
            vp.index for vp in host.cached_scoring_snapshot._prospect_viewports]
    else:
        host.log_debug('scoring: no snapshots available')
        proj_ssids = []
        vp_idxs = []

    measure_settings = MeasureSettings(host.config)
    settings_toolpane = measure_settings.get_settings_as_toolpane(
        't1', 'ToolPaneSettings', sort=False)

    return {
        'ssid': host.cached_scoring_snapshot.ssid if host.cached_scoring_snapshot is not None else -1,
        'proj_ssids': str(proj_ssids),
        'vp_idxs': str(vp_idxs),
        'scoring_proj_limit': len(proj_ssids) - 1,
        'settings_toolpane': settings_toolpane,
        'settings_buttons_toolpane': toolpane_defs.MEAS_SET_BTNS,
        'contour_target_hdr': vis_lib.render_contour_hdr()
    }


def supervisor(host, _req_args, _req_kwargs):
    arena_width_m = host.config['arena.width_m']
    arena_length_m = host.config['arena.length_m']

    return {
        'trio_selection_toolpane': toolpane_defs.PROF_STRAT_PATT_SELECTION,
        'cockpit_monitor_toolpane': toolpane_defs.tp_cockpit_state_1,
        'cockpit_control_toolpane': toolpane_defs.tp_cockpit_control_1,
        'arena_width_m': arena_width_m,
        'arena_length_m': arena_length_m
    }


def contours(host, _req_args, _req_kwargs):
    rnd_score_props = {k: [round(itm, 6) for itm in v] for k, v in host.score_props.items()}
    return {
        'cockpit_monitor_toolpane': toolpane_defs.tp_cockpit_state_1,
        'contour_control_toolpane': toolpane_defs.CONTOUR_BTNS,
        'contour_target_hdr': vis_lib.render_contour_hdr(),
        'contour_target_subhdr': str(rnd_score_props),
        'auto_freeze_ms': constants.UI_AUTO_FREEZE_MS
    }


def navigator(host, _req_args, _req_kwargs):
    arena_width_m = host.config['arena.width_m']
    arena_length_m = host.config['arena.length_m']
    cur_strategy = host.config['current.strategy']

    add_term_xpath = "navigation_strategies/strategy[@name='{0}']/user_terms".format(
        cur_strategy)
    add_rule_xpath = "navigation_strategies/strategy[@name='{0}']/rules".format(
        cur_strategy)

    context_dict = {
        # use a dummy 'fully populated' object to obtain headings
        'terms_hdr': [v.title() for v in Term().render_dict()],
        'rules_hdr': [r.title() for r in Rule().render_dict()],
        'terms': host.rules_engine.terms,
        'rules': host.rules_engine.rules,
        'nav_selection_toolpane': toolpane_defs.NAVIGATOR_SELECTION,
        'cockpit_monitor_toolpane': toolpane_defs.tp_cockpit_state_1,
        'cockpit_control': toolpane_defs.tp_cockpit_control_2,
        'arena_width_m': arena_width_m,
        'arena_length_m': arena_length_m,
        'auto_freeze_ms': constants.NAVIGATOR_AUTO_FREEZE_MS,
        'add_term_xpath': add_term_xpath,
        'add_rule_xpath': add_rule_xpath
    }
    return context_dict


def form_shell(_host, _req_args, req_kwargs):
    ok_msg = 'The action has been completed successfully'
    instruction = 'Expand the tree menu to find the item to edit, insert, delete or duplicate...'
    success = 'success' in req_kwargs and req_kwargs['success'] == 'true'
    if success:
        advice = ok_msg + '<br />' + instruction
    else:
        advice = instruction
    return {
        'advice': advice
    }


def form(host, _req_args, req_kwargs):

    # free-range xpath
    if 'xp' not in req_kwargs:
        tp = None
        form_title = None
        mode = None
        xp = ''
        menu_id = None
    else:
        menu_id = req_kwargs['id']
        xp = req_kwargs['xp']
        mode = req_kwargs['mode']
        klassname = req_kwargs['klass'] if 'klass' in req_kwargs else None
        try:
            element = host.config.query_xpath(xp)
            klass = Morphable.get_klass_from_element(element, klassname)
            if mode == 'create':

                # POST Create
                form_object = klass()

            elif mode == 'edit':

                # PUT PATCH Update
                form_object = klass.from_xml(element)

            elif mode == 'duplicate':

                # POST Duplicate
                form_object = klass.from_xml(element)
                pk_name = getattr(klass, 'pk_att_name')
                pk_val = getattr(form_object, pk_name)
                new_pk_val = pk_val
                unique_pk = False
                while not unique_pk:
                    new_pk_val += '-copy'
                    unique_pk = len(element.getparent().xpath(
                        '//{0}[@{1}="{2}"]'.format(klass.__name__, pk_name, new_pk_val))) == 0
                setattr(form_object, pk_name, new_pk_val)

            elif mode == 'view':

                # View Read-Only
                form_object = klass.from_xml(element)

        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            err_msg = 'Error in model_context: ' + \
                str(e) + ' on line ' + str(err_line)
            host.log_error(err_msg)
            raise Exception('Error in model context')

        tp = form_object.as_complex_toolpane_form(
            'f1', 'formpane', 'root', mode)
        form_title = ''.join(
            map(lambda c: c if c.islower() else " " + c, klass.__name__.title()))

    return {
        'selected_formpane': tp,
        'form_title': form_title,
        'mode': mode,
        'url': xp,
        'token': str(hash(xp)),
        'menu_option_id': menu_id
    }


def settings_menu(host, _req_args, _req_kwargs):
    menu_html = None
    try:
        xml_filename = host.config_file_path_name
        xsl_filename = xml_filename.replace('config.xml', 'settings-menu.xsl')
        xslt = ET.parse(xsl_filename)
        transform = ET.XSLT(xslt)
        newdom = transform(host.config.cfg_tree)
        menu_html = ET.tostring(newdom, pretty_print=True, encoding="unicode")
    except:
        for error in transform.error_log:
            print(error.message, error.line)

    return {'settings_menu': menu_html}


def settings(_host, _req_args, req_kwargs):
    xp1 = req_kwargs['xp1'] if 'xp1' in req_kwargs else None
    return {
        'url': xp1
    }
    
def systerms(host, _req_args, _req_kwargs):
    html = None
    try:
        xml_filename = host.config_file_path_name
        xsl_filename = xml_filename.replace('config.xml', 'systerms.xsl')
        xslt = ET.parse(xsl_filename)
        transform = ET.XSLT(xslt)
        newdom = transform(host.config.cfg_tree)
        html = ET.tostring(newdom, pretty_print=True, encoding="unicode")
    except:
        for error in transform.error_log:
            print(error.message, error.line)

    return {'systerms': html}


def stages(host, _req_args, req_kwargs):
    # self.itinerary.position()
    crid = host.config['current.last_visited_route_node']
    if crid is None:
        crid = 1
    srid = int(req_kwargs['srid']) if 'srid' in req_kwargs else 1
    erid = int(req_kwargs['erid']) if 'erid' in req_kwargs else srid + 1
    return {
        'srid': srid,
        'erid': erid,
        'crid': crid
    }


def projections(host, _req_args, req_kwargs):

    # cid is contour id 0, 1, 2, 3
    num_entries = len(host.contours_buffer)
    cid = int(req_kwargs['cid']) if 'cid' in req_kwargs else num_entries - 1
    eid = num_entries - 1
    return {
        'cid': cid,
        'eid': eid,
        'contour_control_toolpane': toolpane_defs.CONTOUR_BTNS,
        'auto_freeze_ms': constants.UI_AUTO_FREEZE_MS
    }


def contour_navbar(host, _req_args, req_kwargs):

    # cid is contour id 0, 1, 2, 3
    num_entries = len(host.contours_buffer)
    cid = int(req_kwargs['cid']) if 'cid' in req_kwargs else num_entries - 1
    eid = num_entries - 1
    return {
        'cid': cid,
        'eid': eid
    }

def guide(host, _req_args, _req_kwargs):
    help_topics = {}
    # mine help folder for topics
    help_topic_entries = os.listdir("templates/help")
    for fldr in [e for e in help_topic_entries if '.' not in e]:
        fldr_path = "templates/help" + os.path.sep + fldr
        fldr_entries = os.listdir(fldr_path)
        html_filename = 'index.html'
        md_filename = 'index.md'
        if html_filename in fldr_entries:
            filepath = fldr_path + os.path.sep + html_filename
            with open(filepath,"r") as f:
                tmplt_string = f.read()
            tmplt = host.env.from_string(tmplt_string)
            # parse
            html = tmplt.render({})
            help_topics[fldr] = html
        elif md_filename in fldr_entries:
            filepath = fldr_path + os.path.sep + md_filename
            with open(filepath,"r") as f:
                md_string = f.read()
            html_string = markdown.markdown(md_string)
            # recover jinja expressions
            tmplt_string = html_string.replace('<!--', '').replace('-->', '')
            tmplt = host.env.from_string(tmplt_string)
            html = tmplt.render({})                
            help_topics[fldr] = html
    return {
        'help_topics': help_topics
    }
    