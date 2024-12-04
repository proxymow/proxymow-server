import sys
from jinja2 import meta
from pathlib import Path
import markdown

import model_context


def get_included_templates(env, parent_tmplt_filename, inclusions=None, add_root=True, debug=False):
    '''
        recursively assemble list of included templates
        template filenames will be [../../filename.html]
    '''
    template_source = 'No Source Available'
    try:
        if inclusions is None:
            inclusions = [Path(parent_tmplt_filename).stem] if add_root else []
        if parent_tmplt_filename.endswith('html'):
            template_source = env.loader.get_source(env, parent_tmplt_filename)
        elif parent_tmplt_filename.endswith('md'):
            markdown_source = env.loader.get_source(env, parent_tmplt_filename)
            template_source = markdown.markdown(markdown_source[0])
        parsed_content = env.parse(template_source)
        ref_tmplt_filenames = meta.find_referenced_templates(parsed_content)
        for ref_tmplt_filename in ref_tmplt_filenames:
            just_tmplt_name = Path(ref_tmplt_filename).stem
            if debug:
                print('tmplt name:', just_tmplt_name)
            inclusions.append(just_tmplt_name)
            inclusions = get_included_templates(
                env, ref_tmplt_filename, inclusions)
    except Exception as e:
        err_line = sys.exc_info()[-1].tb_lineno
        print('Exception parsing template {} on line {}'.format(e, err_line))
        print('Source:\n', template_source)

    return inclusions


def get_model_context(comp_names, host, req_args, req_kwargs, strict=True):
    '''
        Assemble the context dictionary
    '''
    ctx = getattr(model_context, 'global_ctx')(
        host, comp_names[0], req_args, req_kwargs)  # initialise
    for comp_name in comp_names:
        if hasattr(model_context, comp_name):
            comp_ctx = getattr(model_context, comp_name)(
                host, req_args, req_kwargs)
        else:
            if strict:
                raise Exception(
                    'No Model Context defined for the "{0}" component'.format(comp_name))
            else:
                comp_ctx = {}
        ctx.update(comp_ctx)

    return ctx
